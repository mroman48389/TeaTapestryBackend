from uuid import UUID

from sqlalchemy.orm import Session

from src.db.models.auth.password_confirmation_model import PasswordConfirmationModel
from src.constants.auth_constants import FRESH_LOGIN_WINDOW_TD
from src.utils.time_utils import is_younger_than


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

        return is_younger_than(record.created_at, FRESH_LOGIN_WINDOW_TD, True)
