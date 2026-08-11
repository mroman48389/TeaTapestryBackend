from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
import uuid

# Note that these are related, but do not correspond to, SessionTokenModel.
# That one serves the database layer and these serve the API layer. 

# Used to get a list of active sessions for the user via an endpoint.
class ActiveSessionSchema(BaseModel):
    id: uuid.UUID
    created_at: datetime
    expires_at: datetime
    revoked_at: Optional[datetime]
    user_agent: Optional[str]
    ip_address: Optional[str]

class ActiveSessionsResponse(BaseModel):
    sessions: List[ActiveSessionSchema]

# Used to terminate a specific session.
class TerminateSessionResponse(BaseModel):
    message: str
