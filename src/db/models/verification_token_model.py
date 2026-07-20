import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.db.base import Base

class VerificationToken(Base):
    __tablename__ = "verification_tokens"

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

    token_hash: Mapped[str] = mapped_column(String, nullable = False)

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone = True),
        nullable = False
    )

    # Prevents replay atteacks, duplicate verification, token reuse.
    used: Mapped[bool] = mapped_column(Boolean, default = False, nullable = False)

    # Allows us to distinguish password reset, email changes, account deletion, 2FA,
    # magic login verifications.
    purpose: Mapped[str] = mapped_column(String, nullable = False)
