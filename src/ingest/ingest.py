import logging

from src.ingest.staging import create_staging_table, insert_into_staging
from src.ingest.validate import remove_duplicates
from src.ingest.upsert import upsert_from_staging
from src.utils.csv_utils import load_and_clean_csv

# use __name__ to get a logger named after the module we're in.
logger = logging.getLogger(__name__)

def ingest_data(session, csv_path: str, model, required_fields, conflict_cols: list[str]):
    df = load_and_clean_csv(csv_path, model, required_fields, conflict_cols)

    # logger.debug("Loaded DataFrame from CSV")
    # logger.debug(df)
    # logger.debug("DataFrame dtypes:")
    # logger.debug(df.dtypes)
    # logger.debug(f"DataFrame shape: {df.shape}")

    base_table_name = model.__tablename__

    try:
        create_staging_table(session, base_table_name)
        insert_into_staging(df, base_table_name + "_staging", model, session.bind)
        remove_duplicates(session, base_table_name)
        upsert_from_staging(session, base_table_name, model, conflict_cols)

        session.commit()

    except Exception as e:
        session.rollback()
        logger.exception("Ingestion failed.")

if __name__ == "__main__":
    raise RuntimeError(
        "This module provides ingestion utilities and is not meant to be executed directly. "
        "If you were attempting to ingest data, run the appropriate ingestion runner ",
        "instead (Ex: src.app.ingest_tea_profiles to ingest tea_profiles data)."
    )
