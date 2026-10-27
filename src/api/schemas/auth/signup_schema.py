from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import datetime
from uuid import UUID

# Exposed to the client. Purely for when the user is signing up for an account. Intentionally 
# minimal and strict so the client cannot inject fields and security is maintained.
#
# Note that this one is created from JSON rather than SQLAlchemy ORM objects, so we don't need
# the "from_attributes = True" to read attributes like we do with the other schema.
class SignupSchema(BaseModel):
    # EmailStr has built-in email validation. 
    email: EmailStr
    password: str = Field(min_length = 8)
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

    # Prevent client from adding extra fields.
    model_config = ConfigDict(extra = "forbid")