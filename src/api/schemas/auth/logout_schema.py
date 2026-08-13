from pydantic import BaseModel

class LogoutResponseSchema(BaseModel):
    message: str

class LogoutAllResponseSchema(BaseModel):
    message: str