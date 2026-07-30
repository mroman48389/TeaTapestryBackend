from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from starlette import status
import sentry_sdk
import uuid
import hashlib
from datetime import datetime, timezone
from fastapi.responses import JSONResponse

from src.utils.log_utils import safe_debug, safe_exception
from src.utils.session_utils import get_session
from src.db.models.user_models import UserInternalModel
from src.api.schemas.user_schema import (
    UserInboundSchema,
    UserOutboundSchema,
    LoginSchema
)
from src.api.schemas.password_reset_schema import (
    PasswordResetRequestSchema, 
    PasswordResetSubmissionSchema,
)
from src.api.dependencies.auth_dependencies import get_current_user
from src.utils.auth.password_utils import (
    hash_password, 
    validate_password_strength,
    verify_password
)
from src.constants.jwt_constants import (
    ACCESS_TOKEN_LIFETIME_MINUTES,
    REFRESH_TOKEN_LIFETIME_DAYS
)
from src.utils.auth.jwt_utils import (
    create_access_token,
    create_refresh_token, 
    decode_token
)
from src.core.rate_limit.setup_rate_limit import rate_limiter
from src.core.rate_limit.config_rate_limit import (
    LOW_RATE_LIMIT,
    VERY_LOW_RATE_LIMIT
)
from src.constants.route_constants import (
    AUTH,
    AUTH_PREFIX,
    SIGN_UP,
    VERIFY_EMAIL,
    SEND_VERIFICATION,
    REQUEST_PASSWORD_RESET,
    RESET_PASSWORD,
    LOGIN,
    LOGOUT,
    REFRESH,
    ME
)
from src.utils.auth.token_utils import (
    create_raw_verification_token,
    send_verification_email,
    send_password_reset_email
)
from src.constants.token_constants import (
    EMAIL_VERIFICATION,
    PASSWORD_RESET
)
from src.db.models.verification_token_model import VerificationToken

# Define group of routes with auth as their base path for documentation grouping.
router = APIRouter(prefix = AUTH_PREFIX, tags = ["auth"])

# request param is required by SlowAPI. Without it, we'll get an exception.
@router.post(
    f"/{SIGN_UP}", 
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
    # a minute), and top-level Sentry observability. The Sentry spans are purposefully
    # done a little differently for auth endpoints, since auth is critical and we want
    # to monitor it separately. The version below is auth-first rather than 
    # endpoint-first as a result. 
    # 
    # Etags, last-modified/cahce-control headers, head endpoints, and caching range 
    # from not applicable to harmful here. Sensitive information should never be
    # cached, and we are dealing with a POST, not a GET.
    #
    with sentry_sdk.start_span(op = AUTH, name = "signup"):
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
            display_name = payload.display_name,
        )

        try:
            session.add(new_user)
            session.commit()
            session.refresh(new_user)

            # Create a verification token for the new user and send them an email
            # so they can click a link to verify.
            raw_token = create_raw_verification_token(new_user, session, EMAIL_VERIFICATION)
            send_verification_email(new_user, raw_token)

        except Exception:
            session.rollback()
            
            safe_exception("Unexpected error during signup.")

            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = "An unexpected error occurred while creating the account."
            )
        
        # Return the UserOutboundSchema (FastAPI will take the relevant fields from
        # the UserInboundSchema and serialize it into a UserOutboundSchema because
        # of the response_model we set).
        return new_user


# Postman test steps for testing send_verification and verify_email:
#
#     1. Create the user. Call signup endpoint as POST /auth/signup with body
#
#         {
#             "email": "someUsername@gmail.com",
#             "password": "SomePassword@123",
#             "display_name": "Some User"
#         }
#
#     2. Authenticate the user. Call login endpoint as POST /auth/login with body
#
#         {
#             "email": "someUsername@gmail.com",
#             "password": "SomePassword@123"
#         }
#
#         Copy the access token from the response. You will need it for the
#         send_verification endpoint.
#
#     3. Send a verification email. Call send_verification as POST /auth/send_verification
#        with the Authorization header:
#
#            Authorization: Bearer <access_token>
#
#        This endpoint will log the raw email_verification token (only in development
#        mode). You'll need that for verify_email, so grab it.
#
#     4. Verify the email. Call verify_email as POST /auth/verify_email?token=[raw_token]
#
#        If the token is valid, the endpoint should return a success message and mark
#        the user's email as verified. See note in verify_email for why we put the token in 
#        the URL.
#
#     5. (Optional) Try calling verify_email again with the same token. It should now fail
#        because the token has already been used.

@router.post(f"/{SEND_VERIFICATION}", status_code = status.HTTP_200_OK)
@rate_limiter.limit(VERY_LOW_RATE_LIMIT)
def send_verification(
    request: Request,
    response: Response,
    current_user = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Prevent caching
    response.headers["Cache-Control"] = "no-store"

    # If the user already verified, do not resend.
    if current_user.is_verified:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Email is already verified."
        )

    # Delete old tokens for this user.
    session.query(VerificationToken).filter(
        VerificationToken.user_id == current_user.id,
        VerificationToken.purpose == EMAIL_VERIFICATION
    ).delete()
    session.commit()

    # Create a new token.
    raw_token = create_raw_verification_token(current_user, session, EMAIL_VERIFICATION)

    #TODO: remove
    safe_debug(f"DEV VERIFICATION TOKEN: {raw_token}")

    # Send (print) the verification link.
    send_verification_email(current_user, raw_token)

    return {"message": "Verification email sent."}


@router.post(f"/{VERIFY_EMAIL}", status_code = status.HTTP_200_OK)
@rate_limiter.limit(VERY_LOW_RATE_LIMIT)
def verify_email(
    request: Request,
    response: Response,
    token: str,
    session: Session = Depends(get_session)
):
    # Prevent caching.
    response.headers["Cache-Control"] = "no-store"

    # Hash the incoming raw token. The token will come from the URL
    # (forwarded by the frontend to the backend) so we have a 
    # frictionless one-click action for the user. Email verification
    # tokens are non-sensitive (don't grant login access), so this is 
    # safe to do.
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # Look up the email verification token in the database.
    verification_token = session.query(VerificationToken).filter(
        VerificationToken.token_hash == token_hash,
        VerificationToken.purpose == EMAIL_VERIFICATION
    ).first()

    if not verification_token:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Invalid or unknown verification token."
        )

    # Check if the token was already used.
    if verification_token.used:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "This verification link has already been used."
        )

    # Check to see if the verification token is expired.
    expires_at = verification_token.expires_at

    # SQLite strips timezone info, so normalize naive timestamps to UTC
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo = timezone.utc)

    now = datetime.now(timezone.utc)

    if expires_at < now:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "This verification link has expired."
        )

    # Fetch the user.
    user = session.query(UserInternalModel).filter(
        UserInternalModel.id == verification_token.user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "User no longer exists."
        )

    # Mark the verification token as used.
    verification_token.used = True

    # Mark the user as verified and add the time verified.
    user.is_verified = True
    user.verified_at = now

    session.commit()

    return {"message": "Email verified successfully."}


# Postman test steps for testing request_password_reset and reset_password:
#
#     1. Create the user. Call signup endpoint as POST /auth/signup with body
#
#         {
#             "email": "someUsername@gmail.com",
#             "password": "SomePassword@123",
#             "display_name": "Some User"
#         }
#
#     2. Send a reset email. Call request_password_reset as POST /auth/request_password_reset 
#        with body
#
#        {
#            "email": "someUsername@gmail.com"
#        }
#
#        This endpoint will log the raw token (only in development mode). You'll
#        need that for reset_password, so grab it.
#
#     3. Reset the password. Call reset_password as POST /auth/reset_password
#        with body
#
#        {
#            "new_password": "NewPassword@123"
#            "token": "[raw_token]"
#        }
#
#        See note in reset_password for why we place the token in the body instead of as
#        part of the URL like we did with verify_email.
#
#     4. Try the login endpoint with the new password and then again with the old password. The 
#        former should work, the latter should fail.
#
@router.post(f"/{REQUEST_PASSWORD_RESET}", status_code = status.HTTP_200_OK)
@rate_limiter.limit(VERY_LOW_RATE_LIMIT)
def request_password_reset(
    request: Request,
    response: Response,
    payload: PasswordResetRequestSchema,
    session: Session = Depends(get_session)
):
    with sentry_sdk.start_span(op = AUTH, name = "request_password_reset"):
        sentry_sdk.set_tag("endpoint", "request_password_reset")

        # Prevent caching.
        response.headers["Cache-Control"] = "no-store"

        # Get the user from their email.
        user = session.query(UserInternalModel).filter(
            UserInternalModel.email == payload.email
        ).first()

        # Prevent hackers from using enumeration attacks to discover valid accounts by 
        # submitting emails and observing the response. 200 will be returned whether
        # we found the user or not. 
        # 
        # Avoid saying the email wasn't found, revealing anything about the user 
        # database, and returning 404 or 400.
        request_password_reset_msg = "If the email exists, a reset link has been sent."
        if not user:
            return {"message": request_password_reset_msg}

        # Delete old password reset verification tokens for the user.
        session.query(VerificationToken).filter(
            VerificationToken.user_id == user.id,
            VerificationToken.purpose == PASSWORD_RESET
        ).delete()
        session.commit()

        # Create a new password reset token.
        raw_token = create_raw_verification_token(
            user,
            session,
            purpose = PASSWORD_RESET,
        )

        # So we can grab the raw token when testing password resets via Postman.
        safe_debug(f"DEV PASSWORD RESET TOKEN:{raw_token}")

        send_password_reset_email(user, raw_token)

        return {"message": request_password_reset_msg}


@router.post(f"/{RESET_PASSWORD}", status_code = status.HTTP_200_OK)
@rate_limiter.limit(VERY_LOW_RATE_LIMIT)
def reset_password(
    request: Request,
    response: Response,
    payload: PasswordResetSubmissionSchema,
    session: Session = Depends(get_session)
):
    with sentry_sdk.start_span(op = AUTH, name = "reset_password"):
        sentry_sdk.set_tag("endpoint", "reset_password")

        # Prevent caching.
        response.headers["Cache-Control"] = "no-store"

        # Hash incoming raw token. It must come from the body of the call
        # instead of as part of the URL (which we did with verify_email),
        # because this is a sensitive, high-risk form submission action. The email
        # contains a link to the frontend page rather than the backend page.
        # The frontend gets the new password and sends a POST with the token
        # and new password. 
        token_hash = hashlib.sha256(payload.token.encode()).hexdigest()

        # Try to find a password reset verification token given the inbound
        # hash.
        verification_token = session.query(VerificationToken).filter(
            VerificationToken.token_hash == token_hash,
            VerificationToken.purpose == PASSWORD_RESET
        ).first()

        if not verification_token:
            raise HTTPException(
                status_code = status.HTTP_400_BAD_REQUEST,
                detail = "Invalid or unknown password reset token."
            )

        # Check if the password reset verification token was already used.
        if verification_token.used:
            raise HTTPException(
                status_code = status.HTTP_400_BAD_REQUEST,
                detail = "This password reset link has already been used."
            )

        # Check to see if the password reset verification token has expired.
        expires_at = verification_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo = timezone.utc)

        now = datetime.now(timezone.utc)
        if expires_at < now:
            raise HTTPException(
                status_code = status.HTTP_400_BAD_REQUEST,
                detail = "This password reset link has expired."
            )

        # Get the user from the password reset verification token.
        user = session.query(UserInternalModel).filter(
            UserInternalModel.id == verification_token.user_id
        ).first()

        if not user:
            raise HTTPException(
                status_code = status.HTTP_400_BAD_REQUEST,
                detail = "The user does not exist."
            )

        # Validate password strength of the user's new password.
        validate_password_strength(payload.new_password)

        # Update password.
        user.hashed_password = hash_password(payload.new_password)

        # Mark the password reset verification token as used.
        verification_token.used = True

        # Determine cookie security based on environment. Allows us to ignore
        # secure cookies, which do not work over http (we run locally over http and
        # production over https).
        hostname = request.url.hostname
        is_local = hostname in ("localhost", "127.0.0.1", "testserver")

        # Delete refresh and access tokens.
        response.delete_cookie(
            key = "refresh_token",
            path = "/",
            secure = not is_local,
            samesite = "lax"
        )

        response.delete_cookie(
            key = "access_token",
            path = "/",
            secure = not is_local,
            samesite = "lax"
        )

        session.commit()

        return {"message": "Password reset successfully."}


@router.post(f"/{LOGIN}", status_code = status.HTTP_200_OK)
@rate_limiter.limit(VERY_LOW_RATE_LIMIT)
def login(
    request: Request,
    payload: LoginSchema,
    response: Response,
    session: Session = Depends(get_session)
):
    with sentry_sdk.start_span(op = AUTH, name = "login"):
        sentry_sdk.set_tag("endpoint", "login")

        # Prevent caching
        response.headers["Cache-Control"] = "no-store"

        # Look up the user.
        user = session.query(UserInternalModel).filter(
            UserInternalModel.email == payload.email
        ).first()

        # If they were not found, don't authorize.
        if (not user) or (not verify_password(payload.password, user.hashed_password)):
            raise HTTPException(
                status_code = status.HTTP_401_UNAUTHORIZED,
                detail = "Invalid email or password."
            )

        # Generate tokens.
        access_token = create_access_token(str(user.id), user.is_verified)
        refresh_token = create_refresh_token(str(user.id), user.is_verified)

        # Determine cookie security based on environment. Allows us to ignore
        # secure cookies, which do not work over http (we run locally over http and
        # production over https).
        hostname = request.url.hostname
        is_local = hostname in ("localhost", "127.0.0.1", "testserver")

        response = JSONResponse(
            content = {
                "access_token": access_token,
                "token_type": "bearer"
            }
        )

        # Set refresh token cookie. max_age is the number of seconds the browser 
        # should hold on to this cookie. 7 days * (24 hrs / day) * (60 min / 1 hr) *
        # (60 sec / min)
        response.set_cookie(
            key = "refresh_token",
            value = refresh_token,
            httponly = True,
            secure = not is_local,
            samesite = "lax",
            path = "/",
            max_age = REFRESH_TOKEN_LIFETIME_DAYS * 24 * 60 * 60
        )

        response.set_cookie(
            key = "access_token",
            value = access_token,
            httponly = True,
            secure = not is_local,
            samesite = "lax",
            path = "/",
            max_age = ACCESS_TOKEN_LIFETIME_MINUTES * 60
        )

        return response


@router.post(f"/{LOGOUT}")
@rate_limiter.limit(VERY_LOW_RATE_LIMIT)
def logout(
    request: Request,
    response: Response
):
    with sentry_sdk.start_span(op = AUTH, name = "logout"):
        sentry_sdk.set_tag("endpoint", "logout")
        
        hostname = request.url.hostname
        is_local = hostname in ("localhost", "127.0.0.1", "testserver")

        response.delete_cookie(
            key = "refresh_token",
            path = "/",
            secure = not is_local,
            samesite = "lax"
        )
        response.delete_cookie(
            key = "access_token",
            path = "/",
            secure = not is_local,
            samesite = "lax"
        )

        return {"message": "Logged out"}


@router.post(f"/{REFRESH}", status_code = status.HTTP_200_OK)
@rate_limiter.limit(VERY_LOW_RATE_LIMIT)
def refresh_token(
    request: Request,
    response: Response,
    session: Session = Depends(get_session)
):
    with sentry_sdk.start_span(op = AUTH, name = "refresh_token"):
        sentry_sdk.set_tag("endpoint", "refresh_token")

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
        new_access_token = create_access_token(str(user.id), user.is_verified)

        # Issue a new refresh token (rotate the token). Prevents stolen 
        # refresh tokens from being reused.
        new_refresh_token = create_refresh_token(str(user.id), user.is_verified)

        hostname = request.url.hostname
        is_local = hostname in ("localhost", "127.0.0.1", "testserver")

        response = JSONResponse(
            content = {
                "access_token": new_access_token,
                "token_type": "bearer"
            }
        )

        response.set_cookie(
            key = "refresh_token",
            value = new_refresh_token,
            httponly = True,
            secure = not is_local,
            samesite = "lax",
            path = "/",
            max_age = REFRESH_TOKEN_LIFETIME_DAYS * 24 * 60 * 60
        )

        response.set_cookie(
            key = "access_token",
            value = new_access_token,
            httponly = True,
            secure = not is_local,
            samesite = "lax",
            path = "/",
            max_age = ACCESS_TOKEN_LIFETIME_MINUTES * 60
        )

        return response


@router.get(f"/{ME}")
@rate_limiter.limit(LOW_RATE_LIMIT)
def get_me(
    request: Request,
    current_user = Depends(get_current_user)
):
    with sentry_sdk.start_span(op = AUTH, name = "get_me"):
        sentry_sdk.set_tag("endpoint", "get_me")

        # Protected route that returns information about the 
        # currently authenticated user, based on the access token cookie.
        # The frontend does not store tokens; the browser sends cookies 
        # automatically, and the backend derives identity from them.

        return {
            "id": current_user.id,
            "email": current_user.email,
            "created_at": current_user.created_at
        }