import os 
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
import pytest
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# import tracemalloc

from src.app.main import app
from src.db.base import Base
# SQLAlchemy only creates tables for models that have been imported into memory. 
from src.db.models.tea_profiles_model import TeaProfileModel 
from src.db.models.user_models import UserInternalModel # noqa: F401
from src.db.models.user_tea_profile_notes_model import UserTeaProfileNotesModel
from src.utils.session_utils import get_session 
from src.utils.model_utils import get_model_column_names
from src.utils.auth.password_utils import hash_password
from src.utils.auth.jwt_utils import create_access_token, create_refresh_token
from tests.utils.test_utils import get_empty_user_tea_profile_notes_body
from src.constants.model_metadata_constants import DELIMITER_VALUE


# Mark the process as a pytest run. The application checks this flag to skip 
# production startup logicsuch as creating real database tables or connecting 
# to external services.
os.environ["PYTEST_RUNNING"] = "true"

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
@pytest.fixture(scope = "function")
def create_test_db():
    # Create an in‑memory SQLite engine. Using StaticPool + check_same_thread=False
    # ensures all connections share the same in‑memory database.
    engine = create_engine(
        "sqlite://",
        connect_args = {"check_same_thread": False},
        poolclass = StaticPool
    )

     # Open a single shared connection for the entire test.
    connection = engine.connect()

    # Create all tables on this connection.
    Base.metadata.create_all(bind = connection)

    # Create a sessionmaker bound to this shared connection.
    TestingSessionLocal = sessionmaker(bind = connection)

    # Open a session for the test.
    db = TestingSessionLocal()

    try:
        # Hand session to the test.
        yield db

    finally:
        # Ensure resources are cleaned up after each test.
        db.close()
        connection.close()
        engine.dispose()

@pytest.fixture
def client(create_test_db):
    # Override FastAPI's DB dependency so routes use the test DB. 
    def override_get_session():
        try:
            yield create_test_db
        finally:
            pass

    app.dependency_overrides[get_session] = override_get_session

    # FastAPI provides the TestClient helper for simulating HTTP requests without
    # running a server. It's like a mock browser. Define it here, since we'll be using it
    # in our route tests.
    with TestClient(app) as c:
        yield c

    # Clean up after test
    app.dependency_overrides.clear()

@pytest.fixture
def long_jing_tea_profile_id(create_test_db, seed_tea_profiles):
    obj = create_test_db.query(TeaProfileModel).filter_by(name = "Long Jing").first()
    return obj.id

@pytest.fixture
def seed_tea_profiles(create_test_db):
    create_test_db.add(TeaProfileModel(
        name="Long Jing",
        alternative_names=["Dragonwell", "Dragon Well"],
        tea_type="green",
        cultivars=["Longjing #43"],
        processing="pan-fired",
        oxidation_level="low",
        cultural_significance="Top 10 tea of China",
        cultural_significance_source="Various",
        country_of_origin="China",
        subregions=["Hangzhou"],
        liquor_appearance=["pale green"],
        liquor_aroma=["fresh", "chestnut"],
        liquor_taste=["smooth", "sweet"],
        liquor_body_mouthfeel=["light"],
        body_effect=["calming"],
        dry_leaf_appearance=["flat", "green"],
        dry_leaf_aroma=["nutty"],
        wet_leaf_appearance=["tender"],
        wet_leaf_aroma=["fresh"]
    ))
    create_test_db.commit()

@pytest.fixture
def seed_user_tea_profile_notes(create_test_db, test_user, long_jing_tea_profile_id):
    body = get_empty_user_tea_profile_notes_body()

    user_tea_profile_notes = UserTeaProfileNotesModel(
        user_id = test_user.id,
        tea_profile_id = long_jing_tea_profile_id,
        **body
    )

    create_test_db.add(user_tea_profile_notes)
    create_test_db.commit()
    create_test_db.refresh(user_tea_profile_notes)

    return user_tea_profile_notes


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
def test_user(create_test_db):
    user = UserInternalModel(
        email = "testUser@testdomain.com",
        hashed_password = hash_password("TestPassword@123"),
        display_name = "Test User"
    )

    create_test_db.add(user)
    create_test_db.commit()
    create_test_db.refresh(user)

    return user

@pytest.fixture
def access_token_for_test_user(test_user):
    return create_access_token(str(test_user.id), test_user.is_verified)

@pytest.fixture
def refresh_token_for_test_user(test_user):
    return create_refresh_token(str(test_user.id), test_user.is_verified)