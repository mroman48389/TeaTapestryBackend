from sqlalchemy.dialects import postgresql
from src.db.types.sqlite_compatible_array import SQLiteCompatibleArray

def test_load_dialect_impl_postgres():
    # We use type_ because type itself is a reserved word.
    type_ = SQLiteCompatibleArray()
    dialect = postgresql.dialect()
    impl = type_.load_dialect_impl(dialect)
    # For PostgreSQL, the impl should be an ARRAY of String
    assert "ARRAY" in str(impl)

def test_process_bind_param_postgres():
    # We use type_ because type itself is a reserved word.
    type_ = SQLiteCompatibleArray()
    dialect = postgresql.dialect()
    value = ["nutty", "sweet"]
    # For Postgres, the list should be returned unchanged
    result = type_.process_bind_param(value, dialect)
    assert result == ["nutty", "sweet"]