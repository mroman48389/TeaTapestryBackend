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

    # display_name does not have to be unique. Allow letters, numbers, hyphens, whitespace. 
    # Used to identify the user in UI  such as the app bar, user profile display, 
    # comments, reviews, chatting.
    display_name: Mapped[str] = mapped_column(
        String,
        nullable = False,
    )

    # username must be unique. Allows lowercase letters, numbers, underscores, hyphens. Normalized and 
    # stored as all lowercase. It will be used for looking up users, querying databases, URLs, mentions.
    username: Mapped[str] = mapped_column(
        String(30),
        unique = True,
        nullable = False,
        index = True
    )

    bio: Mapped[str | None] = mapped_column(
        String(500),
        nullable = True,
    )

    # Reference to where the avatar image is stored. (Currently, we automatically generate
    # initials instead. If we implement this in the future, we need a way of preventing
    # inappropriate image uploads and / or reporting such things).
    avatar_url: Mapped[str | None] = mapped_column(
        String,
        nullable = True,
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

    # For gating features, login flows, JWT claims, UI banners.
    is_verified: Mapped[bool] = mapped_column(
        default = False,
        nullable = False,
    )

    # For analytics, fraud detection, debugging, verified badges.
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone = True),
        nullable = True,
    )
