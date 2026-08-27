from uuid import UUID
from sqlalchemy import delete
from sqlalchemy.orm import Session

from src.db.repositories.user_tea_profile_notes_repository import (
    UserTeaProfileNotesRepository
)

from src.db.models.auth.session_token_model import SessionTokenModel
from src.db.models.auth.verification_token_model import VerificationTokenModel
from src.db.models.auth.user_models import UserInternalModel

class _UserDeletionCommon:

    def __init__(
        self, 
        session: Session, 
        user_tea_profile_notes_repo: UserTeaProfileNotesRepository
    ):
        self.session = session
        self.user_tea_profile_notes_repo = user_tea_profile_notes_repo


    def _delete_user_generated_data(self, user_id: UUID) -> None:

        # We are legally required by CTDPA / CCPA / GDPR to provide a means for the 
        # user to delete anything they created in Tea Tapestry as well as anything 
        # classified as "personal data" (info that reveals device or 
        # network identity, login history, behavioral patterns,
        # authentication artifacts). The only things we don't have to delete is account
        # identity fields (unless the user chooses to delete their entire account).
        self.user_tea_profile_notes_repo.delete_by_user_id(user_id)

        # Delete session tokens.
        self.session.execute(
            delete(SessionTokenModel).where(SessionTokenModel.user_id == user_id)
        )

        # Delete verification tokens.
        self.session.execute(
            delete(VerificationTokenModel).where(VerificationTokenModel.user_id == user_id)
        )


class UserDataDeletionService(_UserDeletionCommon):

    def delete_user_data(self, user_id: UUID) -> None:

        self._delete_user_generated_data(user_id)

        self.session.commit()


class UserAccountDeletionService(_UserDeletionCommon):

    def delete_user_account(self, user_id: UUID) -> None:

        self._delete_user_generated_data(user_id)

        self.session.execute(
            delete(UserInternalModel).where(UserInternalModel.id == user_id)
        )

        self.session.commit()
