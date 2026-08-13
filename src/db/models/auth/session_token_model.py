import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.db.base import Base

class SessionTokenModel(Base):
    __tablename__ = "session_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid = True),
        primary_key = True,
        default = uuid.uuid4
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid = True),
        ForeignKey("users.id", ondelete = "CASCADE"),
        nullable = False
    )

    # The hashed refresh token itself. Never store the raw refresh
    # token in case the database is compromised. When a refresh request
    # is made, the incoming token is hashed and compared to this token_hash.
    refresh_token_hash: Mapped[str] = mapped_column(String, nullable = False)

    # Used for rotating refresh tokens and detecting token reuse. default 
    # ensures that login creates a refresh token ID automatically and we don't 
    # need to manually set it during session creation.
    refresh_token_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid = True),
        default = uuid.uuid4,
        nullable = False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone = True),
        default = lambda: datetime.now(timezone.utc),
        nullable = False
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone = True),
        nullable = False
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone = True),
        nullable = True
    )

    # browser, OS, device type; For ex, Chrome/126.0.0.0 Safari/537.36.
    # Helps detect suspicious logins, debugging, audits.
    user_agent: Mapped[str | None] = mapped_column(String, nullable = True)

    # Network address the request came from. Helps detect suspicious logins,
    # stolen refresh tokens. Provides device and session history.
    ip_address: Mapped[str | None] = mapped_column(String, nullable = True)
