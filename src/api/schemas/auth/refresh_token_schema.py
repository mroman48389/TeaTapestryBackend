from pydantic import BaseModel
from uuid import UUID
from typing import Literal

class RefreshTokenPayloadSchema(BaseModel):
    sub: UUID # subject (user ID)
    scope: Literal["refresh"] # token type
    email_verified: bool
    iat: int # issued at; int(datetime_now.timestamp())
    exp: int # expiration; int(datetime_expired.timestamp())
    jti: str # JWT ID; guarantees uniqueness; str(uuid.uuid4())
    refresh_token_id: UUID