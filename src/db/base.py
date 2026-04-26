from sqlalchemy.orm import DeclarativeBase

# Base class for all models. All tables will inherit from this. It
# registers models so SQLAlchemy knows how to map them to actual
# database tables.
class Base(DeclarativeBase):
    """Shared SQLAlchemy declarative base class."""
    pass