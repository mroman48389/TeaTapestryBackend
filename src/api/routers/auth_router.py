from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
import logging
from starlette import status
import sentry_sdk
import uuid

from src.utils.session_utils import get_session
from src.db.models.user_models import UserInternalModel
from src.api.schemas.user_schema import (
    UserInboundSchema,
    UserOutboundSchema,
    LoginSchema
)
from src.api.dependencies.auth_dependencies import get_current_user
from src.utils.auth.password_utils import (
    hash_password, 
    validate_password_strength,
    verify_password
)
from src.utils.auth.jwt_utils import (
    create_access_token,
    create_refresh_token, 
    decode_token,
    REFRESH_TOKEN_LIFETIME_DAYS,
)
from src.core.rate_limit.setup_rate_limit import rate_limiter
from src.core.rate_limit.config_rate_limit import (
    LOW_RATE_LIMIT,
    VERY_LOW_RATE_LIMIT
)

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

@router.post("/login", status_code = status.HTTP_200_OK)
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

        # Generate tokens.
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        # Determine cookie security based on environment. Allows us to ignore
        # secure cookies, which do not work over http (we run locally over http and
        # production over https).
        hostname = request.url.hostname
        is_local = hostname in ("localhost", "127.0.0.1")

        # Set refresh token cookie. max_age is the number of seconds the browser 
        # should hold on to this cookie. 7 days * (24 hrs / day) * (60 min / 1 hr) *
        # (60 sec / min)
        response.set_cookie(
            key = "refresh_token",
            value = refresh_token,
            httponly = True,
            secure = not is_local,
            samesite = "strict",
            max_age = REFRESH_TOKEN_LIFETIME_DAYS * 24 * 60 * 60
        )

        # Return access token
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }

        # Placeholder response (JWTs coming).
        # return {"message": "Login successful (tokens coming next)"}


@router.post("/logout")
@rate_limiter.limit(VERY_LOW_RATE_LIMIT)
def logout(
    request: Request,
    response: Response
):
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}


@router.post("/refresh", status_code = status.HTTP_200_OK
)
@rate_limiter.limit(VERY_LOW_RATE_LIMIT)
def refresh_token(
    request: Request,
    response: Response,
    session: Session = Depends(get_session)
):
    # When the access token expires after about 15 minutes on the frontend, it
    # can call this endpoint to read the refresh token from the HttpOnly cookie.
    # We'll decode and validate it, ensure the scope is "refresh", and issue a 
    # new access token (returned as JSON).
    #
    # Refresh tokens live in cookies because cookies persist across browser restarts
    # and page reloads. Since they are HttpOnly, JavaScript can't be used to steal
    # them. They have CSRF (cross-site request forgery) protection, since they are 
    # SameSite strict.

    # Make sure the refresh token is in the cookie.
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Missing refresh token."
        )

    # Decode and validate the refresh token.
    try:
        payload = decode_token(refresh_token)

    except Exception:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid or expired refresh token."
        )

    # Ensure the token is a refresh token.
    if payload.get("scope") != "refresh":
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid token scope."
        )

    user_id = uuid.UUID(payload.get("sub"))

    # Ensure the user exists.
    user = session.query(UserInternalModel).filter(
        UserInternalModel.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "User no longer exists."
        )

    # Issue a new access token.
    new_access_token = create_access_token(str(user.id))

    # Issue a new refresh token (rotate the token). Prevents stolen 
    # refresh tokens from being reused.
    new_refresh_token = create_refresh_token(str(user.id))

    hostname = request.url.hostname
    is_local = hostname in ("localhost", "127.0.0.1")

    response.set_cookie(
        key = "refresh_token",
        value = new_refresh_token,
        httponly = True,
        secure = not is_local,
        samesite = "strict",
        max_age = REFRESH_TOKEN_LIFETIME_DAYS * 24 * 60 * 60
    )

    # Return a new access token.
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }


@router.get("/me")
@rate_limiter.limit(LOW_RATE_LIMIT)
def get_me(
    request: Request,
    current_user = Depends(get_current_user)
):
    # Protected route that returns information about the 
    # currently authenticated user, based on their access token.
    # The frontend should never store user identity in cookies or
    # local storage. It should always just store an access token and
    # ask the backend for user details after passing that access
    # token back.
    # print("DEBUG: inside /me route")
    # print("DEBUG: current_user:", current_user)
    # print("DEBUG: current_user.id:", current_user.id)
    # print("DEBUG: current_user.email:", current_user.email)
    # print("DEBUG: current_user.created_at:", current_user.created_at)

    return {
        "id": current_user.id,
        "email": current_user.email,
        "created_at": current_user.created_at
    }