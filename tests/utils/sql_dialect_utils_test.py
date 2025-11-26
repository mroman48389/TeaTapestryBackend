import pytest
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

from src.utils.sql_dialect_utils import get_sql_from_dialect

@pytest.mark.parametrize(
    "dialect,expected,raises",
    [
        ("postgresql", "PostgreSQL SQL string", None),
        ("sqlite", "SQLite SQL string", None),
        ("other", None, NotImplementedError),
    ],
)
def test_get_sql_from_dialect(dialect, expected, raises):
    # Use a safe SQLite engine to avoid PostgreSQL setup but 
    # force dialect to 'postgresql' to cover that branch.
    engine = create_engine("sqlite:///:memory:")
    engine.dialect.name = dialect

    session = Session(bind = engine)

    if raises:
        with pytest.raises(raises):
            get_sql_from_dialect(session, "PostgreSQL SQL string", "SQLite SQL string")

    else:
        value = get_sql_from_dialect(session, "PostgreSQL SQL string", "SQLite SQL string")
        assert value == expected
