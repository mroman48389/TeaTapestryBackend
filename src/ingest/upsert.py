# Insert new rows into database.

from sqlalchemy import text

from src.utils.staging_utils import get_staging_table_name
from src.utils.model_utils import get_model_column_names_as_str
from src.utils.sql_dialect_utils import get_sql_from_dialect

def upsert_from_staging(session, base_table: str, model, conflict_cols: list[str]):
    staging_table = get_staging_table_name(session, base_table)

    columns = get_model_column_names_as_str(model, False)
    conflicts = ", ".join(conflict_cols)

    # ON CONFLICT (name) DO NOTHING; is a second line of
    # defense against duplicates. They should be gone and we
    # don't won't our pipeline to break if they aren't. Just
    # skip the data instead of erroring out if something
    # slipped by.
    #
    # Passing in the column names of the data we want to
    # upsert is less brittle than inserting the whole
    # staging table into the base_table because this won't
    # break if the staging and base tables have differing
    # numbers of columns or columns in different orders or
    # different columns altogether.
    sql = get_sql_from_dialect(
        session,
        f"""
            INSERT INTO {base_table} ({columns})
            SELECT {columns}
            FROM {staging_table}
            ON CONFLICT ({conflicts}) DO NOTHING;
        """,
        f"""
            INSERT OR IGNORE INTO {base_table} ({columns})
            SELECT {columns}
            FROM {staging_table};
        """
    )
    session.execute(text(sql))