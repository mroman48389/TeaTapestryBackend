from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
import logging
from starlette import status
import sentry_sdk

from src.utils.session_utils import get_session
from src.db.models.user_models import UserInternalModel
from src.api.schemas.user_schema import (
    UserInboundSchema,
    UserOutboundSchema,
    LoginSchema
)
from src.utils.auth.password_utils import (
    hash_password, 
    validate_password_strength,
    verify_password
)
from src.core.rate_limit.setup_rate_limit import rate_limiter
from src.core.rate_limit.config_rate_limit import VERY_LOW_RATE_LIMIT

# use __name__ to get a logger named after the module we're in.
logger = logging.getLogger(__name__)

# Define group of routes with auth as their base path for documentation grouping.
router = APIRouter(prefix = "/auth", tags = ["auth"])

# request param is required by SlowAPI. Without it, we'll get an exception.
@router.post(
    "/signup", 
    response_model = UserOutboundSchema, 
    status_code = status.HTTP_201_CREATED
)
@rate_limiter.limit(VERY_LOW_RATE_LIMIT)
def signup(
    request: Request,
    payload: UserInboundSchema, 
    response: Response,
    session: Session = Depends(get_session)
):
    # We'll employ strict rate limiting (no reason to allow more than a few attempts 
    # a minute), and top-level Sentry observability.  
    # 
    # Etags, last-modified/cahce-control headers, head endpoints, and caching range 
    # from not applicable to harmful here. Sensitive information should never be
    # cached, and we are dealing with a POST, not a GET.
    #
    with sentry_sdk.start_span(op = "auth", name = "signup"):
        sentry_sdk.set_tag("endpoint", "signup")

        # Prevent caching of sensitive auth responses
        response.headers["Cache-Control"] = "no-store"

        validate_password_strength(payload.password)

        # The email format is already validated by EmailStr in UserInboundSchema, so 
        # check if the entered email exists already next. EmailStr checks things like
        # the presence of the @ symbol, valid domain, etc.
        existing_user = session.query(UserInternalModel).filter(
            UserInternalModel.email == payload.email
        ).first()

        if existing_user:
            raise HTTPException(
                status_code = status.HTTP_400_BAD_REQUEST,
                detail = "A user with this email address already exists."
            )

        # Hash the password.
        hashed_pw = hash_password(payload.password)

        # Insert the user into the DB.
        new_user = UserInternalModel(
            email = payload.email,
            hashed_password = hashed_pw,
        )

        try:
            session.add(new_user)
            session.commit()
            session.refresh(new_user)

            logger.info(f"New user created: {new_user.id}")

        except Exception:
            session.rollback()
            
            logger.exception("Unexpected error during signup.")

            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = "An unexpected error occurred while creating the account."
            )
        
        # Return the UserOutboundSchema
        return new_user

@router.post(
    "/login",
    status_code = status.HTTP_200_OK
)
@rate_limiter.limit(VERY_LOW_RATE_LIMIT)
def login(
    request: Request,
    payload: LoginSchema,
    response: Response,
    session: Session = Depends(get_session)
):
    with sentry_sdk.start_span(op = "auth", name = "login"):
        sentry_sdk.set_tag("endpoint", "login")

        response.headers["Cache-Control"] = "no-store"

        # Look up the user.
        user = session.query(UserInternalModel).filter(
            UserInternalModel.email == payload.email
        ).first()

        # If they were not found, don't authorize.
        if not user:
            raise HTTPException(
                status_code = status.HTTP_401_UNAUTHORIZED,
                detail = "Invalid email or password."
            )

        # If they were found, verify their password.
        if not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code = status.HTTP_401_UNAUTHORIZED,
                detail = "Invalid email or password."
            )

        # Placeholder response (JWTs coming).
        return {"message": "Login successful (tokens coming next)"}
