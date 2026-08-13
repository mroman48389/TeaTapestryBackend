import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
import jwt  
from uuid import UUID

from src.core.config import settings
from src.constants.jwt_constants import (
    ACCESS_TOKEN_LIFETIME_MINUTES,
    REFRESH_TOKEN_LIFETIME_DAYS
)
from src.api.schemas.auth.refresh_token_schema import RefreshTokenPayloadSchema
from src.api.schemas.auth.access_token_schema import AccessTokenPayloadSchema
from src.utils.log_utils import safe_debug

def create_access_token(user_id: str, email_verified: bool) -> str:
    """
        Create a short-lived JWT access token for protected API routes.
        Sent in Authorization: Bearer <token>.
    """
    datetime_now = datetime.now(timezone.utc)
    datetime_expired = datetime_now + timedelta(minutes = ACCESS_TOKEN_LIFETIME_MINUTES)

    payload = AccessTokenPayloadSchema(
        sub = UUID(user_id),                       
        scope = "access",                      
        email_verified = email_verified,
        iat = int(datetime_now.timestamp()),    
        exp = int(datetime_expired.timestamp()) 
    )

    token = jwt.encode(
        payload.model_dump(mode = "json"), 
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

    payload = RefreshTokenPayloadSchema(
        sub = UUID(user_id),                           
        scope = "refresh",                       
        email_verified = email_verified,
        iat = int(datetime_now.timestamp()),     
        exp = int(datetime_expired.timestamp()), 
        jti = str(uuid.uuid4()),                 
        refresh_token_id = UUID(refresh_token_id)
    )

    token = jwt.encode(
        payload.model_dump(mode = "json"), 
        settings.refresh_token_secret, 
        algorithm = settings.refresh_token_algorithm
    )
    return token


def decode_access_token(token: str) -> AccessTokenPayloadSchema:
    """
        Decode and verify a JWT. Verifies signature, expiration, algorithm.
        Raises jwt.ExpiredSignatureError if expired and jwt.InvalidTokenError if invalid.
    """
    payload_dict = jwt.decode(
        token,         
        settings.access_token_secret, 
        algorithms = [settings.access_token_algorithm]
    )

    payload = AccessTokenPayloadSchema.model_validate(payload_dict)

    return payload


def decode_refresh_token(token: str) -> RefreshTokenPayloadSchema:

    payload_dict = jwt.decode(
        token,         
        settings.refresh_token_secret, 
        algorithms = [settings.refresh_token_algorithm]
    )

    payload = RefreshTokenPayloadSchema.model_validate(payload_dict)

    return payload


def token_expired(payload: Dict[str, Any]) -> bool:
    """
        Check if a decoded token payload is expired.
    """
    exp = payload.get("exp")

    # Treat tokens without exp as expired (invalid).
    if exp is None:
        return True

    return exp < int(time.time())
