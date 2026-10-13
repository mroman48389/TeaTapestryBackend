import secrets
import hashlib
from datetime import datetime, timezone, timedelta

from src.utils.log_utils import safe_debug, safe_info, safe_exception
from src.db.models.auth.verification_token_model import VerificationTokenModel
from src.constants.app_constants import FRONTEND_BASE_URL
from src.constants.token_constants import VERIF_TOKEN_EXPIR_MIN

def create_raw_verification_token(user, session, purpose, expiration_minutes = VERIF_TOKEN_EXPIR_MIN):
    try:
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

        safe_info(f"Created {purpose} token for user {user.id}")

        # Return the raw token for the email link.
        return raw_token_str

    except Exception:
        safe_exception("Error creating verification token.")
        
        return None


# Builds links sent by the frontend. Used in emails that the user clicks.
# The frontend will call the backend to verify the token. 
# Ex: https://tea-tapestry.netlify.app/verify_email?token=abc123
# Note that the page looks similar to route constants, but they are not the
# same, and we should not mix them. 
def build_frontend_token_link(page: str, raw_token: str) -> str:
    return f"{FRONTEND_BASE_URL}/{page}?token={raw_token}"
