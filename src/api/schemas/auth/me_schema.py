from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class MeResponseSchema(BaseModel):
    id: UUID
    email: str
    created_at: datetime