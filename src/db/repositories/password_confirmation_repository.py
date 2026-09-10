from datetime import datetime, timezone, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from src.db.models.auth.password_confirmation_model import PasswordConfirmationModel


class PasswordConfirmationRepository:

    def __init__(self, session: Session):
        self.session = session


    def create_confirmation(self, user_id: UUID) -> PasswordConfirmationModel:
        confirmation = PasswordConfirmationModel(user_id = user_id)

        self.session.add(confirmation)

        return confirmation


    def is_confirmation_valid(self, user_id: UUID) -> bool:
        record = (
            self.session.query(PasswordConfirmationModel)
            .filter_by(user_id = user_id)
            .order_by(PasswordConfirmationModel.created_at.desc())
            .first()
        )

        if record is None:
            return False

        now = datetime.now(timezone.utc)

        created_at = record.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo = timezone.utc)

        return (now - created_at) <= timedelta(minutes = 5)
