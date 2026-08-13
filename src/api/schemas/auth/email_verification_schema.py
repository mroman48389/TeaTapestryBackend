from pydantic import BaseModel

class SendVerificationResponseSchema(BaseModel):
    message: str

class VerifyEmailResponseSchema(BaseModel):
    message: str

