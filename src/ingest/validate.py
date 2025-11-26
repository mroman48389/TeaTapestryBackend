# Clean and deduplicate data.

from sqlalchemy import text

from src.utils.staging_utils import get_staging_table_name
from src.utils.sql_dialect_utils import get_sql_from_dialect

def remove_duplicates(session, base_table: str):
    staging_table = get_staging_table_name(session, base_table)

    # In case the CSV had a duplicate tea, delete it from the
    # staging table. Look for the "name" column in the base
    # table for the tea name. 
    #
    # For the PostgreSQL dialect:
    #
    # SELECT name FROM {base_table} -->
    #   Returns all values in the "name" column of the
    #   database as a result set.
    #
    # WHERE name IN -->
    #   Check each name value of the staging table from the
    #   aforementioned result set.
    #
    # The same raw SQL works in both dialects this time!
    sql = get_sql_from_dialect(
        session,
        f"""
            DELETE FROM {staging_table}
            WHERE name IN (SELECT name FROM {base_table});
        """,
        f"""
            DELETE FROM {staging_table}
            WHERE name IN (SELECT name FROM {base_table});
        """ 
    )
    session.execute(text(sql))
