import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import jwt  # PyJWT

# Set this in environment later.
# Signing key, known only be the backend. Keep safe to avoid token 
# forging.
JWT_SECRET_KEY = "CHANGE_THIS_IN_PRODUCTION"
JWT_ALGORITHM = "HS256"

ACCESS_TOKEN_LIFETIME_MINUTES = 15
REFRESH_TOKEN_LIFETIME_DAYS = 7

def create_access_token(user_id: str) -> str:
    """
        Create a short-lived JWT access token for protected API routes.
        Sent in Authorization: Bearer <token>.
    """
    datetime_now = datetime.now(timezone.utc)
    datetime_expired = datetime_now + timedelta(minutes = ACCESS_TOKEN_LIFETIME_MINUTES)

    payload = {
        "sub": user_id,                          # subject (user ID)
        "scope": "access",                       # token type
        "iat": int(datetime_now.timestamp()),    # issued at
        "exp": int(datetime_expired.timestamp()) # expiration
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm = JWT_ALGORITHM)
    return token


def create_refresh_token(user_id: str) -> str:
    """
        Create a long-lived JWT refresh token.
        Stored in HttpOnly cookie.
    """
    datetime_now = datetime.now(timezone.utc)
    datetime_expired = datetime_now + timedelta(days = REFRESH_TOKEN_LIFETIME_DAYS)

    payload = {
        "sub": user_id,
        "scope": "refresh",
        "iat": int(datetime_now.timestamp()),
        "exp": int(datetime_expired.timestamp())
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
