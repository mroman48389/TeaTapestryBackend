import bcrypt

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
