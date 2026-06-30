from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from uuid import UUID

# Break up the user information into several schema for security and transparency.

# NOT exposed to the client. Corresponds to UserModel. Internal backend representation of a user. 
class UserInternalSchema(BaseModel):
    id: UUID
    email: EmailStr
    hashed_password: str
    created_at: datetime
    updated_at: datetime
    last_login: datetime | None = None

    class Config:
        from_attributes = True

# Exposed to the client. Purely for when the user is signing up for an account. Intentionally 
# minimal and strict so the client cannot inject fields and security is maintained.
#
# Note that this one is created from JSON rather than SQLAlchemy ORM objects, so we don't need
# the "from_attributes = True" to read attributes like we do with the other schema.
class UserInboundSchema(BaseModel):
    # EmailStr has built-in email validation. 
    email: EmailStr
    password: str = Field(min_length = 8)

# Exposed to the client. Public API contract used when the API returns a user object 
# to the frontend. This should be used when returning a new user after they sign up, 
# after the user logs in, whenever we need to fetch the current user, and generally 
# when returning user data in any endpoint.
#
# Contains fields that travel from server to client; ones that a client must not 
# control for security anddata integrity reasons (such as IDs, created_at, timestamps).
class UserOutboundSchema(BaseModel):
    id: UUID
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True

# Mirrors UserInboundSchema, but separate for clarity.
class LoginSchema(BaseModel):
    email: EmailStr
    password: str = Field(min_length = 8)