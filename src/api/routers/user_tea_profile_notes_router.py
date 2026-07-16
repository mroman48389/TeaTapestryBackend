from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from uuid import UUID
from starlette import status
import sentry_sdk
import logging

from src.api.schemas.user_tea_profile_notes_schema import (
    UserTeaProfileNotesInboundSchema,
    UserTeaProfileNotesOutboundSchema,
)
from src.app.services.user_tea_profile_notes_services import (
    UserTeaProfileNotesService,
)
from src.db.repositories.user_tea_profile_notes_repository import (
    UserTeaProfileNotesRepository,
)
from src.utils.session_utils import get_session
from src.api.dependencies.auth_dependencies import get_current_user
from src.db.models.user_models import UserInternalModel
from src.core.rate_limit.config_rate_limit import (
    HIGH_RATE_LIMIT, 
    LOW_RATE_LIMIT, 
    VERY_LOW_RATE_LIMIT
)
from src.core.rate_limit.setup_rate_limit import rate_limiter
from src.constants.route_constants import USER_TEA_PROFILE_NOTES_PREFIX

# use __name__ to get a logger named after the module we're in.
logger = logging.getLogger(__name__)

router = APIRouter(prefix = USER_TEA_PROFILE_NOTES_PREFIX, tags = ["user_tea_profile_notes"])


def _get_service(session: Session) -> UserTeaProfileNotesService:
    repo = UserTeaProfileNotesRepository(session)
    return UserTeaProfileNotesService(repo)


@router.get(
    "/{tea_profile_id}",
    response_model = UserTeaProfileNotesOutboundSchema,
    status_code = status.HTTP_200_OK,
)
@rate_limiter.limit(HIGH_RATE_LIMIT)
def get_user_tea_profile_notes_for_tea(
    request: Request, # required for rate limiter
    tea_profile_id: int,
    current_user: UserInternalModel = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    # Get user tea profile notes for a particular tea and user.
    service = _get_service(session)

    with sentry_sdk.start_span(op = "endpoint", name = "get_user_tea_profile_notes_for_tea"):
        return service.get_by_user_and_tea_profile_id(current_user.id, tea_profile_id)


@router.get(
    "/",
    response_model = list[UserTeaProfileNotesOutboundSchema],
    status_code = status.HTTP_200_OK,
)
@rate_limiter.limit(HIGH_RATE_LIMIT)
def get_all_user_tea_profile_notes(
    request: Request, # required for rate limiter
    current_user: UserInternalModel = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    # Get all user tea profiles notes for the user. To test in Postman, call login first so
    # the access and refresh tokens are stored in the Cookie Jar and Postman attaches the
    # cookies.
    service = _get_service(session)

    with sentry_sdk.start_span(op = "endpoint", name = "get_all_user_tea_profile_notes"):
        return service.get_by_user_id(current_user.id)


@router.post(
    "/{tea_profile_id}",
    response_model = UserTeaProfileNotesOutboundSchema,
    status_code = status.HTTP_201_CREATED,
)
@rate_limiter.limit(LOW_RATE_LIMIT)
def create_user_tea_profile_notes(
    request: Request, # required for rate limiter
    tea_profile_id: int,
    inbound_schema: UserTeaProfileNotesInboundSchema,
    current_user: UserInternalModel = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    # Create user tea profile notes.
    service = _get_service(session)

    with sentry_sdk.start_span(op = "endpoint", name = "create_user_tea_profile_notes"):
        return service.create(current_user.id, tea_profile_id, inbound_schema)


@router.patch(
    "/{note_id}",
    response_model = UserTeaProfileNotesOutboundSchema,
    status_code = status.HTTP_200_OK,
)
@rate_limiter.limit(LOW_RATE_LIMIT)
def update_user_tea_profile_notes(
    request: Request, # required for rate limiter
    note_id: UUID,
    inbound_schema: UserTeaProfileNotesInboundSchema,
    current_user: UserInternalModel = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    # Update existing user tea profile notes.
    service = _get_service(session)

    with sentry_sdk.start_span(op = "endpoint", name = "update_user_tea_profile_notes"):
        return service.update(current_user.id, note_id, inbound_schema)


@router.delete(
    "/{note_id}",
    status_code = status.HTTP_204_NO_CONTENT,
)
@rate_limiter.limit(VERY_LOW_RATE_LIMIT)
def delete_user_tea_profile_notes(
    request: Request, # required for rate limiter
    note_id: UUID,
    current_user: UserInternalModel = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    # Delete existing user tea profile notes.
    service = _get_service(session)

    with sentry_sdk.start_span(op = "endpoint", name = "delete_user_tea_profile_notes"):
        service.delete(current_user.id, note_id)
        return None
