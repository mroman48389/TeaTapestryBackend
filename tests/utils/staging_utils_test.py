import pytest
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

from src.utils.staging_utils import get_staging_table_name

@pytest.mark.parametrize(
    "dialect, expected, raises",
    [
        ("postgresql", "staging.test_table_staging", None),
        ("sqlite", "test_table_staging", None),
        ("other", None, NotImplementedError),
    ],
)
def test_get_staging_table_name(dialect, expected, raises):
    # Use a safe SQLite engine to avoid PostgreSQL setup but 
    # force dialect to 'postgresql' to cover that branch.
    engine = create_engine("sqlite:///:memory:")
    engine.dialect.name = dialect

    session = Session(bind = engine)

    if raises:
        with pytest.raises(raises):
            get_staging_table_name(session, "test_table")

    else:
        value = get_staging_table_name(session, "test_table")
        assert value == expected
