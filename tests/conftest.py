import os #changeA
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
import pytest
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# import tracemalloc

from src.app.main import app
from src.db.base import Base
# SQLAlchemy only creates tables for models that have been imported into memory. #changeA
from src.db.models.tea_profiles_model import TeaProfileModel  #changeA
from src.utils.session_utils import get_session 
from src.utils.model_utils import get_model_column_names
from src.constants.model_metadata_constants import DELIMITER_VALUE

os.environ["PYTEST_RUNNING"] = "1" #changeA

# Report leaks (slow)
# tracemalloc.start()

#changeA
# FastAPI provides the TestClient helper for simulating HTTP requests without
# running a server. It's like a mock browser. Define it here, since we'll be using it
# in our route tests.
@pytest.fixture
def client(create_test_db):
    # Override FastAPI's DB dependency so routes use the test DB
    def override_get_session():
        print("DEBUG: USING TEST DB SESSION")
        print("DEBUG: SESSION BIND:", create_test_db.bind)
        print("DEBUG: OVERRIDE SESSION CONNECTION:", create_test_db.connection())
        print("DEBUG: OVERRIDE ENGINE ID:", id(create_test_db.bind))
        try:
            yield create_test_db
        finally:
            pass

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as c:
        yield c

    # Clean up after test
    app.dependency_overrides.clear()

#Old:
# @pytest.fixture
# def client():
#     with TestClient(app) as c:
#         yield c

@pytest.fixture
def long_jing_tea_profile_id(create_test_db, seed_tea_profiles):
    obj = create_test_db.query(TeaProfileModel).filter_by(name="Long Jing").first()
    return obj.id

#Old
# @pytest.fixture(scope = "session")
# def long_jing_tea_profile_id():
#     """Fetches the ID for Long Jing after ingestion has run."""
#     return get_id_from_tea_name("Long Jing")

@pytest.fixture(scope="function")
def create_test_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    # IMPORTANT: open a single shared connection
    connection = engine.connect()

    # Bind the metadata to this connection explicitly
    Base.metadata.create_all(bind=connection)

    # Create a sessionmaker bound to THIS connection
    TestingSessionLocal = sessionmaker(bind=connection)

    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        connection.close()
        engine.dispose()

#Old changeA
# Functions decorated with @pytest.fixture are 
# automatically available to all tests in the same folder and
# subfolders (no importing needed!) Fixtures can be scoped to
# dictate when they're created and destroyed.  Scope can be function,
# class, module, session, etc. Function means the method will be created
# and destroyed for each test we define. This function runs each test 
# in a sandbox, so our real DBs and CSVs are untouched.
# @pytest.fixture(scope = "function")
# def create_test_db():
#     # Create a temporary, in-memory SQLite for isolation. 
#     #changeA
#     # engine = create_engine("sqlite:///:memory:")
#     engine = create_engine(
#         "sqlite:///:memory:?cache=shared",
#         connect_args={"check_same_thread": False},
#         poolclass=StaticPool
#     )
#     TestingSessionLocal = sessionmaker(bind=engine)

#     # Build a table.
#     Base.metadata.create_all(bind=engine)

#     #changeA
#     # DEBUG: what tables does SQLAlchemy think exist on this engine?
#     with engine.connect() as conn:
#         print("DEBUG: CREATE_TEST_DB CONNECTION:", conn)
#     inspector = inspect(engine)
#     print("DEBUG: TEST DB TABLES:", inspector.get_table_names())
#     print("DEBUG: METADATA TABLES:", list(Base.metadata.tables.keys()))
#     print("DEBUG: ENGINE POOL:", type(engine.pool))
#     print("DEBUG: TEST ENGINE ID:", id(engine))

#     # Open session.
#     db = TestingSessionLocal()

#     try:
#         # Hand session to the test.
#         yield db

#     finally:
#         # Ensure resources are closed after each test.
#         db.close()
#         engine.dispose()


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
