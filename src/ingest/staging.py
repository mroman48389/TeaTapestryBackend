# Create and manage staging table.

from sqlalchemy import text

from src.utils.staging_utils import get_staging_table_name
from src.utils.model_utils import get_dtype_mapping

def create_staging_table(session, base_table: str):
    staging_table = get_staging_table_name(session, base_table)

    # For the PostgreSQL dialect:
    #
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
    dialect = session.bind.dialect.name

    if dialect == "postgresql":
        session.execute(text(f"""
            CREATE SCHEMA IF NOT EXISTS staging;
            CREATE UNLOGGED TABLE IF NOT EXISTS {staging_table}
            (LIKE {base_table} INCLUDING ALL);
            TRUNCATE TABLE {staging_table};
        """))

    elif dialect == "sqlite":
        session.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {staging_table} AS
            SELECT * FROM {base_table} WHERE 0;
        """))
        session.execute(text(f"DELETE FROM {staging_table};"))

    # Necessary because of the CREATE SCHEMA
    session.commit()

def insert_into_staging(df, table_name: str, model, engine):
    
    # Schema alignment

    # Ensure DataFrame has all model columns (minus the primary key). When 
    # SQLite is used, it clones the schema of tea_profiles
    # in create_staging_table, including the id column. This
    # won't affect PostgreSQL, which will automatically
    # generate the id.
    cols = [col.name for col in model.__table__.columns if not col.primary_key]

    # reorder to match table schema
    df = df[cols]  
 
    # Load Pandas DataFrame into staging table.

    # Push DataFrame rows into SQLAlchemy database.
    #
    # con=engine passes the SQLAlchemy engine connection.
    #
    # index=False prevents writing the DataFrame index as
    # a column.
    #
    # method="multi" uses batched inserts for efficiency.
    kwargs = {
        "name": table_name,
        "con": engine,
        "if_exists": "append",
        "index": False,
        "dtype": get_dtype_mapping(model),
        "method": "multi",
    }

    # Add schema for PostgreSQL and leave out completely for SQLite,
    # which does not support staging.
    if engine.dialect.name == "postgresql":
        kwargs["schema"] = "staging"

    # print("DataFrame about to insert:\n", df)
    # print("DataFrame dtypes:\n", df.dtypes)

    df.to_sql(**kwargs)