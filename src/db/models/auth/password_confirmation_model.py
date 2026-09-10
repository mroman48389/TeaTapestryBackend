from datetime import datetime, timezone
import uuid

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.db.base import Base


class PasswordConfirmationModel(Base):
    __tablename__ = "password_confirmations"

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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone = True),
        nullable = False,
        default = lambda: datetime.now(timezone.utc)
    )
