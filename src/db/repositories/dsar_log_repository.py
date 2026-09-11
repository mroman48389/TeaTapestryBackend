from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from src.db.models.auth.dsar_log_model import DSARLogModel
from src.constants.dsar_constants import (
    DSAR_STATUS_PENDING,
    DSAR_STATUS_FULFILLED,
    DSAR_STATUS_FAILED,
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
            status = DSAR_STATUS_PENDING,
            notes = notes,
        )

        self.session.add(log)

        # Flush the new DSAR log to the database so it receives a real primary key
        # and becomes queryable within the current transaction. Without flush(),
        # SQLAlchemy only stages the INSERT in memory, meaning mark_fulfilled() /
        # mark_failed() would not be able to load the row via session.get(log_id).
        self.session.flush() 

        return log


    def mark_fulfilled(self, log_id: UUID) -> None:

        log = self.session.get(DSARLogModel, log_id)

        if log:
            log.status = DSAR_STATUS_FULFILLED
            log.fulfilled_at = datetime.now(timezone.utc)


    def mark_failed(self, log_id: UUID, notes: Optional[str] = None) -> None:

        log = self.session.get(DSARLogModel, log_id)

        if log:
            log.status = DSAR_STATUS_FAILED
            log.notes = notes
            log.fulfilled_at = None


    def get_logs_for_user(self, user_id: UUID) -> List[DSARLogModel]:

        return (
            self.session.query(DSARLogModel)
            .filter(DSARLogModel.user_id == user_id)
            .order_by(DSARLogModel.requested_at.desc())
            .all()
        )
    