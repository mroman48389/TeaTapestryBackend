from pydantic import BaseModel, EmailStr, Field

# Inbound schema for requesting a password reset. The client will send an email. 
# No outbound representation is needed. The server will only return a success message.
class PasswordResetRequestSchema(BaseModel):
    email: EmailStr

    # Prevent client from adding extra fields.
    class Config:
        extra = "forbid"

# Inbound schema for submitting a password reset. The client will send the token 
# and new password. No outbound representation is needed.  The sever will only return 
# a success message.
class PasswordResetSubmissionSchema(BaseModel):

    # ... = field is required (must be provided by the client) and has no default.
    token: str = Field(..., min_length = 1)
    new_password: str = Field(..., min_length = 8)

    # Prevent client from adding extra fields.
    class Config:
        extra = "forbid"