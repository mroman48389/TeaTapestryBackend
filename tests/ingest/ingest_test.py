from sqlalchemy import text
# from sqlalchemy import inspect

from src.db.models.tea_profiles_model import TeaProfileModel
from src.ingest.ingest import ingest_data
import src.ingest.ingest as ingest_module
from src.constants.tea_profiles_constants import (
    REQUIRED_TEA_PROFILE_MODEL_FIELDS, TeaProfileModelFields
)
from src.utils.sample_data_utils import get_sample_tea_profiles_data

def test_ingest_data(create_test_db, create_test_csv):
    # Use create_test_csv fixture to create a CSV file with sample data
    # and return the path.

    sample_tea_profiles_data = get_sample_tea_profiles_data()
    csv_file = create_test_csv(TeaProfileModel, sample_tea_profiles_data)

    # Ingest data from the test CSV.
    ingest_data(
        create_test_db,
        csv_file, 
        TeaProfileModel, 
        [
            field for field in REQUIRED_TEA_PROFILE_MODEL_FIELDS 
            if field != TeaProfileModelFields.ID
        ], 
        [TeaProfileModelFields.NAME]
    )

    # To run just this test:
    #
    # $env:PYTHONPATH="C:\Proj\TeaTapestryBackend"
    # >> pytest tests\ingest\ingest_test.py::test_ingest_data -s
    #
    # print(
    #     "Rows in staging:",
    #     create_test_db.execute(text("SELECT COUNT(*) FROM tea_profiles_staging")).scalar()
    # )
    # print(
    #     "Rows in base:",
    #     create_test_db.execute(text("SELECT COUNT(*) FROM tea_profiles")).scalar()
    # )
    #
    # insp = inspect(create_test_db.bind)
    # print("Tables in DB:", insp.get_table_names())
    # print("Columns in tea_profiles_staging:", insp.get_columns("tea_profiles_staging"))
    # print("Columns in tea_profiles:", insp.get_columns("tea_profiles"))
    # with open(csv_file) as f:
    #     print("CSV contents:\n", f.read())
    # rows = list(create_test_db.execute(text("SELECT * FROM tea_profiles_staging")))
    # print("Staging rows:", rows)

    # Query the test DB to confirm the row was inserted
    result = create_test_db.query(TeaProfileModel).filter_by(
        name = sample_tea_profiles_data[TeaProfileModelFields.NAME]).first()
    
    assert result.tea_type == \
        sample_tea_profiles_data[TeaProfileModelFields.TEA_TYPE]
    
    assert result.cultivars == \
        sample_tea_profiles_data[TeaProfileModelFields.CULTIVARS]
    
    assert result.country_of_origin == \
        sample_tea_profiles_data[TeaProfileModelFields.COUNTRY_OF_ORIGIN]
    
    assert result.liquor_appearance == \
        sample_tea_profiles_data[TeaProfileModelFields.LIQUOR_APPEARANCE]
    
    assert result.liquor_aroma == \
        sample_tea_profiles_data[TeaProfileModelFields.LIQUOR_AROMA]
    
    assert result.liquor_taste == \
        sample_tea_profiles_data[TeaProfileModelFields.LIQUOR_TASTE]

def test_ingest_data_failure(monkeypatch, create_test_db, create_test_csv):
    sample_tea_profiles_data = get_sample_tea_profiles_data()
    csv_file = create_test_csv(TeaProfileModel, sample_tea_profiles_data)

    # Monkeypatch insert_into_staging to raise an error.
    def fake_insert_into_staging(*args, **kwargs):
        raise RuntimeError("Forced failure for coverage.")

    monkeypatch.setattr(ingest_module, "insert_into_staging", fake_insert_into_staging)

    # Ingest data from the test CSV.
    ingest_data(
        create_test_db,
        csv_file, 
        TeaProfileModel, 
        [
            field for field in REQUIRED_TEA_PROFILE_MODEL_FIELDS 
            if field != TeaProfileModelFields.ID
        ], 
        [TeaProfileModelFields.NAME]
    )

    # After rollback, the table should be empty.
    num_rows = create_test_db.execute(text("SELECT COUNT(*) FROM tea_profiles")).scalar()
    assert num_rows == 0