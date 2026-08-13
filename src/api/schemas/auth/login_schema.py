from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Mirrors UserInboundSchema, but separate for clarity.
class LoginSchema(BaseModel):
    email: EmailStr
    password: str = Field(min_length = 8)

    # Prevent client from adding extra fields.
    model_config = ConfigDict(extra = "forbid")

class LoginResponseSchema(BaseModel):
    access_token: str
    token_type: str
