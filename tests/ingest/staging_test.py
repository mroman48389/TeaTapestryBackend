from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
import pandas as pd

from src.ingest.staging import create_staging_table
from src.ingest.staging import insert_into_staging
from src.db.models.tea_profiles_model import TeaProfileModel

def test_create_staging_table_postgres(monkeypatch):
    executed = {}

    # Create a mock execute so we don't need to set up a real
    # example with a PostgreSQL database. We only need to test that our
    # PostgreSQL branch of create_staging_table gets hit.
    def mock_execute(self, statement, *args, **kwargs):
        executed["sql"] = str(statement)
        class DummyResult:
            def scalar(self): 
                return None
        return DummyResult()

    # Calls to session.execute will now use the mock execute.
    monkeypatch.setattr(Session, "execute", mock_execute)

    # Use a safe SQLite engine to avoid PostgreSQL setup but 
    # force dialect to 'postgresql' to cover that branch.
    engine = create_engine("sqlite:///:memory:")
    engine.dialect.name = "postgresql"

    session = Session(bind = engine)

    create_staging_table(session, "tea_profiles")

    # This is the first line in the session.execute call of the PostgreSQL branch
    # of the logic. It should be in the executed dict.
    assert "CREATE SCHEMA IF NOT EXISTS staging;" in executed["sql"]

def test_insert_into_staging_postgres(monkeypatch):
    # Use a safe SQLite engine to avoid PostgreSQL setup but 
    # force dialect to 'postgresql' to cover that that branch.
    engine = create_engine("sqlite:///:memory:")
    engine.dialect.name = "postgresql" 

    # Minimal DataFrame.
    row: dict[str, Any] = {
        col.name: None for col in TeaProfileModel.__table__.columns if not col.primary_key
    }
    row["name"] = "Dragonwell"
    df = pd.DataFrame([row])
    # df = pd.DataFrame([{"name": "Dragonwell"}])

    # Create a mock to_sql so we don't have to execute a real to_sql
    captured = {}
    def mock_to_sql(self, name, *args, **kwargs):
        captured.update(kwargs)
        captured["name"] = name

    # Calls to df.to_sql will now use the mock to_sql.
    monkeypatch.setattr(pd.DataFrame, "to_sql", mock_to_sql)

    # make_df_sqlite_compatible(df, TeaProfileModel)

    df = insert_into_staging(df, "tea_profiles_staging", TeaProfileModel, engine)

    # Assert schema was added for PostgreSQL.
    assert captured["schema"] == "staging"
    assert captured["name"] == "tea_profiles_staging"