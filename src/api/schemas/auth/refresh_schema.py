from pydantic import BaseModel

class RefreshResponseSchema(BaseModel):
    access_token: str
    token_type: str
