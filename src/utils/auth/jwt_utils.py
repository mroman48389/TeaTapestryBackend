import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
import jwt  

from src.core.config import settings
from src.constants.jwt_constants import (
    ACCESS_TOKEN_LIFETIME_MINUTES,
    REFRESH_TOKEN_LIFETIME_DAYS
)

def create_access_token(user_id: str, email_verified: bool) -> str:
    """
        Create a short-lived JWT access token for protected API routes.
        Sent in Authorization: Bearer <token>.
    """
    datetime_now = datetime.now(timezone.utc)
    datetime_expired = datetime_now + timedelta(minutes = ACCESS_TOKEN_LIFETIME_MINUTES)

    payload = {
        "sub": user_id,                          # subject (user ID)
        "scope": "access",                       # token type
        "email_verified": email_verified,
        "iat": int(datetime_now.timestamp()),    # issued at
        "exp": int(datetime_expired.timestamp()) # expiration
    }

    token = jwt.encode(
        payload, 
        settings.access_token_secret, 
        algorithm = settings.access_token_algorithm
    )
    return token


def create_refresh_token(
    user_id: str, 
    email_verified: bool,
    refresh_token_id: str
) -> str:
    """
        Create a long-lived JWT refresh token.
        Stored in HttpOnly cookie.
    """
    datetime_now = datetime.now(timezone.utc)
    datetime_expired = datetime_now + timedelta(days = REFRESH_TOKEN_LIFETIME_DAYS)

    payload = {
        "sub": user_id,                           # subject (user ID)
        "scope": "refresh",                       # token type
        "email_verified": email_verified,
        "iat": int(datetime_now.timestamp()),     # issued at
        "exp": int(datetime_expired.timestamp()), # expiration
        "jti": str(uuid.uuid4()),                 # JWT ID; guarantees uniqueness
        "refresh_token_id": refresh_token_id
    }

    token = jwt.encode(
        payload, 
        settings.refresh_token_secret, 
        algorithm = settings.refresh_token_algorithm
    )
    return token


def decode_access_token(token: str) -> Dict[str, Any]:
    """
        Decode and verify a JWT. Verifies signature, expiration, algorithm.
        Raises jwt.ExpiredSignatureError if expired and jwt.InvalidTokenError if invalid.
    """
    return jwt.decode(
        token,         
        settings.access_token_secret, 
        algorithms = [settings.access_token_algorithm]
    )


def decode_refresh_token(token: str) -> Dict[str, Any]:
    return jwt.decode(
        token,         
        settings.refresh_token_secret, 
        algorithms = [settings.refresh_token_algorithm]
    )


def token_expired(payload: Dict[str, Any]) -> bool:
    """
        Check if a decoded token payload is expired.
    """
    exp = payload.get("exp")
    if exp is None:
        return True

    return exp < int(time.time())
