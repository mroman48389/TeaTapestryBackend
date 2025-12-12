from fastapi.testclient import TestClient
import pytest
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# import tracemalloc

from src.app.main import app
from src.db.base import Base
from src.utils.model_utils import get_model_column_names
from src.constants.model_metadata_constants import DELIMITER_VALUE
from tests.utils.test_utils import get_id_from_tea_name

# Report leaks (slow)
# tracemalloc.start()


# FastAPI provides the TestClient helper for simulating HTTP requests without
# running a server. It's like a mock browser. Define it here, since we'll be using it
# in our route tests.
@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope = "session")
def long_jing_tea_profile_id():
    """Fetches the ID for Long Jing after ingestion has run."""
    return get_id_from_tea_name("Long Jing")


# Functions decorated with @pytest.fixture are 
# automatically available to all tests in the same folder and
# subfolders (no importing needed!) Fixtures can be scoped to
# dictate when they're created and destroyed.  Scope can be function,
# class, module, session, etc. Function means the method will be created
# and destroyed for each test we define. This function runs each test 
# in a sandbox, so our real DBs and CSVs are untouched.
@pytest.fixture(scope = "function")
def create_test_db():
    # Create a temporary, in-memory SQLite for isolation. 
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)

    # Build a table.
    Base.metadata.create_all(bind=engine)

    # Open session.
    db = TestingSessionLocal()

    try:
        # Hand session to the test.
        yield db

    finally:
        # Ensure resources are closed after each test.
        db.close()
        engine.dispose()


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