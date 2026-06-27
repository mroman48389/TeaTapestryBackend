import pytest
from fastapi import HTTPException

from src.utils.auth.password_utils import (
    hash_password,
    verify_password,
    validate_password_strength,
)


def test_hash_password_produces_different_hashes_for_each_call():
    pw = "MyPassword@123"

    hash1 = hash_password(pw)
    hash2 = hash_password(pw)

    assert hash1 != pw
    assert hash2 != pw
    assert hash1 != hash2  # bcrypt uses random salt
    assert isinstance(hash1, str)
    assert isinstance(hash2, str)


def test_verify_password_correct_and_incorrect():
    pw = "MyPassword@123"
    hashed = hash_password(pw)

    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword!123", hashed) is False


def test_validate_password_strength_accepts_strong_password():
    # Should NOT raise an exception.
    validate_password_strength("StrongPassword@123")


@pytest.mark.parametrize("weak_password, message", [
    ("short", "at least 8 characters"),
    ("all@lowercase@123", "uppercase"),
    ("ALL@UPPERCASE@123", "lowercase"),
    ("No@Digits", "number"),
    ("NoSymbols123", "symbol"),
    ("Has spaces 123!", "spaces"),
])
def test_validate_password_strength_rejects_weak_passwords(weak_password, message):
    with pytest.raises(HTTPException) as exc:
        validate_password_strength(weak_password)

    # We should find message in the detail field of each exception.
    assert message in exc.value.detail
