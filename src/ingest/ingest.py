from src.utils.session_utils import get_session
from src.ingest.staging import create_staging_table, insert_into_staging
from src.ingest.validate import remove_duplicates
from src.ingest.upsert import upsert_from_staging
from src.utils.csv_utils import load_and_clean_csv


def ingest_data(csv_path: str, model, required_fields, conflict_cols: list[str]):
    df = load_and_clean_csv(csv_path, model, required_fields)

    base_table_name = model.__tablename__

    with get_session() as session:
        try:
            create_staging_table(session, base_table_name)
            insert_into_staging(df, base_table_name + "_staging", session.bind)
            remove_duplicates(session, base_table_name)
            upsert_from_staging(session, base_table_name, model, conflict_cols)

            session.commit()

        except Exception as e:
            session.rollback()
            print(f"Ingestion failed: {e}")