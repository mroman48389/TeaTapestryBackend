from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import datetime
from uuid import UUID

# Break up the user information into several schema for security and transparency.

# NOT exposed to the client. Corresponds to UserInternalModel. Internal backend representation of a user. 
class UserSchema(BaseModel):
    id: UUID
    email: EmailStr
    # display_name does not have to be unique. Allow letters, numbers, hyphens, whitespace. 
    # Used to identify the user in UI  such as the app bar, user profile display, 
    # comments, reviews, chatting.
    display_name: str = Field(
        min_length = 1,
        max_length = 30,
        pattern = r"^[A-Za-z0-9\-\s]+$"
    )
    # username must be unique. Allows lowercase letters, numbers, underscores, hyphens. Normalized and 
    # stored as all lowercase. It will be used for looking up users, querying databases, URLs, mentions.
    username: str = Field(
        min_length = 3,
        max_length = 30,
        pattern = r"^[a-z0-9_-]+$"
    )
    bio: str | None = Field(
        default = None,
        max_length = 500
    )
    # Reference to where the avatar image is stored. (Currently, we automatically generate
    # initials instead. If we implement this in the future, we need a way of preventing
    # inappropriate image uploads and / or reporting such things).
    avatar_url: str | None = None

    hashed_password: str
    created_at: datetime
    updated_at: datetime
    last_login: datetime | None = None
    is_verified: bool
    verified_at: datetime | None = None

    model_config = ConfigDict(from_attributes = True)


# Exposed to the client. Public API contract used when the API returns a user object 
# to the frontend. This should be used when returning a new user after they sign up, 
# after the user logs in, whenever we need to fetch the current user, and generally 
# when returning user data in any endpoint.
#
# Contains fields that travel from server to client; ones that a client must not 
# control for security anddata integrity reasons (such as IDs, created_at, timestamps).
class UserResponseSchema(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str = Field(
        min_length = 1,
        max_length = 30,
        pattern = r"^[A-Za-z0-9\-\s]+$"
    )
    username: str = Field( 
        min_length = 3,
        max_length = 30,
        pattern = r"^[a-z0-9_-]+$"
    )
    bio: str | None = None
    avatar_url: str | None = None

    created_at: datetime
    is_verified: bool
    verified_at: datetime | None = None

    model_config = ConfigDict(from_attributes = True)