import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.db.base import Base

# SQLAlchemy blueprint for user table. This schema defines how data is stored in the database.
class UserInternalModel(Base):
    # SQLAlchemy needs this dunder to be called tablename to do its mapping.
    __tablename__ = "users"

    # PG_UUID gives better performance, native UUID storage, and no casting issues for Postgres,
    # and SQLite accepts it.
    #
    # default = uuid.uuid4 will auto generate a new UUID when a new user is added. Note this is 
    # a function reference so that SQLAlchemy generates a new UUID each time.
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid = True), 
        primary_key = True, 
        default = uuid.uuid4,
    )
    
    email: Mapped[str] = mapped_column(
        String,
        unique = True,
        nullable = False,
    )

    hashed_password: Mapped[str] = mapped_column(
        String,
        nullable = False,
    )

    display_name: Mapped[str] = mapped_column(
        String,
        nullable = False,
    )

    # DateTime(timezone = True) and datetime.now(timezone.utc) give us 
    # timezone-aware UTC timestamps.
    #
    # Again, we use a lambda function to pass the function reference so SQLAlchemy 
    # generates a new datetime each time.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone = True),
        default = lambda: datetime.now(timezone.utc),
        nullable = False,
    )

    # onupdate = lambda: datetime.now(timezone.utc) means every time the user row 
    # is updated, updated_at will be set to the current UTC timestamp.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone = True),
        default = lambda: datetime.now(timezone.utc),
        onupdate = lambda: datetime.now(timezone.utc),
        nullable = False,
    )

    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone = True), 
        nullable = True
    )