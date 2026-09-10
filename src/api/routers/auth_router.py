from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from starlette import status
import sentry_sdk
import uuid
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from fastapi.responses import JSONResponse, StreamingResponse
import json
import gzip


# Constants

from src.constants.jwt_constants import (
    ACCESS_TOKEN_LIFETIME_MINUTES,
    REFRESH_TOKEN_LIFETIME_DAYS
)
from src.constants.cookie_constants import SAME_SITE_VALUE
from src.constants.route_constants import (
    AUTH,
    AUTH_PREFIX,
    SIGNUP,
    VERIFY_EMAIL,
    SEND_VERIFICATION,
    REQUEST_PASSWORD_RESET,
    RESET_PASSWORD,
    LOGIN,
    LOGOUT,
    LOGOUT_ALL,
    ACTIVE_SESSIONS,
    TERMINATE_SESSION,
    REFRESH,
    ME,
    EXPORT_USER_DATA,
    DELETE_USER_DATA,
    DELETE_USER_ACCOUNT,
    CONFIRM_PASSWORD,
)
from src.constants.dsar_constants import (
    DSAR_REQUEST_DELETE_USER_ACCOUNT,
    DSAR_REQUEST_DELETE_USER_DATA,
    DSAR_REQUEST_EXPORT_USER_DATA
)
from src.constants.token_constants import (
    EMAIL_VERIFICATION,
    PASSWORD_RESET
)
from src.constants.auth_constants import (
    FRESH_LOGIN_WINDOW_SECONDS,
    CONCURRENT_REFRESH_GRACE_SECONDS
)


# Config and setup

from src.core.rate_limit.setup_rate_limit import rate_limiter
from src.core.rate_limit.config_rate_limit import (
    LOW_RATE_LIMIT,
    VERY_LOW_RATE_LIMIT,
    LOWEST_RATE_LIMIT
)


# Dependencies

from src.api.dependencies.auth_dependencies import get_current_user


# Utilities

from src.utils.log_utils import safe_debug, safe_exception
from src.utils.session_utils import get_session
from src.utils.auth.password_utils import (
    hash_password, 
    validate_password_strength,
    verify_password
)
from src.utils.auth.jwt_utils import (
    create_access_token
)
from src.utils.auth.token_utils import (
    create_raw_verification_token,
    send_verification_email,
    send_password_reset_email
)
from src.utils.request_metadata_utils import (
    get_client_ip,
    get_user_agent
)
from src.utils.auth.cookie_utils import delete_auth_token_cookies

# Models

from src.db.models.auth.user_models import UserInternalModel
from src.db.models.auth.session_token_model import SessionTokenModel
from src.db.models.auth.verification_token_model import VerificationTokenModel

# Schema

from src.api.schemas.auth.user_schema import (
    UserInboundSchema,
    UserOutboundSchema,
)
from src.api.schemas.auth.login_schema import (
    LoginSchema,
    LoginResponseSchema
)
from src.api.schemas.auth.logout_schema import (
    LogoutResponseSchema,
    LogoutAllResponseSchema
)
from src.api.schemas.auth.password_reset_schema import (
    PasswordResetRequestSchema, 
    PasswordResetRequestResponseSchema,
    PasswordResetSubmissionSchema,
    PasswordResetSubmissionResponseSchema
)
from src.api.schemas.auth.session_schema import (
    ActiveSessionSchema,
    ActiveSessionsResponseSchema,
    TerminateSessionResponseSchema
)
from src.api.schemas.auth.email_verification_schema import (
    VerifyEmailResponseSchema,
    SendVerificationResponseSchema
)
from src.api.schemas.auth.refresh_schema import RefreshResponseSchema
from src.api.schemas.auth.me_schema import MeResponseSchema
from src.api.schemas.auth.confirm_password_schema import ConfirmPasswordInboundSchema


# Services

from src.app.services.user_data_export_services import UserDataExportService
from src.app.services.user_data_deletion_services import (
    UserDataDeletionService,
    UserAccountDeletionService
)


# Repositories
from src.db.repositories.user_tea_profile_notes_repository import UserTeaProfileNotesRepository
from src.db.repositories.dsar_log_repository import DSARLogRepository
from src.db.repositories.password_confirmation_repository import PasswordConfirmationRepository


# Define group of routes with auth as their base path for documentation grouping.
router = APIRouter(prefix = AUTH_PREFIX, tags = ["auth"])


DUMMY_PASSWORD_HASH = hash_password("dummy-password-for-timing")


###############################################################################
#################################   Helpers   #################################
###############################################################################

# Requiring a recent login (within the past 5 minutes) protects against
# stolen long-lived session tokens, compromised devices, unattended browsers,
# and malicious scripts.
def _require_fresh_login(current_user: UserInternalModel):
    if current_user.last_login is None:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Please log in again before exporting your data."
        )

    last_login = current_user.last_login

    # Normalize naive datetimes (SQLite strips timezone info in testing).
    if last_login.tzinfo is None:
        last_login = last_login.replace(tzinfo = timezone.utc)

    now = datetime.now(timezone.utc)

    if (now - last_login) > timedelta(seconds = FRESH_LOGIN_WINDOW_SECONDS):
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = (
                "Your login session is too old. "
                "Please log in again before exporting your data."
            )
        )

###############################################################################
###############################   Endpoints   #################################
###############################################################################

# Postman test steps for testing signup:
#
#     1. Call signup endpoint as "POST /auth/signup" with body:
#
#            {
#                "email": "someUsername@gmail.com",
#                "password": "SomePassword@123",
#                "display_name": "Some User"
#            }
#
# request param is required by SlowAPI. Without it, we'll get an exception.
#
@router.post(
    f"/{SIGNUP}", 
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

        # Handles concurrency / race conditions. If two signups happen 
        # at the same time, for ex, both could pass the existing_user
        # check and one could commit first, leading to the second signup
        # hitting a DB issue.
        except IntegrityError:
            session.rollback()

            raise HTTPException(
                status_code = status.HTTP_400_BAD_REQUEST,
                detail = "A user with this email address already exists."
            )
        
        except Exception:
            session.rollback()
            
            safe_exception("Unexpected error during signup.")

            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = "An unexpected error occurred while creating the account."
            )

        try:
            session.refresh(new_user)

        except Exception:
            # The user row is already committed at this point. Refresh only
            # reloads server-generated fields (id, defaults). There's nothing to
            # roll back, and telling the client account creation failed would be
            # wrong. Log it. downstream code will still need new_user.id, so this
            # is likely to surface again shortly if the connection is genuinely bad.
            safe_exception("Unexpected error refreshing new user after signup.")
            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = "An unexpected error occurred while refreshing the new account."
            )

        # Create a verification token for the new user .
        raw_token = create_raw_verification_token(new_user, session, EMAIL_VERIFICATION)

        # We still want to return the user if something went wrong with the verification
        # token and we don't send the verification email.
        if raw_token is None:
            return new_user

        try:
            session.commit()

        except Exception:
            session.rollback()

            safe_exception("Failed to commit verification token during signup.")

            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = "Failed to create verification token.",
            )

        try:
            # Send the user an email so they can click a link to verify. Treat this as a 
            # best effort approach, rolling backing nothing if the email sending fails.
            
            send_verification_email(new_user, raw_token)

        except Exception:
            safe_exception("Error sending verification email during signup.")

        # Return the UserOutboundSchema (FastAPI will take the relevant fields from
        # the UserInboundSchema and serialize it into a UserOutboundSchema because
        # of the response_model we set).
        return new_user


# Postman steps for testing send_verification and verify_email:
#
#     1. Follow the steps for testing login. Copy the access token from the response. 
#         You will need it for the send_verification endpoint.
#
#     2. Send a verification email. Call send_verification as "POST /auth/send_verification"
#        with the Authorization header:
#
#            Authorization: Bearer <access_token>
#
#        This endpoint will log the raw email_verification token (only in development
#        mode). You'll need that for verify_email, so grab it.
#
#     3. Verify the email. Call verify_email as "POST /auth/verify_email?token=[raw_token]"
#
#        If the token is valid, the endpoint should return a success message and mark
#        the user's email as verified. See note in verify_email for why we put the token in 
#        the URL.
#
#     4. (Optional) Try calling verify_email again with the same token. It should now fail
#        because the token has already been used.
#
@router.post(
    f"/{SEND_VERIFICATION}", 
    status_code = status.HTTP_200_OK,
    response_model = SendVerificationResponseSchema
)
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

    try:
        # Delete old tokens for this user.
        session.query(VerificationTokenModel).filter(
            VerificationTokenModel.user_id == current_user.id,
            VerificationTokenModel.purpose == EMAIL_VERIFICATION
        ).delete()

        session.commit()

    except Exception:
        session.rollback()

        safe_exception("Unexpected error deleting old verification tokens.")

        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = "An unexpected error occurred while preparing the verification token."
        )

    raw_token = create_raw_verification_token(current_user, session, EMAIL_VERIFICATION)

    if raw_token is None:
        return SendVerificationResponseSchema(
            message = "Failed to create token."
        )

    try:
        session.commit()

    except Exception:
        session.rollback()

        safe_exception("Failed to commit verification token.")

        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = "Failed to create verification token.",
        )

    try:
        # Send (print) the verification link. Treat this as a best effort approach,
        # rolling backing nothing if the email sending fails.
        send_verification_email(current_user, raw_token)

    except Exception:
        safe_exception("Error sending verification email.")

    return SendVerificationResponseSchema(message = "Verification email sent.")


@router.post(
    f"/{VERIFY_EMAIL}", 
    status_code = status.HTTP_200_OK,
    response_model = VerifyEmailResponseSchema
)
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
    verification_token = session.query(VerificationTokenModel).filter(
        VerificationTokenModel.token_hash == token_hash,
        VerificationTokenModel.purpose == EMAIL_VERIFICATION
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

    try:
        # Mark the verification token as used.
        verification_token.used = True

        # Mark the user as verified and add the time verified.
        user.is_verified = True
        user.verified_at = now

        session.commit()

    except Exception:
        session.rollback()

        safe_exception("Unexpected error during email verification.")

        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = "An unexpected error occurred while verifying the email."
        )

    return VerifyEmailResponseSchema(message = "Email verified successfully.")


# Postman test steps for testing request_password_reset and reset_password:
#
#     1. Follow the steps for testing the signup endpoint.
#
#     2. Send a reset email. Call request_password_reset as "POST /auth/request_password_reset"
#        with body
#
#            {
#                "email": "someUsername@gmail.com"
#            }
#
#        This endpoint will log the raw token (only in development mode). You'll
#        need that for reset_password, so grab it.
#
#     3. Reset the password. Call reset_password as "POST /auth/reset_password"
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
@router.post(
    f"/{REQUEST_PASSWORD_RESET}", 
    status_code = status.HTTP_200_OK,
    response_model = PasswordResetRequestResponseSchema
)
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

        request_password_reset_msg = "If the email exists, a reset link has been sent."

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
        if not user:
            return PasswordResetRequestResponseSchema(message =  request_password_reset_msg)

        try:
            # Delete old password reset verification tokens for the user.
            session.query(VerificationTokenModel).filter(
                VerificationTokenModel.user_id == user.id,
                VerificationTokenModel.purpose == PASSWORD_RESET
            ).delete()

            session.commit()

        except Exception:
            session.rollback()
            safe_exception("Unexpected error during password reset request.")

        # Create a new password reset token.
        raw_token = create_raw_verification_token(
            user,
            session,
            purpose = PASSWORD_RESET,
        )

        # So we can grab the raw token when testing password resets via Postman.
        safe_debug(f"DEV PASSWORD RESET TOKEN:{raw_token}")

        try:
            session.commit()

        except Exception:
            session.rollback()

            safe_exception("Failed to commit verification token.")

            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = "Failed to create verification token.",
            )

        if raw_token is not None:
            try:
                send_password_reset_email(user, raw_token)

            except Exception:
                safe_exception("Error sending password reset email.")

        return PasswordResetRequestResponseSchema(message = request_password_reset_msg)


@router.post(
    f"/{RESET_PASSWORD}", 
    status_code = status.HTTP_200_OK,
    response_model = PasswordResetSubmissionResponseSchema
)
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
        verification_token = session.query(VerificationTokenModel).filter(
            VerificationTokenModel.token_hash == token_hash,
            VerificationTokenModel.purpose == PASSWORD_RESET
        ).first()

        if not verification_token:
            raise HTTPException(
                status_code = status.HTTP_400_BAD_REQUEST,
                detail = "Invalid or unknown password reset token."
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

        try:
            # Grab the unused password reset verification token. This should only
            # return one token by virtue of checking the token id, but we include
            # the used check to ensure only one request can update this row under
            # concurrency. This is an atomic CAS (compare and swap).
            updated_verification_token = session.query(VerificationTokenModel).filter(
                VerificationTokenModel.id == verification_token.id,
                VerificationTokenModel.used.is_(False)
            )

            # Mark it as used.
            updated = updated_verification_token.update(
                {VerificationTokenModel.used: True},
                synchronize_session = False
            )

            # If we failed to mark the token as used, assume the password verfication
            # token was already used.
            if updated == 0:
                raise HTTPException(
                    status_code = status.HTTP_400_BAD_REQUEST,
                    detail = "This password reset link has already been used."
                )

            # Update password
            user.hashed_password = hash_password(payload.new_password)

            # Get all session tokens for this user that have not already been revoked. We
            # are being sure not to re-revoke tokens here so we preserve the original
            # revoke times.
            user_session_tokens = session.query(SessionTokenModel).filter(
                SessionTokenModel.user_id == user.id,
                SessionTokenModel.revoked_at.is_(None)
            )

            # Revoke all active sessions for this user by updating the revoked_at field 
            # for their tokens. 
            user_session_tokens.update(
                {SessionTokenModel.revoked_at: now},
                synchronize_session = False
            )
            
            session.commit()

        except HTTPException:
            # Let controlled errors bubble up
            raise

        except Exception:
            session.rollback()

            safe_exception("Unexpected error during password reset.")

            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = "An unexpected error occurred while resetting the password."
            )

        delete_auth_token_cookies(request, response)

        return PasswordResetSubmissionResponseSchema(message = "Password reset successfully.")


# Postman test steps for testing login:
#
#     1. Follow the steps for testing signup, if a user does not exist yet.
#
#     2. Call login as "POST /auth/login" with body
#
#            {
#                "email": "someUsername@gmail.com"
#                "password": "SomePassword@123"
#            }
#
#        Use the same email and password as you did during signup. Upon successful Postman will 
#        automatically store the access_token and refresh_token cookies. These are required 
#        for all protected endpoints, including:
#            
#            /auth/me
#            /auth/refresh 
#            /auth/active_sessions 
#            /auth/terminate_session/{session_id}
#            /auth/logout_all
#
@router.post(
    f"/{LOGIN}", 
    status_code = status.HTTP_200_OK,
    response_model = LoginResponseSchema
)
@rate_limiter.limit(VERY_LOW_RATE_LIMIT)
def login(
    request: Request,
    payload: LoginSchema,
    response: Response,
    session: Session = Depends(get_session)
):
    with sentry_sdk.start_span(op = AUTH, name = "login"):
        sentry_sdk.set_tag("endpoint", "login")

        # Look up the user.
        user = session.query(UserInternalModel).filter(
            UserInternalModel.email == payload.email
        ).first()

        # Make invalid logins take the same amount of time as valid ones rather than
        # failing faster due to lack of registration. This prevent attackers from 
        # figuring out which emails have have been registered based on timing differences.
        # Basically, if the user does not exist, instead of quickly failing, we burn time
        # by still calling verify password.
        if user:
            password_ok = verify_password(payload.password, user.hashed_password)
        else:
            verify_password(payload.password, DUMMY_PASSWORD_HASH)  # burn time
            password_ok = False

        if (not user) or (not password_ok):
            raise HTTPException(
                status_code = status.HTTP_401_UNAUTHORIZED,
                detail = "Invalid email or password."
            )

        # Generate tokens.
        access_token = create_access_token(str(user.id), user.is_verified)
        raw_refresh_token = secrets.token_urlsafe(32)
        hashed_refresh_token = hashlib.sha256(raw_refresh_token.encode()).hexdigest()

        now = datetime.now(timezone.utc)
        created_at = now
        expires_at = now + timedelta(days = REFRESH_TOKEN_LIFETIME_DAYS)

        session_token = SessionTokenModel(
            user_id = user.id,
            refresh_token_hash = hashed_refresh_token,
            created_at = created_at,
            expires_at = expires_at,
            user_agent = get_user_agent(request),
            ip_address = get_client_ip(request)
        )

        try: 
            user.last_login = datetime.now(timezone.utc)

            session.add(session_token)

            session.commit()

        except Exception as exc:
            session.rollback()
            sentry_sdk.capture_exception(exc)

            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = "Could not create session token."
            ) from exc

        # Determine cookie security based on environment. Allows us to ignore
        # secure cookies, which do not work over http (we run locally over http and
        # production over https).
        hostname = request.url.hostname
        is_local = hostname in ("localhost", "127.0.0.1", "testserver")

        body = LoginResponseSchema(
            access_token = access_token,
            token_type = "bearer"
        )

        response = JSONResponse(content = body.model_dump())

        # Prevent caching
        response.headers["Cache-Control"] = "no-store"

        # Set refresh token cookie. max_age is the number of seconds the browser 
        # should hold on to this cookie. 7 days * (24 hrs / day) * (60 min / 1 hr) *
        # (60 sec / min)
        response.set_cookie(
            key = "refresh_token",
            value = raw_refresh_token,
            httponly = True,
            secure = not is_local,
            samesite = SAME_SITE_VALUE,
            path = "/",
            max_age = REFRESH_TOKEN_LIFETIME_DAYS * 24 * 60 * 60
        )

        response.set_cookie(
            key = "access_token",
            value = access_token,
            httponly = True,
            secure = not is_local,
            samesite = SAME_SITE_VALUE,
            path = "/",
            max_age = ACCESS_TOKEN_LIFETIME_MINUTES * 60
        )

        return response


# Postman test steps for testing logout or logout_all:
#
#     1. Follow the steps for testing login. 
#
#     2. Call logout or logout_all as "POST /auth/logout_all". 
#        (no body needed for either)
#
@router.post(
    f"/{LOGOUT}",
    status_code = status.HTTP_200_OK,
    response_model = LogoutResponseSchema
)
@rate_limiter.limit(VERY_LOW_RATE_LIMIT)
def logout(
    request: Request,
    response: Response,
    session: Session = Depends(get_session)
):
    with sentry_sdk.start_span(op = AUTH, name = "logout"):
        sentry_sdk.set_tag("endpoint", "logout")

        response.headers["Cache-Control"] = "no-store"

        # We still delete cookies even if DB fails because the browser 
        # will no longer have the tokens, but we report the failure.
        delete_auth_token_cookies(request, response)

        # Get the raw refresh token from cookie and revoke the session
        # token.
        raw_refresh_token = request.cookies.get("refresh_token")

        if raw_refresh_token:
            hashed_refresh_token = hashlib.sha256(raw_refresh_token.encode()).hexdigest()

            session_token = session.query(SessionTokenModel).filter(
                SessionTokenModel.refresh_token_hash == hashed_refresh_token
            ).first()

            if session_token:
                now = datetime.now(timezone.utc)

                session_token.revoked_at = now

                try:
                    session.commit()

                except Exception as exc:
                    session.rollback()

                    sentry_sdk.capture_exception(exc)

                    error_response = JSONResponse(
                        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                        content = {"detail": "Could not revoke session token."}
                    )
                    # Preserve Cache-Control and the cookie-deletion headers already set on
                    # the injected response object. Raising HTTPException here would
                    # otherwise discard them, since FastAPI's default exception handler
                    # builds an entirely new Response that never sees them.
                    error_response.raw_headers.extend(response.raw_headers)

                    return error_response                    

        return LogoutResponseSchema(message = "Logged out")


@router.post(
    f"/{LOGOUT_ALL}",
    status_code = status.HTTP_200_OK,
    response_model = LogoutAllResponseSchema
)
@rate_limiter.limit(VERY_LOW_RATE_LIMIT)
def logout_all(
    request: Request,
    response: Response,
    session: Session = Depends(get_session)
):
    with sentry_sdk.start_span(op = AUTH, name = "logout_all"):
        sentry_sdk.set_tag("endpoint", "logout_all")

        response.headers["Cache-Control"] = "no-store"

        # Get the raw refresh token from cookie.
        raw_refresh_token = request.cookies.get("refresh_token")

        # If the browser didn't send a refresh token, we can't identify the
        # user and revoke all their sessions. Logout all must still succeed
        # and we should still delete cookies explicitly (they may still be
        # there if raw_refresh_token is None).
        if not raw_refresh_token:
            # Cookies may still exist even if raw_refresh_token is None.
            delete_auth_token_cookies(request, response)

            return LogoutAllResponseSchema(message = "Logged out of all devices.")

        # Otherwise, hash the refresh token and use it to get the session token for 
        # this session.
        hashed_refresh_token = hashlib.sha256(raw_refresh_token.encode()).hexdigest()

        session_token = session.query(SessionTokenModel).filter(
            SessionTokenModel.refresh_token_hash == hashed_refresh_token
        ).first()

        # If we didn't find a session token, assume there's no active session on this
        # device and do as we did above.
        #
        # This scenario can happen if the user logs out on a different device, the 
        # session expired, or the cookie is stale.
        if not session_token:
            delete_auth_token_cookies(request, response)

            return LogoutAllResponseSchema(message = "Logged out of all devices.")

        # Otherwise, we found a session. Since it has a user id, we can use it to revoke 
        # all sessions for this user.
        now = datetime.now(timezone.utc)

        try:
            # Get all session tokens for this user that have not already been revoked. We
            # are being sure not to re-revoke tokens here so we preserve the original
            # revoke times.
            user_session_tokens = session.query(SessionTokenModel).filter(
                SessionTokenModel.user_id == session_token.user_id,
                SessionTokenModel.revoked_at.is_(None)
            )

            # Update the revoked_at field for those tokens. synchronize_session = False
            # avoids unnecessary overhead by telling SQLAlchemy we're doing a bulk update
            # and it shouldn't try to update in-memory ORM objects.
            user_session_tokens.update(
                {SessionTokenModel.revoked_at: now},
                synchronize_session = False
            )

            session.commit()

        except Exception as exc:
            session.rollback()
            sentry_sdk.capture_exception(exc)

            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = "Could not revoke all session tokens."
            ) from exc


        delete_auth_token_cookies(request, response)

        return LogoutAllResponseSchema(message = "Logged out of all devices.")
    
# Postman test steps for testing active_sessions:
#
#     1. Follow the steps for testing login. 
#
#     2. Call active_sessions as "GET /auth/active_sessions". 
#        (no body needed)
#
@router.get(
    f"/{ACTIVE_SESSIONS}", 
    status_code = status.HTTP_200_OK,
    response_model = ActiveSessionsResponseSchema
)
@rate_limiter.limit(VERY_LOW_RATE_LIMIT)
def get_active_sessions(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
    current_user: UserInternalModel = Depends(get_current_user)
):
    with sentry_sdk.start_span(op = AUTH, name = "get_active_sessions"):
        sentry_sdk.set_tag("endpoint", "get_active_sessions")

        # Prevent caching.
        response.headers["Cache-Control"] = "no-store"

        # Get all session tokens for this user and sort them using created_at.
        user_sessions = session.query(SessionTokenModel).filter(
            SessionTokenModel.user_id == current_user.id
        ).order_by(SessionTokenModel.created_at.desc()).all()

        # Convert the user_sessions to a ActiveSessionsResponse.
        sessions_list = [
            ActiveSessionSchema(
                id = s.id,
                created_at = s.created_at,
                expires_at = s.expires_at,
                revoked_at = s.revoked_at,
                user_agent = s.user_agent,
                ip_address = s.ip_address
            )
            for s in user_sessions
        ]

        return ActiveSessionsResponseSchema(sessions = sessions_list)

# Postman test steps for testing active_sessions:
#
#     1. Follow steps for active_sessions. Copy one of the session_id values you
#        get in the response. 
#
#     2. Call terminate_sessions as POST /auth/terminate_session/[session_id]. (no body needed)
#
# Note that we inject UserInternalModel in endpoints that require authentication to have
# happened first. It forces authentication.
#
# The session_id must be a param in terminate_session as well because we are using it as 
# a path parameter in the URL.
#
@router.post(
    f"/{TERMINATE_SESSION}/{{session_id}}", 
    status_code = status.HTTP_200_OK,
    response_model = TerminateSessionResponseSchema
)
@rate_limiter.limit(VERY_LOW_RATE_LIMIT)
def terminate_session(
    session_id: uuid.UUID,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
    current_user: UserInternalModel = Depends(get_current_user)
):
    with sentry_sdk.start_span(op = AUTH, name = "terminate_session"):
        sentry_sdk.set_tag("endpoint", "terminate_session")

        # Prevent caching.
        response.headers["Cache-Control"] = "no-store"

        # Look up the session token.
        session_token = session.query(SessionTokenModel).filter(
            SessionTokenModel.id == session_id,
            SessionTokenModel.user_id == current_user.id
        ).first()

        if not session_token:
            raise HTTPException(
                status_code = status.HTTP_404_NOT_FOUND,
                detail = "Session not found."
            )

        try:
            # Revoke the session if it's not already revoked. Use atomic CAS in
            # case of concurrent requests so a second commit won't overwrite the
            # first's timestamp. In this case, it won't really hurt anything,
            # but we prevent race conditions and set ourselves up better for 
            # any future modifications.
            updated_session_token = session.query(SessionTokenModel).filter(
                SessionTokenModel.id == session_id,
                SessionTokenModel.user_id == current_user.id,
                SessionTokenModel.revoked_at.is_(None)
            )

            updated = updated_session_token.update(
                {SessionTokenModel.revoked_at: datetime.now(timezone.utc)},
                synchronize_session = False
            )

            # If we failed to update, assume it was already revoked.
            if updated == 0:
                return TerminateSessionResponseSchema(
                    message = "Session already terminated."
                )

            session.commit()

        except Exception as exc:
            session.rollback()

            sentry_sdk.capture_exception(exc)

            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail = "Failed to terminate session."
            ) from exc

        return TerminateSessionResponseSchema(message = "Session terminated successfully.")


# Postman test steps for testing refresh:
#
#     1. Follow steps for testing login. 
#
#     2. Call refresh as "POST /auth/refresh" (no body needed)
#
@router.post(
    f"/{REFRESH}", 
    status_code = status.HTTP_200_OK,
    response_model = RefreshResponseSchema
)
@rate_limiter.limit(VERY_LOW_RATE_LIMIT)
def refresh_token(
    request: Request,
    response: Response,
    session: Session = Depends(get_session)
):
    with sentry_sdk.start_span(op = AUTH, name = "refresh_token"):
        sentry_sdk.set_tag("endpoint", "refresh_token")

        # The frontend should call this endpoint when the access token expires.
        # We read the opaque refresh token from the HttpOnly cookie, hash it,
        # and look up the corresponding SessionTokenModel row in the database.
        #
        # We look at the session token's revoked_at. If it's...
        #
        #     - NULL: We are dealing with the live session token and will rotate it.
        #
        #     - <= CONCURRENT_REFRESH_GRACE_SECONDS: Assume benign concurrency 
        #       (two refreshes raced for the same token and the other one won). 
        #       We will treat the session token as expired in this case.
        #
        #     - > CONCURRENT_REFRESH_GRACE_SECONDS: The session token was already 
        #       rotated a while ago and is now being replayed (maliciously reused). 
        #       We will revoke every session for this user.
        #
        # Refresh tokens are stored as HttpOnly, SameSite = SAME_SITE_VALUE cookies,
        # protecting them from JavaScript access and CSRF attacks.

        # Get the raw opaque refresh token from the cookie and raise an exception if it's 
        # missing.
        raw_refresh_token = request.cookies.get("refresh_token")

        if not raw_refresh_token:
            raise HTTPException(
                status_code = status.HTTP_401_UNAUTHORIZED,
                detail = "Missing refresh token."
            )

        # Hash the raw opaque refresh token and look up the corresponding session and 
        # refresh token id. Raise an exception if the session can't be found.
        hashed_refresh_token = hashlib.sha256(raw_refresh_token.encode()).hexdigest()

        session_token = session.query(SessionTokenModel).filter(
            SessionTokenModel.refresh_token_hash == hashed_refresh_token,
        ).first()

        if not session_token:
            raise HTTPException(
                status_code = status.HTTP_401_UNAUTHORIZED,
                detail = "Invalid refresh token."
            )

        now = datetime.now(timezone.utc)

        # Normalize times for SQLite (naive --> aware)
        expires_at = session_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo = timezone.utc)

        # Make sure the refresh token isn't expired.
        if expires_at < now:
            raise HTTPException(
                status_code = status.HTTP_401_UNAUTHORIZED,
                detail = "Refresh token expired."
            )

        revoked_at = session_token.revoked_at

        # If the session token was already revoked, check to make sure we
        # have not run into concurrency or malicious attack issues.
        if revoked_at is not None:

            # If the revocation occurred within our grace window, assume
            # it's just a concurrency issue.
            if revoked_at.tzinfo is None:
                revoked_at = revoked_at.replace(tzinfo = timezone.utc)
 
            time_since_revocation = (now - revoked_at).total_seconds()
 
            if time_since_revocation <= CONCURRENT_REFRESH_GRACE_SECONDS:
                raise HTTPException(
                    status_code = status.HTTP_401_UNAUTHORIZED,
                    detail = "Refresh token expired or stale."
                )
 
            # If we reach here, the token was rotated outside the 
            # grace window. Assume theft and revoke every active session for the user.
            user_session_tokens = session.query(SessionTokenModel).filter(
                SessionTokenModel.user_id == session_token.user_id,
                SessionTokenModel.revoked_at.is_(None)
            )

            user_session_tokens.update(
                {SessionTokenModel.revoked_at: now},
                synchronize_session = False
            )
 
            session.commit()
 
            raise HTTPException(
                status_code = status.HTTP_401_UNAUTHORIZED, 
                detail = "Refresh token reuse detected. All sessions revoked."
            )

        # If we make it here, assume no concurrency, staleness, or malicious intent. 
        # Prevent double rotation when two refreshes happen concurrently by 
        # updating the refresh token atomically. That is, ensure the refresh token
        # is updated in a single operation (exactly one call to "update"). 
        # The operation should either succeed or do nothing with no partial updates.
        new_refresh_token_id = uuid.uuid4()
        new_raw_refresh_token = secrets.token_urlsafe(32)
        new_hashed_refresh_token = hashlib.sha256(
            new_raw_refresh_token.encode()
        ).hexdigest()

        updated_session_token = session.query(SessionTokenModel).filter(
            SessionTokenModel.id == session_token.id,
            SessionTokenModel.revoked_at.is_(None)
        )

        token_updated = updated_session_token.update(
            {
                SessionTokenModel.refresh_token_id: new_refresh_token_id,
                SessionTokenModel.revoked_at: now
            },
            synchronize_session = False
        )

        # If the token was not updated, another request already rotated the token.
        if token_updated == 0:
            raise HTTPException(
                status_code = status.HTTP_401_UNAUTHORIZED, 
                detail = "Refresh token expired."
            )

        # Create new session token with the new refresh token. Why? A new session 
        # token is created rather than modifying the old one so we can preserve 
        # the old session for auditing, detect token reuse, support multi‑device login, and 
        # safely handle concurrent refreshes. Modifying the existing row
        # would erase this history and break these guarantees.

        expires_at = now + timedelta(days = REFRESH_TOKEN_LIFETIME_DAYS)
        new_session_token = SessionTokenModel(
            user_id = session_token.user_id,
            refresh_token_hash = new_hashed_refresh_token,
            refresh_token_id = new_refresh_token_id,
            created_at = now,
            expires_at = expires_at,
            user_agent = get_user_agent(request),
            ip_address = get_client_ip(request)
        )

        session.add(new_session_token)
        session.commit()

        # Issue new access token
        user = session.query(UserInternalModel).filter(
            UserInternalModel.id == session_token.user_id
        ).first()

        if not user:
            raise HTTPException(
                status_code = status.HTTP_401_UNAUTHORIZED,
                detail = "User no longer exists."
            )

        # Issue a new access token.
        new_access_token = create_access_token(str(user.id), user.is_verified)

        # Set cookies.
        hostname = request.url.hostname
        is_local = hostname in ("localhost", "127.0.0.1", "testserver")

        body = RefreshResponseSchema(
            access_token = new_access_token,
            token_type = "bearer"
        )

        response = JSONResponse(content = body.model_dump())

        # Tell client not to cache anything about the response.
        response.headers["Cache-Control"] = "no-store"

        response.set_cookie(
            key = "refresh_token",
            value = new_raw_refresh_token,
            httponly = True,
            secure = not is_local,
            samesite = SAME_SITE_VALUE,
            path = "/",
            max_age = REFRESH_TOKEN_LIFETIME_DAYS * 24 * 60 * 60
        )

        response.set_cookie(
            key = "access_token",
            value = new_access_token,
            httponly = True,
            secure = not is_local,
            samesite = SAME_SITE_VALUE,
            path = "/",
            max_age = ACCESS_TOKEN_LIFETIME_MINUTES * 60
        )

        return response
    

# Postman test steps for testing refresh:
#
#     1. Follow steps for testing login. 
#
#     2. Call me as "GET /auth/me"
#        (no body needed)
#
@router.get(
    f"/{ME}",
    status_code = status.HTTP_200_OK,
    response_model = MeResponseSchema
)
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

        return MeResponseSchema(
            id = current_user.id,
            email = current_user.email,
            created_at = current_user.created_at
        )


# Postman test steps for testing export user data:
#
#     1. Follow the steps for testing login. 
#
#     2. Call export_user_data as "GET /auth/export_user_data". 
#        (no body needed). To actually be able to see the file, you
#        can run this in PowerShell:
#  
# $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
#
# $session.Cookies.Add(
#     (New-Object System.Net.Cookie("access_token", "YOUR_ACCESS_TOKEN", "/", "localhost"))
# )
#
# $session.Cookies.Add(
#     (New-Object System.Net.Cookie("refresh_token", "YOUR_REFRESH_TOKEN", "/", "localhost"))
# )
#
# Invoke-WebRequest `
#   -Uri "http://localhost:8000/auth/export_user_data" `
#   -WebSession $session `
#   -OutFile "Tea_Tapestry_user_data.json.gz"
#
#       This will save the file to whatever directory you run the command from. Just unzip
#       the file to look at its contents.
#
@router.get(
    f"/{EXPORT_USER_DATA}",
    status_code = status.HTTP_200_OK,
    summary = "Export all user data",
    description = (
        "Returns all data associated with the user, including profile, "
        "sessions, verification tokens, and tea profile notes."
    )
)
@rate_limiter.limit(LOWEST_RATE_LIMIT)
def export_user_data(
    request: Request,
    current_user: UserInternalModel = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    with sentry_sdk.start_span(op = AUTH, name = "export_user_data"):
        sentry_sdk.set_tag("endpoint", "export_user_data")

        _require_fresh_login(current_user)

        # Instantiate repos.
        user_tea_profile_notes_repo = UserTeaProfileNotesRepository(session)
        dsar_log_repo = DSARLogRepository(session)  

        # Create DSAR log entry.
        dsar_log = dsar_log_repo.create_log(              
            user_id = current_user.id,
            request_type = DSAR_REQUEST_EXPORT_USER_DATA
        )
        # Save log id before the commit, since ORM instances expire after commit.
        dsar_log_id = dsar_log.id

        # Commit right away so that if something else fails, these logs will not be
        # rolled back. This is one of the few times we want multiple commits in an 
        # endpoint.
        session.commit()  

        # Instantiate service.
        user_data_export_service = UserDataExportService(
            session = session,
            user_tea_profile_notes_repo = user_tea_profile_notes_repo,
        )

        try:
            user_data = user_data_export_service.export_user_data(current_user.id)
            user_data_JSON_bytes = json.dumps(user_data, indent = 4).encode("utf-8")
            user_data_compressed = gzip.compress(user_data_JSON_bytes)

            dsar_log_repo.mark_fulfilled(dsar_log_id) 

            session.commit()

            # Ex: Tea_Tapestry_user_data 24-Aug-2026 at 16-24-00.json
            timestamp = datetime.now().strftime("%d-%b-%Y at %H-%M-%S")
            file_name = f"Tea_Tapestry_user_data {timestamp}.json.gz"

            response = StreamingResponse(
                iter([user_data_compressed]),
                media_type = "application/json; charset=utf-8",
                headers = {
                    "Content-Disposition": f'attachment; filename="{file_name}"'
                },
            )

            # Prevent caching.
            response.headers["Cache-Control"] = "no-store"

            return response
        
        except Exception as e:
            session.rollback()

            dsar_log_repo.mark_failed(dsar_log_id, notes = str(e))

            session.commit()

            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = "Failed to export user data.",
            )


# Postman test steps for deleting user data:
#
#     1. Follow the steps for testing login. You may want to make a new user for this.
#
#     2. Call delete_user_data as "DELETE /auth/delete_user_data". 
#
@router.delete(
    f"/{DELETE_USER_DATA}",
    status_code = status.HTTP_204_NO_CONTENT,
    summary = "Delete all user-generated data",
    description = (
        "Deletes all user-generated data associated with their account, including "
        "tea profile notes, session tokens, and verification tokens. "
        "The user account itself is preserved."
    )
)
@rate_limiter.limit(LOWEST_RATE_LIMIT)
def delete_user_data(
    request: Request,
    current_user: UserInternalModel = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    with sentry_sdk.start_span(op = AUTH, name = "delete_user_data"):
        sentry_sdk.set_tag("endpoint", "delete_user_data")

        _require_fresh_login(current_user)

        # Instantiate repos.
        user_tea_profile_notes_repo = UserTeaProfileNotesRepository(session)
        dsar_log_repo = DSARLogRepository(session)

        # Create DSAR log entry.
        dsar_log = dsar_log_repo.create_log(           
            user_id = current_user.id,
            request_type = DSAR_REQUEST_DELETE_USER_DATA
        )        
        # Save log id before the commit, since ORM instances expire after commit.
        dsar_log_id = dsar_log.id

        # Commit right away so that if something else fails, these logs will not be
        # rolled back. This is one of the few times we want multiple commits in an 
        # endpoint.
        session.commit()  

        # Instantiate service.
        user_data_deletion_service = UserDataDeletionService(
            session = session,
            user_tea_profile_notes_repo = user_tea_profile_notes_repo,
        )

        try:
            user_data_deletion_service.delete_user_data(current_user.id)

            dsar_log_repo.mark_fulfilled(dsar_log_id)  

            session.commit()

            return Response(status_code = status.HTTP_204_NO_CONTENT)

        except Exception as e:
            session.rollback()

            dsar_log_repo.mark_failed(dsar_log_id, notes = str(e)) 

            session.commit()

            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = "Failed to delete user data.",
            )


# Postman test steps for deleting user data:
#
#     1. Follow the steps for testing login. You may want to make a new user for this.
#
#     2. Call delete_user_account as "DELETE /auth/delete_user_account". 
#
@router.delete(
    f"/{DELETE_USER_ACCOUNT}",
    status_code = status.HTTP_204_NO_CONTENT,
    summary = "Delete user account and all associated data",
    description = (
        "Deletes the user account and all associated data, including profile, "
        "sessions, verification tokens, and tea profile notes. "
        "This action is irreversible."
    )
)
@rate_limiter.limit(LOWEST_RATE_LIMIT)
def delete_user_account(
    request: Request,
    current_user: UserInternalModel = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    with sentry_sdk.start_span(op = AUTH, name = "delete_user_account"):
        sentry_sdk.set_tag("endpoint", "delete_user_account")

        _require_fresh_login(current_user)

        # Require recent password confirmation.
        password_confirmation_repo = PasswordConfirmationRepository(session)
        if not password_confirmation_repo.is_confirmation_valid(current_user.id):
            raise HTTPException(
                status_code = status.HTTP_403_FORBIDDEN,
                detail = "Password confirmation required."
            )

        # Instantiate repos.
        user_tea_profile_notes_repo = UserTeaProfileNotesRepository(session)
        dsar_log_repo = DSARLogRepository(session)

        # Create DSAR log entry .
        dsar_log = dsar_log_repo.create_log(             
            user_id = current_user.id,
            request_type = DSAR_REQUEST_DELETE_USER_ACCOUNT
        )
        # Save log id before the commit, since ORM instances expire after commit.
        dsar_log_id = dsar_log.id

        # Commit right away so that if something else fails, these logs will not be
        # rolled back. This is one of the few times we want multiple commits in an 
        # endpoint.
        session.commit()  

        # Instantiate service.
        user_account_deletion_service = UserAccountDeletionService(
            session = session,
            user_tea_profile_notes_repo = user_tea_profile_notes_repo,
        )

        try:
            user_account_deletion_service.delete_user_account(current_user.id)

            dsar_log_repo.mark_fulfilled(dsar_log_id)  

            session.commit()

            return Response(status_code = status.HTTP_204_NO_CONTENT)

        except Exception as e:
            session.rollback()

            dsar_log_repo.mark_failed(dsar_log_id, notes = str(e)) 

            session.commit()

            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = "Failed to delete user account.",
            )

# Postman test steps for confirming password:
#
#     1. Follow the steps for testing login. You may want to make a new user for this.
#
#     2. Call confirm_password as "POST /auth/confirm_password" with JSON:
#        { "password": "<user's password>" }
#
@router.post(
    f"/{CONFIRM_PASSWORD}",
    status_code = status.HTTP_204_NO_CONTENT,
    summary = "Confirm password for high-risk actions",
    description = (
        "Verifies the user's password and records a short-lived confirmation "
        "allowing high-risk actions such as account deletion."
    )
)
@rate_limiter.limit(LOWEST_RATE_LIMIT)
def confirm_password(
    request: Request,
    payload: ConfirmPasswordInboundSchema,
    current_user: UserInternalModel = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    with sentry_sdk.start_span(op = AUTH, name = "confirm_password"):
        sentry_sdk.set_tag("endpoint", "confirm_password")

        _require_fresh_login(current_user)

        # Validate password.
        if not verify_password(payload.password, current_user.hashed_password):
            raise HTTPException(
                status_code = status.HTTP_401_UNAUTHORIZED,
                detail = "Invalid password."
            )

        # Instantiate repo.
        password_confirmation_repo = PasswordConfirmationRepository(session)

        # Create confirmation entry.
        password_confirmation_repo.create_confirmation(user_id = current_user.id)

        # Commit immediately so confirmation is durable.
        session.commit()

        return Response(status_code = status.HTTP_204_NO_CONTENT)
