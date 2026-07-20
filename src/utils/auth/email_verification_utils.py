import secrets
import hashlib
from datetime import datetime, timezone, timedelta

from src.db.models.verification_token_model import VerificationToken
from src.constants.token_constants import EMAIL_VERIFICATION

def create_verification_token(user, session):
    # Generate a secure random token.
    raw_token_str = secrets.token_urlsafe(32)

    # Hash the token.
    hashed_token = hashlib.sha256(raw_token_str.encode()).hexdigest()

    # Allow 30 minutes for verification.
    expires_at = datetime.now(timezone.utc) + timedelta(minutes = 30)

    # Create the verification token.
    verification_token = VerificationToken(
        user_id = user.id,
        token_hash = hashed_token,
        expires_at = expires_at,
        purpose = EMAIL_VERIFICATION
    )

    # Store the token.
    session.add(verification_token)
    session.commit()

    # Return the raw token for the email link.
    return raw_token_str

def send_verification_email(user, raw_token):
    verification_link = f"https://tea-tapestry.netlify.app/verify-email?token={raw_token}"

    # TODO: integrate email provider (SendGrid, Mailgun, SES)
    print(f"Send email to {user.email}: {verification_link}")
