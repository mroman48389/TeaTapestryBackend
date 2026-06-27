import bcrypt
import re
from fastapi import HTTPException
from starlette import status

def hash_password(plaintext_password: str) -> str:
    """
        Hash a plaintext password using bcrypt.
        Returns a UTF-8 string suitable for storing in the database.
    """

    hashed_password = bcrypt.hashpw(plaintext_password.encode("utf-8"), bcrypt.gensalt())
    return hashed_password.decode("utf-8")


def verify_password(plaintext_password: str, hashed_password: str) -> bool:
    """
        Verify a plaintext password against a stored bcrypt hash.
    """

    return bcrypt.checkpw(
        plaintext_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )

def validate_password_strength(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Password must be at least 8 characters long."
        )

    if not re.search(r"[A-Z]", password):
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Password must contain at least one uppercase letter."
        )

    if not re.search(r"[a-z]", password):
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Password must contain at least one lowercase letter."
        )

    if not re.search(r"[0-9]", password):
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Password must contain at least one number."
        )

    if not re.search(r"[^A-Za-z0-9]", password):
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Password must contain at least one symbol."
        )

    if re.search(r"\s", password):
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Password cannot contain spaces."
        )
