# Create and manage staging table.

from sqlalchemy import text

from src.utils.staging_utils import get_staging_table_name

def create_staging_table(session, base_table: str):
    staging_table = get_staging_table_name(base_table)

    # CREATE SCHEMA IF NOT EXISTS staging; -->
    #
    #   Ensure staging scheme exists.
    #
    # CREATE UNLOGGED TABLE IF NOT EXISTS {staging_table}
    # (LIKE {base_table} INCLUDING ALL); -->
    #
    #   Create table with same structure as base table.
    #
    #   UNLOGGED is not crash-safe but allows for faster
    #   inserting, which is ok for temporary staging.
    #
    #   INCLUDING ALL copies all attributes of the base
    #   table (indices, defaults, constraints, etc.)
    #
    # TRUNCATE TABLE {staging_table}; -->
    #
    #   Clear old data.
    #
    session.execute(text(f"""
        CREATE SCHEMA IF NOT EXISTS staging;
        CREATE UNLOGGED TABLE IF NOT EXISTS {staging_table}
        (LIKE {base_table} INCLUDING ALL);
        TRUNCATE TABLE {staging_table};
    """))

def insert_into_staging(df, table_name: str, engine):
    # Load Pandas DataFrame into staging table.

    # Push DataFrame rows into SQLAlchemy database.
    #
    # con=engine passes the SQLAlchemy engine connection.
    #
    # index=False prevents writing the DataFrame index as
    # a column.
    #
    # method="multi" uses batched inserts for efficiency.
    df.to_sql(
        name = table_name,
        con = engine,
        schema = "staging",
        if_exists = "append",
        index = False,
        method= " multi"
    )