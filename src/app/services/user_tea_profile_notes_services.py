# Layer 2 (Services / middle layer): Contains custom exception handlers to express 
# meaningful business logic failures. Layer 2 will turn them into HTTP responses.
#
# Domain exceptions are expressions of semantic intent rather than behavior containers, 
# so these will generally be sparse/bare.

from uuid import UUID
from fastapi import HTTPException
from starlette import status

from src.db.repositories.user_tea_profile_notes_repository import (
    UserTeaProfileNotesRepository
)
from src.api.schemas.user_tea_profile_notes_schema import (
    UserTeaProfileNotesInboundSchema,
    UserTeaProfileNotesOutboundSchema,
)
from src.app.errors import (
    UserTeaProfileNotesNotFoundError,
    UserTeaProfileNotesQueryError,
    UserTeaProfileNotesAlreadyExistError
)

class UserTeaProfileNotesService:
    def __init__(self, repo: UserTeaProfileNotesRepository):
        self._repo = repo

    def get_by_user_and_tea_profile_id(
        self,
        user_id: UUID,
        tea_profile_id: int,
    ) -> UserTeaProfileNotesOutboundSchema:

        try:
            user_tea_profile_notes = self._repo.get_by_user_and_tea_profile_id(
                user_id, tea_profile_id
            )
            return UserTeaProfileNotesOutboundSchema.model_validate(user_tea_profile_notes)

        except UserTeaProfileNotesNotFoundError: # pragma: no cover
            raise HTTPException( 
                status_code = status.HTTP_404_NOT_FOUND,
                detail = "No notes found for this tea.",
            )

        except UserTeaProfileNotesQueryError: # pragma: no cover
            raise HTTPException( 
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = "Failed to fetch user tea profile notes.",
            )

    def get_by_user_id(self, user_id: UUID) -> list[UserTeaProfileNotesOutboundSchema]:

        try:
            user_tea_profile_notes = self._repo.get_by_user_id(user_id)
            return [
                UserTeaProfileNotesOutboundSchema.model_validate(entry)
                for entry in user_tea_profile_notes
            ]

        except UserTeaProfileNotesQueryError: # pragma: no cover
            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = "Failed to fetch user tea profile notes.",
            )

    def create(
        self,
        user_id: UUID,
        tea_profile_id: int,
        inbound_schema: UserTeaProfileNotesInboundSchema,
    ) -> UserTeaProfileNotesOutboundSchema:

        try:
            user_tea_profile_notes = self._repo.create(user_id, tea_profile_id, inbound_schema)
            return UserTeaProfileNotesOutboundSchema.model_validate(user_tea_profile_notes)

        except UserTeaProfileNotesAlreadyExistError: # pragma: no cover
            raise HTTPException(
                status_code = status.HTTP_409_CONFLICT,
                detail = "User tea profile notes already exist for this tea profile id."
            )

        except UserTeaProfileNotesQueryError: # pragma: no cover
            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = "Failed to create user tea profile notes.",
            )

    def update(
        self,
        user_id: UUID,
        note_id: UUID,
        inbound_schema: UserTeaProfileNotesInboundSchema,
    ) -> UserTeaProfileNotesOutboundSchema:

        try:
            user_tea_profile_notes = self._repo.get_by_note_id(note_id)

            # Ownership check
            if user_tea_profile_notes.user_id != user_id:
                raise HTTPException(
                    status_code = status.HTTP_403_FORBIDDEN,
                    detail = "You do not have permission to modify this note.",
                )

            updated_user_tea_profile_notes = self._repo.update(note_id, inbound_schema)
            return UserTeaProfileNotesOutboundSchema.model_validate(updated_user_tea_profile_notes)

        except UserTeaProfileNotesNotFoundError: # pragma: no cover
            raise HTTPException( 
                status_code = status.HTTP_404_NOT_FOUND,
                detail = "Note not found.",
            )

        except UserTeaProfileNotesQueryError: # pragma: no cover
            raise HTTPException( 
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = "Failed to update user tea profile notes.",
            )

    def delete(
        self,
        user_id: UUID,
        note_id: UUID,
    ) -> None:

        try:
            user_tea_profile_notes = self._repo.get_by_note_id(note_id)

            # Ownership check
            if user_tea_profile_notes.user_id != user_id:
                raise HTTPException(
                    status_code = status.HTTP_403_FORBIDDEN,
                    detail = "You do not have permission to delete this note.",
                )

            self._repo.delete(note_id)

        except UserTeaProfileNotesNotFoundError: # pragma: no cover
            raise HTTPException( 
                status_code = status.HTTP_404_NOT_FOUND,
                detail = "Note not found.",
            )

        except UserTeaProfileNotesQueryError: # pragma: no cover
            raise HTTPException( 
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = "Failed to delete user tea profile notes.",
            )
