# Layer 3 (Database / SQLAlchemy / bottomost layer): This is where error handling starts. We
# catch raw SQLAlchemy errors and convert them into the domain errors that layer 2 deals
# with. This layer ensures raw SQL errors don't reach layer 1.

from __future__ import annotations

# later, once the user can add their own tea profiles: from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from uuid import UUID

from src.app.errors import (
    UserTeaProfileNotesNotFoundError,
    UserTeaProfileNotesQueryError,
    UserTeaProfileNotesAlreadyExistError
)
from src.db.models.user_tea_profile_notes_model import UserTeaProfileNotesModel 
from src.api.schemas.user_tea_profile_notes_schema import UserTeaProfileNotesInboundSchema

# A repository is a class tasked with talking to a database and returning domain objects. It
# should be the only place on the backend that knows how to query the DB, insert/update/delete,
# translate SQLAlchemy errors, and manage transactions. 
# 
# It's a class rather than a set of functions because it needs to work on a database session. 
# Without it, we'd need to pass a session into each function of said set. It's useful for testing.
#
# Use the primary key (note_id) whenever the resource already exists, because it is the most 
# stable, simple, efficient (due to indexing), canonical (the database guarantees its identity),
#  and unambiguous identifier. It is the most natural for REST endpoints we often have 
# /resource/{id}). Most repository methods should use this. 
# 
# Only use the natural composite key (user_id + tea_profile_id) when the resource does not exist 
# yet (such as on "create") or when you are locating notes by their domain meaning 
# (such as "get_by_user_and_tea_profile_id").
#
class UserTeaProfileNotesRepository:

    # Store database session.
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_note_id(self, note_id: UUID) -> UserTeaProfileNotesModel:
        try:
            user_tea_profile_notes = self._session.get(UserTeaProfileNotesModel, note_id)

            if user_tea_profile_notes is None:
                raise UserTeaProfileNotesNotFoundError(
                    f"User tea profile notes with id {note_id} were not found.",
                    details = {"note_id": note_id},
                )

            return user_tea_profile_notes

        except SQLAlchemyError as exc:
            raise UserTeaProfileNotesQueryError(
                "Failed to fetch user tea profile notes.",
                details = {"note_id": note_id},
            ) from exc

    # Gets one set of user tea profile notes with the specified user id and tea profile id. 
    # 
    # Since this is asking for a specific row of user tea profile notes, we will expect it to
    # exist and raise an exception if it does not.
    #
    # Getting an entire row rather than particular fields is predictable, easier to handle, 
    # easier to cache.
    #
    def get_by_user_and_tea_profile_id(
        self, 
        user_id: UUID, 
        tea_profile_id: int
    ) -> UserTeaProfileNotesModel:

        try:        
            user_tea_profile_notes = (
                self._session.query(UserTeaProfileNotesModel)
                .filter(
                    UserTeaProfileNotesModel.user_id == user_id,
                    UserTeaProfileNotesModel.tea_profile_id == tea_profile_id,
                )
                .one_or_none()
            )

            if user_tea_profile_notes is None:
                raise UserTeaProfileNotesNotFoundError(
                    f"User tea profile notes with the given user id {user_id} "
                    f"and tea profile id {tea_profile_id} were not found.",
                    details = {
                        "user_id": user_id,
                        "tea_profile_id": tea_profile_id
                    }
                )
            
            return user_tea_profile_notes
        
        except SQLAlchemyError as exc:
            raise UserTeaProfileNotesQueryError(
                "Failed to fetch user tea profile notes.",
                details = {
                    "user_id": user_id,
                    "tea_profile_id": tea_profile_id
                },
            ) from exc
        
    # Gets all user tea profile notes with a particular user id.
    #
    # Since this is asking for all user tea profile notes that match our filter, we will 
    # NOT expect any notes to exist and treat all outcomes as valid. 
    def get_by_user_id(self, user_id: UUID) -> list[UserTeaProfileNotesModel]:

        try:        
            return (
                self._session.query(UserTeaProfileNotesModel)
                .filter(
                    UserTeaProfileNotesModel.user_id == user_id,
                )
                .all()
            )
        
        except SQLAlchemyError as exc:
            raise UserTeaProfileNotesQueryError(
                "Failed to fetch user tea profile notes.",
                details = {
                    "user_id": user_id,
                },
            ) from exc
    
    # Create a new row of user tea profile notes.
    def create(
        self, 
        user_id: UUID, 
        tea_profile_id: int, 
        inbound_schema: UserTeaProfileNotesInboundSchema
    ) -> UserTeaProfileNotesModel:
        
        try:
            # Before creating the notes, make sure they don't already exist for the 
            # specified user and tea profile ids. If they do, raise a domain 
            # exception.
            existing_notes = (
                self._session.query(UserTeaProfileNotesModel)
                .filter_by(user_id = user_id, tea_profile_id = tea_profile_id)
                .one_or_none()
            )

            if existing_notes is not None:
                raise UserTeaProfileNotesAlreadyExistError(
                    f"User tea profile notes already exist for "
                    f"tea_profile_id = {tea_profile_id} and user_id = {user_id}"
                )

            # Create a new SQLAlchemy ORM object (instance of a database row) using
            # the user_id from the authenticated user and the tea_profile_id from the
            # route parameter for security. Everything else can come from the JSON the
            # client sends via inbound_schema. model_dump converts inbound_schema into a 
            # dict and ** expands that dict into keyword arguments so we don't need to 
            # explicitly pass in the rest of the fields.
            user_tea_profile_notes = UserTeaProfileNotesModel(
                user_id = user_id,
                tea_profile_id = tea_profile_id,
                **inbound_schema.model_dump()
            )

            self._session.add(user_tea_profile_notes)
            self._session.commit()
            self._session.refresh(user_tea_profile_notes)

            return user_tea_profile_notes

        except UserTeaProfileNotesAlreadyExistError:
            # Let the service layer handle this.
            raise

        except SQLAlchemyError as exc:
            self._session.rollback()

            raise UserTeaProfileNotesQueryError(
                "Failed to create user tea profile notes.",
                details = {
                    "user_id": user_id,
                    "tea_profile_id": tea_profile_id,
                },
            ) from exc

    # Update an existing row of user tea profile notes.
    def update(
        self, 
        note_id: UUID, 
        inbound_schema: UserTeaProfileNotesInboundSchema
    ) -> UserTeaProfileNotesModel:
        
        try:
            user_tea_profile_notes = self._session.get(UserTeaProfileNotesModel, note_id)

            if user_tea_profile_notes is None:
                raise UserTeaProfileNotesNotFoundError(
                    f"User tea profile notes with id {note_id} were not found.",
                    details = {"note_id": note_id},
                )

            for field, value in inbound_schema.model_dump().items():
                setattr(user_tea_profile_notes, field, value)

            self._session.commit()
            self._session.refresh(user_tea_profile_notes)

            return user_tea_profile_notes

        except SQLAlchemyError as exc:
            self._session.rollback()

            raise UserTeaProfileNotesQueryError(
                "Failed to update user tea profile notes.",
                details = {"note_id": note_id},
            ) from exc
    
    # Delete a row of user tea profile notes.
    def delete(self, note_id: UUID) -> None:

        try:
            user_tea_profile_notes = self._session.get(UserTeaProfileNotesModel, note_id)

            if user_tea_profile_notes is None:
                raise UserTeaProfileNotesNotFoundError(
                    f"User tea profile notes with id {note_id} were not found.",
                    details = {"note_id": note_id},
                )

            self._session.delete(user_tea_profile_notes)
            self._session.commit()

        except SQLAlchemyError as exc:
            self._session.rollback()

            raise UserTeaProfileNotesQueryError(
                "Failed to delete user tea profile notes.",
                details = {"note_id": note_id},
            ) from exc
