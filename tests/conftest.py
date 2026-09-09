import os 

# Mark the process as a pytest run. The application checks this flag to skip 
# production startup logicsuch as creating real database tables or connecting 
# to external services. Also, don't run Sentry or SlowAPI.
#
# NOTE: Must be set before other imports or PYTEST_RUNNING will be false for 
# all the tests.
os.environ["PYTEST_RUNNING"] = "true"
os.environ["SENTRY_DSN"] = ""
os.environ["DISABLE_SLOWAPI"] = "1"

from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
import pytest
import csv
from sqlalchemy.orm import sessionmaker
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
import secrets
# import tracemalloc

import logging

from src.app.main import app
from src.db.base import Base
# SQLAlchemy only creates tables for models that have been imported into memory. 
from src.db.models.tea_profiles_model import TeaProfileModel 
from src.db.models.auth.user_models import UserInternalModel # noqa: F401
from src.db.models.user_tea_profile_notes_model import UserTeaProfileNotesModel
from src.db.models.auth.verification_token_model import VerificationTokenModel
from src.db.models.auth.session_token_model import SessionTokenModel
from src.api.schemas.user_tea_profile_notes_schema import UserTeaProfileNotesInboundSchema
from src.utils.session_utils import get_session 
from src.utils.model_utils import get_model_column_names
from src.utils.auth.password_utils import hash_password
from src.utils.auth.jwt_utils import (
    create_access_token, 
    create_refresh_token, 
    decode_refresh_token
)
from tests.utils.test_utils import get_empty_user_tea_profile_notes_body
from src.constants.model_metadata_constants import DELIMITER_VALUE
from src.constants.jwt_constants import REFRESH_TOKEN_LIFETIME_DAYS
from src.db.repositories.user_tea_profile_notes_repository import UserTeaProfileNotesRepository

# Remove the verbose SQL statements we don't care about from the TERMINAL 
# output.
logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)


@pytest.fixture(scope = "function")
def test_engine():
    # Create an in‑memory SQLite engine. Using StaticPool + check_same_thread = False
    # ensures all connections share the same in‑memory database.
    engine = create_engine(
        "sqlite://",
        connect_args = {"check_same_thread": False},
        poolclass = StaticPool
    )

    # SQLite has foreign key enforcement off by default. Without this, deletes
    # that violate a foreign key (e.g. deleting a user while a verification
    # token still references them) succeed silently instead of raising
    # IntegrityError, which would let real referential-integrity bugs pass
    # tests undetected.
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Automatically re-apply PRAGMA settings on reused connections, as 
    # connect only fires once when the connection is first created.
    @event.listens_for(engine, "begin")
    def set_sqlite_pragma_begin(dbapi_connection):
        dbapi_connection.exec_driver_sql("PRAGMA foreign_keys=ON")

    # Create all tables with this engine.
    Base.metadata.create_all(bind = engine)

    yield engine

    engine.dispose()


# Report leaks (slow)
# tracemalloc.start()

# Functions decorated with @pytest.fixture are 
# automatically available to all tests in the same folder and
# subfolders (no importing needed!) Fixtures can be scoped to
# dictate when they're created and destroyed.  Scope can be function,
# class, module, session, etc. Function means the method will be created
# and destroyed for each test we define. 

# This fixture provides an isolated, in‑memory SQLite database for tests.
# It ensures every test runs in a clean sandbox so no real database or files
# are touched. Use it instead of "Session" (from sqlalchemy.orm).
#
# By passing this fixture to our tests, we can add multiple types of data. All
# of the following is in the same database, just different tables:
#
#     users, tea profiles, user tea profile notes, verification tokens.
#
# For example, we can do:
#
#     create_test_db.add(user)
#     create_test_db.add(token)
#     create_test_db.commit()
#
# in the same test to add a new user to the users table and a new email 
# verification token to the verification tokens table. SQLAlchemy will use the 
# __table__name in the models we defined to add the data to the proper table.
# create_test_db will return the same SQLAlchemy session (database connection) no 
# matter how many times it's called in the same test. The first time it's called,
# it sets the database up for use. All subsequent calls simple return the 
# database that's set up by the first call.
@pytest.fixture
def create_test_db(test_engine):
    TestingSessionLocal = sessionmaker(bind = test_engine)
    db = TestingSessionLocal()

    try:
        # Hand session to the test.
        yield db

    finally:
        # Ensure resources are cleaned up after each test.
        db.close()


@pytest.fixture
def client(test_engine):
    TestingSessionLocal = sessionmaker(bind = test_engine)

    # Override FastAPI's DB dependency so routes use the test DB. 
    def override_get_session():
        db = TestingSessionLocal()

        try:
            yield db

        finally:
            db.close()

    app.dependency_overrides[get_session] = override_get_session

    # FastAPI provides the TestClient helper for simulating HTTP requests without
    # running a server. It's like a mock browser. Define it here, since we'll be using it
    # in our route tests.
    with TestClient(app) as c:
        yield c

    # Clean up after test.
    app.dependency_overrides.clear()


@pytest.fixture
def long_jing_tea_profile_id(seed_tea_profiles):
    return seed_tea_profiles.id


@pytest.fixture
def seed_tea_profiles(create_test_db):

    test_tea_profile = TeaProfileModel(
        name = "Long Jing",
        alternative_names = ["Dragonwell", "Dragon Well"],
        tea_type = "green",
        cultivars = ["Longjing #43"],
        processing = "pan-fired",
        oxidation_level = "low",
        cultural_significance = "Top 10 tea of China",
        cultural_significance_source = "Various",
        country_of_origin = "China",
        subregions = ["Hangzhou"],
        liquor_appearance = ["pale green"],
        liquor_aroma = ["fresh", "chestnut"],
        liquor_taste = ["smooth", "sweet"],
        liquor_body_mouthfeel = ["light"],
        body_effect = ["calming"],
        dry_leaf_appearance = ["flat", "green"],
        dry_leaf_aroma = ["nutty"],
        wet_leaf_appearance = ["tender"],
        wet_leaf_aroma = ["fresh"]
    )

    create_test_db.add(test_tea_profile)
    create_test_db.commit()
    create_test_db.refresh(test_tea_profile)

    return test_tea_profile


@pytest.fixture
def seed_user_tea_profile_notes(
    create_test_db, 
    access_token_for_test_user, 
    long_jing_tea_profile_id
):
    user = access_token_for_test_user["user"]

    body = get_empty_user_tea_profile_notes_body()

    user_tea_profile_notes = UserTeaProfileNotesModel(
        user_id = user.id,
        tea_profile_id = long_jing_tea_profile_id,
        **body
    )

    create_test_db.add(user_tea_profile_notes)
    create_test_db.commit()

    # Reload both user and notes from the same session so they are both bound to create_test_db.
    user = create_test_db.get(UserInternalModel,user.id)
    user_tea_profile_notes = (
        create_test_db.get(UserTeaProfileNotesModel, user_tea_profile_notes.id)
    )

    return user_tea_profile_notes


@pytest.fixture
def seed_verification_token(create_test_db, create_test_user):
    """
        Create a user and a verification token for that user.
        Returns both the user and the token, bound to a session to 
        help prevent IntegrityErrors.
    """

    def _seed_verification_token(
        purpose,
        raw_verification_token = None,
        expires_in_minutes = 30,
        used = False,
        **overrides
    ):
        # Create the user.
        user = create_test_user(**overrides)

        # If caller didn't specify a raw token, generate one.
        raw_verification_token = raw_verification_token or secrets.token_urlsafe(32)

        # Hash the token.
        token_hash = hashlib.sha256(raw_verification_token.encode()).hexdigest()

        expires_at = datetime.now(timezone.utc) + timedelta(minutes = expires_in_minutes)

        # Create the token row
        verification_token = VerificationTokenModel(
            user_id = user.id,
            token_hash = token_hash,
            purpose = purpose,
            expires_at = expires_at,
            used = used,
        )

        create_test_db.add(verification_token)
        create_test_db.commit()

        # Reload both objects so they are session-bound.
        user = create_test_db.get(UserInternalModel, user.id)
        verification_token = create_test_db.get(VerificationTokenModel, verification_token.id)

        return {
            "user": user,
            "raw_token": raw_verification_token,
            "token": verification_token,
            "token_hash": token_hash,
        }

    return _seed_verification_token


@pytest.fixture
# Note that while we can rename fixture functions, you CANNOT rename fixture
# parameters.
def create_test_csv(tmp_path):

    # Note that, unless we use pytest's built-in parametrization, we can't
    # change the pytest fixture's methods. Instead, we create and return this
    # inner function.
    def _create_csv(model = None, sample_data: dict | None = None):
        # Set up FQ CSV file path
        csv_file = tmp_path / "test.csv"

        # If no model is specified, create a simple on-the-fly schema to use.
        if model is None:
            sample = "name,origin\nDragonwell,China\n"
            csv_file.write_text(sample)
            return str(csv_file)

        # Build the data row from the model and sample_data (if any) that was passed in.
        model_col_names = get_model_column_names(model, False)
        # For each column name in the model, return the corresponding value 
        # from sample_data. If the key (the column name) is not present in
        # sample_data or sample_data wasn't specified, return "" for the value instead.
        sample_data = sample_data or {}

        # SQLite doesn't have true arrays, so we must serialize into strings.
        # row = {col: DELIMITER_VALUE.join(val) if isinstance(val, list) else val
        #     for col, val in sample_data.items()}
        row = {}
        for col in model_col_names:
            # Get the value for the key "col", returning "" if the key does not exist
            # in the sample data dict.
            val = sample_data.get(col, "")

            # If the value is a list, serialize into a string.
            if isinstance(val, list):
                row[col] = DELIMITER_VALUE.join(val)
            # Otherwise, use the value as-is.
            else:
                row[col] = val

        # Write with proper quoting
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames = model_col_names,
                quoting = csv.QUOTE_MINIMAL  # or csv.QUOTE_ALL for extra safety
            )
            writer.writeheader()
            writer.writerow(row)

        return str(csv_file)
    
    return _create_csv


@pytest.fixture
def create_test_user(create_test_db):

    '''
        Factory fixture that can create one or more users
        in tests requiring a user(s) in the DB.
    '''
    def _create_test_user(
        email = "testUser@example.com",
        password = "MyPassword@123",
        display_name = "Test User",
        **overrides
    ):
        
        user = UserInternalModel(
            email = email,
            hashed_password = hash_password(password),
            display_name = display_name,
            **overrides
        )

        create_test_db.add(user)
        create_test_db.commit()
        create_test_db.refresh(user)

        return user

    return _create_test_user


@pytest.fixture
def user_tea_profile_notes_repo(create_test_db):
    return UserTeaProfileNotesRepository(create_test_db)


@pytest.fixture
def empty_user_tea_profile_notes_inbound():
    body = get_empty_user_tea_profile_notes_body(as_json = True)
    return UserTeaProfileNotesInboundSchema(**body)



@pytest.fixture
def access_token_for_test_user(create_test_user):

    user = create_test_user()

    access_token = create_access_token(str(user.id), user.is_verified)

    return {
        "user": user,
        "access_token": access_token,
    }


# Return just the raw refresh token for a test user. Use this if the test 
# does NOT interact with the refresh endpoint or session DB.
@pytest.fixture
def refresh_token_for_test_user(access_token_for_test_user):

    user = access_token_for_test_user["user"]

    refresh_token = create_refresh_token(
        user_id = str(user.id), 
        email_verified = user.is_verified, 
        refresh_token_id = str(uuid.uuid4())
    )

    return refresh_token


@pytest.fixture
def auth_bundle_for_test_user(create_test_user):

    user = create_test_user()

    access_token = create_access_token(
        str(user.id), 
        user.is_verified
    )

    refresh_token = create_refresh_token(        
        user_id = str(user.id), 
        email_verified = user.is_verified, 
        refresh_token_id = str(uuid.uuid4())
    )

    refresh_token_id = decode_refresh_token(refresh_token).refresh_token_id

    return {
        "user": user, 
        "access_token": access_token, 
        "refresh_token": refresh_token,
        "refresh_token_id": refresh_token_id,
    }


# Use this for the refresh endpoint, or, in general, when a valid refresh
# session in the database is required.
@pytest.fixture
def refresh_token_bundle_for_test_user(create_test_user, create_test_db):
    user = create_test_user()

    raw_refresh_token = create_refresh_token(
        user_id = str(user.id),
        email_verified = user.is_verified,
        refresh_token_id = str(uuid.uuid4())
    )

    payload = decode_refresh_token(raw_refresh_token)
    refresh_token_id = payload.refresh_token_id
    refresh_token_hash = hashlib.sha256(raw_refresh_token.encode()).hexdigest()

    now = datetime.now(timezone.utc)

    session_token = SessionTokenModel(
        user_id = user.id,
        refresh_token_hash = refresh_token_hash,
        refresh_token_id = refresh_token_id,
        created_at = now,
        expires_at = now + timedelta(days = REFRESH_TOKEN_LIFETIME_DAYS),
        revoked_at = None,
        user_agent = "pytest",
        ip_address = "127.0.0.1"
    )

    create_test_db.add(session_token)
    create_test_db.commit()

    return {
        "user": user,
        "raw": raw_refresh_token,
        "hashed": refresh_token_hash,
        "id": refresh_token_id,
    }


@pytest.fixture
def email_send_success(monkeypatch):
    def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "src.api.routers.auth_router.send_email",
        _noop
    )

    return _noop


@pytest.fixture
def email_send_failure(monkeypatch):
    def _fail(*args, **kwargs):
        raise Exception("Simulated email failure")

    monkeypatch.setattr(
        "src.api.routers.auth_router.send_email",
        _fail
    )

    return _fail


@pytest.fixture
def email_capture(monkeypatch):
    sent_emails = []

    def _capture(to_email, subject, body):
        sent_emails.append({
            "to": to_email,
            "subject": subject,
            "body": body,
        })

    monkeypatch.setattr(
        "src.api.routers.auth_router.send_email",
        _capture
    )

    return sent_emails
