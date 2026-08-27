from uuid import UUID
from fastapi import HTTPException
from starlette import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models.auth.session_token_model import SessionTokenModel
from src.db.models.auth.user_models import UserInternalModel
from src.db.models.auth.verification_token_model import VerificationTokenModel

from src.api.schemas.user_tea_profile_notes_schema import UserTeaProfileNotesOutboundSchema

from src.db.repositories.user_tea_profile_notes_repository import (
    UserTeaProfileNotesRepository
)

class UserDataExportService:
    
    # Pass in repository classes when we have them and otherwise pull data from the
    # session
    def __init__(
        self,
        session: Session, 
        user_tea_profile_notes_repo: UserTeaProfileNotesRepository,
    ):
        self.session = session
        self.user_tea_profile_notes_repo = user_tea_profile_notes_repo


    def _serialize_user(self, user: UserInternalModel) -> dict:

        # Pick out relevant fields manually, as this model may contain
        # sensitive info we can't leak.
        return {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
            "last_login": (
                user.last_login.isoformat() if user.last_login else None
            ),
            "is_verified": user.is_verified,
            "verified_at": (
                user.verified_at.isoformat() if user.verified_at else None
            ),
        }


    def _serialize_session_tokens(
        self, 
        session_tokens: list[SessionTokenModel]
    ) -> list[dict]:

        # Pick out relevant fields manually, as this model may contain
        # sensitive info we can't leak.
        return [
            {
                "id": str(token.id),
                "created_at": token.created_at.isoformat(),
                "expires_at": token.expires_at.isoformat(),
                "revoked_at": (
                    token.revoked_at.isoformat() 
                    if token.revoked_at else None
                ),
                "refresh_token_id": str(token.refresh_token_id),
                "user_agent": token.user_agent,
                "ip_address": token.ip_address,
            }
            for token in session_tokens
        ]


    def _serialize_verification_tokens(
        self, 
        verification_tokens: list[VerificationTokenModel]
    ) -> list[dict]:

        return [
            {
                "id": str(token.id),
                "expires_at": token.expires_at.isoformat(),
                "used": token.used,
                "purpose": token.purpose,
            }
            for token in verification_tokens
        ]


    def _serialize_user_tea_profile_notes(
        self, 
        user_tea_profile_notes: list[UserTeaProfileNotesOutboundSchema]
    ) -> list[dict]:
        # For most things (esp auth-related ones), it's better to explicitly 
        # serialize so we don't accidentally leak sensitive fields. User tea 
        # profile notes should never have anything security-related in it, 
        # so dumping the model should be fine.
        return [notes.model_dump() for notes in user_tea_profile_notes]


    def export_user_data(self, user_id: UUID) -> dict:
        user = self.session.scalar(
            select(UserInternalModel).where(UserInternalModel.id == user_id)
        )

        if user is None:
            raise HTTPException(
                status_code = status.HTTP_404_NOT_FOUND,
                detail = "User not found."
            )

        session_tokens = list(self.session.scalars(
            select(SessionTokenModel).where(SessionTokenModel.user_id == user_id)
        ))

        verification_tokens = list(self.session.scalars(
            select(VerificationTokenModel).where(VerificationTokenModel.user_id == user_id)
        ))

        user_tea_profile_notes = self.user_tea_profile_notes_repo.get_by_user_id(user_id)
        user_tea_profile_notes_outbound = [
            UserTeaProfileNotesOutboundSchema.model_validate(notes) 
            for notes in user_tea_profile_notes
        ]
        
        return {
            "user": self._serialize_user(user),
            "session_tokens": self._serialize_session_tokens(session_tokens),
            "verification_tokens": self._serialize_verification_tokens(verification_tokens),
            "user_tea_profile_notes": self._serialize_user_tea_profile_notes(
                user_tea_profile_notes_outbound
            ),
        }
