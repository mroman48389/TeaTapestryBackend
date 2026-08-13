from pydantic import BaseModel
from uuid import UUID
from typing import Literal

class AccessTokenPayloadSchema(BaseModel):
    sub: UUID # subject (user ID)
    scope: Literal["access"] # token type
    email_verified: bool
    iat: int # issued at; int(datetime_now.timestamp())
    exp: int # expiration; int(datetime_expired.timestamp())
