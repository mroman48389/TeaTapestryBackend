import secrets
import hashlib
from datetime import datetime, timezone, timedelta

from src.utils.log_utils import safe_debug, safe_info
from src.db.models.verification_token_model import VerificationTokenModel
from src.constants.app_constants import FRONTEND_BASE_URL

def create_raw_verification_token(user, session, purpose, expiration_minutes = 30):
    # Generate a secure random token.
    raw_token_str = secrets.token_urlsafe(32)

    # Hash the token.
    hashed_token = hashlib.sha256(raw_token_str.encode()).hexdigest()

    # Allow 30 minutes for verification.
    expires_at = datetime.now(timezone.utc) + timedelta(minutes = expiration_minutes)

    # Create the verification token.
    verification_token = VerificationTokenModel(
        user_id = user.id,
        token_hash = hashed_token,
        expires_at = expires_at,
        purpose = purpose # ex: EMAIL_VERIFICATION
    )

    # Store the token.
    session.add(verification_token)
    session.commit()

    safe_info(f"Created {purpose} token for user {user.id}")

    # Return the raw token for the email link.
    return raw_token_str

# Builds links sent by the frontend. Used in emails that the user clicks.
# The frontend will call the backend to verify the token. 
# Ex: https://tea-tapestry.netlify.app/verify_email?token=abc123
# Note that the page looks similar to route constants, but they are not the
# same, and we should not mix them. 
def build_frontend_token_link(page: str, raw_token: str) -> str:
    return f"{FRONTEND_BASE_URL}/{page}?token={raw_token}"


def send_verification_email(user, raw_token):
    verification_link = build_frontend_token_link("verify-email", raw_token)

    # TODO: integrate email provider (SendGrid, Mailgun, SES)
    safe_debug(f"Send email to {user.email}: {verification_link}")


def send_password_reset_email(user, raw_token):
    password_reset_link = build_frontend_token_link("reset-password", raw_token)

    # TODO: integrate email provider
    safe_debug(f"Send password reset email to {user.email}: {password_reset_link}")
