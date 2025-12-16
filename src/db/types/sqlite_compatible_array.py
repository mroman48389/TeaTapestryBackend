from sqlalchemy.types import TypeDecorator, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import String

from src.constants.model_metadata_constants import DELIMITER_VALUE

class SQLiteCompatibleArray(TypeDecorator):
    """
        Use ARRAY for PostgreSQL in production and integration tests.
        Use Text for SQLite for unit tests.
    """

    # By default, treat the value as Text. TypeDecorator requires a
    # base implementation type.
    impl = Text
    cache_ok = True # tell SQLAlchemy this type can be used in query cache keys

    def load_dialect_impl(self, dialect):
        # Use Text for SQLite and ARRAY for PostgreSQL
        if dialect.name == "sqlite":
            return dialect.type_descriptor(Text())
        
        else:
            return dialect.type_descriptor(ARRAY(String()))

    # Convert the Python object into something the database can store.
    # This is run when a value is sent to the database (e.g. with
    # session.commit()).
    #
    # Ex: ["nutty", "sweet"] --> "nutty;sweet"
    #
    def process_bind_param(self, value, dialect):
        # For SQLite, serialize the list into a semicolon-delimited string.
        if (dialect.name == "sqlite") and (value is not None):
            return DELIMITER_VALUE.join(value)
        
        # For PostgreSQL, pass the list as-is, since PostgreSQL understands
        # arrays.
        return value

    # Convert the database value back into a Python object.
    # This is run when a value is retrieved from the database (e.g. with
    # session.query(...).first()).
    #
    # Ex: "nutty;sweet" --> ["nutty", "sweet"]
    #
    def process_result_value(self, value, dialect):
        # For SQLite, deserialize the semicolon-delimited string back into a list.
        if (dialect.name == "sqlite") and (value is not None):
            return value.split(DELIMITER_VALUE)
        
        # For PostgreSQL, retrieve the list as-is.
        return value