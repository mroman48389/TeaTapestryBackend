from starlette import status
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from src.utils.session_utils import get_session
from src.db.models.auth.user_models import UserInternalModel
from src.utils.auth.jwt_utils import decode_access_token

def get_current_user(
    request: Request,
    session: Session = Depends(get_session)
):
    # Try to get an access token from cookies.
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED, 
            detail = "Not authenticated"
        )

    # Decode token, and make sure it's an access token.
    try:
        payload = decode_access_token(token)

    except Exception:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid or expired access token."
        )

    # Make sure it's an access token.
    if payload.scope != "access":
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED, 
            detail = "Invalid token scope."
        )

    # Get the user.
    user_id = payload.sub

    user = session.query(UserInternalModel).filter(
        UserInternalModel.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "User no longer exists."
        )

    return user
