import uuid
from starlette import status
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from src.utils.session_utils import get_session
from src.db.models.user_models import UserInternalModel
from src.utils.auth.jwt_utils import decode_token

# FastAPI’s built-in bearer token extractor
bearer_scheme = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: Session = Depends(get_session)
):
    # print("DEBUG: get_current_user called")

    token = credentials.credentials

    # print("DEBUG: raw token:", token)

    # Decode token.
    try:
        payload = decode_token(token)

        # print("DEBUG: decoded payload:", payload)

    except Exception:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid or expired access token."
        )

    # Ensure the token is an access token.
    if payload.get("scope") != "access":
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid token scope."
        )

    # Get the user.
    user_id = uuid.UUID(payload.get("sub"))

    # print("DEBUG: user_id from token:", user_id)

    user = session.query(UserInternalModel).filter(
        UserInternalModel.id == user_id
    ).first()

    # try:
    #     user = session.query(UserInternalModel).filter(
    #         UserInternalModel.id == user_id
    #     ).first()
    #     print("DEBUG: user from DB:", user)

    # except Exception as e:
    #     print("DEBUG: SQLAlchemy exception:", repr(e))
    #     raise

    # print("DEBUG: user from DB:", user)

    if not user:
        # print("DEBUG: user not found in DB")

        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "User no longer exists."
        )

    return user
