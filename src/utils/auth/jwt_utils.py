import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
import jwt  

from src.constants.jwt_constants import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
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

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm = JWT_ALGORITHM)
    return token


def create_refresh_token(user_id: str, email_verified: bool) -> str:
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
        "jti": str(uuid.uuid4())                  # JWT ID; guarantees uniqueness
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm = JWT_ALGORITHM)
    return token


def decode_token(token: str) -> Dict[str, Any]:
    """
        Decode and verify a JWT. Verifies signature, expiration, algorithm.
        Raises jwt.ExpiredSignatureError if expired and jwt.InvalidTokenError if invalid.
    """
    return jwt.decode(token, JWT_SECRET_KEY, algorithms = [JWT_ALGORITHM])


def token_expired(payload: Dict[str, Any]) -> bool:
    """
        Check if a decoded token payload is expired.
    """
    exp = payload.get("exp")
    if exp is None:
        return True

    return exp < int(time.time())
