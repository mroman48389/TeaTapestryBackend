from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from src.db.models.auth.dsar_log_model import DSARLogModel
from src.constants.dsar_constants import (
    STATUS_PENDING,
    STATUS_FULFILLED,
    STATUS_FAILED,
)


class DSARLogRepository:

    def __init__(self, session: Session):
        self.session = session


    def create_log(
        self, 
        user_id: UUID, 
        request_type: str, 
        notes: Optional[str] = None
    ) -> DSARLogModel:
        
        log = DSARLogModel(
            user_id = user_id,
            request_type = request_type,
            status = STATUS_PENDING,
            notes = notes,
        )

        self.session.add(log)
        self.session.commit()
        self.session.refresh(log)

        return log


    def mark_fulfilled(self, log_id: UUID) -> None:

        log = self.session.get(DSARLogModel, log_id)

        if log:
            log.status = STATUS_FULFILLED
            log.fulfilled_at = datetime.now(timezone.utc)
            self.session.commit()


    def mark_failed(self, log_id: UUID, notes: Optional[str] = None) -> None:

        log = self.session.get(DSARLogModel, log_id)

        if log:
            log.status = STATUS_FAILED
            log.notes = notes
            log.fulfilled_at = datetime.now(timezone.utc)
            self.session.commit()


    def get_logs_for_user(self, user_id: UUID) -> List[DSARLogModel]:

        return (
            self.session.query(DSARLogModel)
            .filter(DSARLogModel.user_id == user_id)
            .order_by(DSARLogModel.requested_at.desc())
            .all()
        )
    