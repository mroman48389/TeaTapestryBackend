from datetime import datetime, timezone
import uuid

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.constants.dsar_constants import DSAR_STATUS_PENDING
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

# Under CTDPA, CCPA / CPRA, GDPR, etc., users have legal rights called DSARs 
# (Data Subject Access Requests). Businesses must record related requests and 
# mark when they were fulfilled. We must be able to provide proof that these
# requests were fulfilled, and that is done with this table.
class DSARLogModel(Base):
    __tablename__ = "dsar_logs"

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

    request_type: Mapped[str] = mapped_column(
        String,
        nullable = False
    )

    status: Mapped[str] = mapped_column(
        String,
        nullable = False,
        default = DSAR_STATUS_PENDING
    )

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone = True),
        nullable = False,
        default = lambda: datetime.now(timezone.utc)
    )

    fulfilled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone = True),
        nullable = True
    )

    # Optional notes, such as error messages.
    notes: Mapped[str | None] = mapped_column(
        String,
        nullable = True
    )
