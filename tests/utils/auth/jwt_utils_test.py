import pytest
import jwt
import time
import uuid

from src.utils.auth.jwt_utils import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    token_expired
)


def test_create_access_token_payload_correct():
    token = create_access_token("testUser", True)
    payload = decode_access_token(token)

    assert payload["sub"] == "testUser"
    assert payload["scope"] == "access"
    assert "iat" in payload
    assert "exp" in payload


###################################################################


def test_create_refresh_token_payload_correct():
    token = create_refresh_token("testUser", True, str(uuid.uuid4()))
    payload = decode_refresh_token(token)

    assert payload["sub"] == "testUser"
    assert payload["scope"] == "refresh"
    assert "iat" in payload
    assert "exp" in payload
    assert "jti" in payload


def test_create_refresh_token_produces_unique_tokens_per_call():
    token_1 = create_refresh_token("testUser", True, str(uuid.uuid4()))
    token_2 = create_refresh_token("testUser", True, str(uuid.uuid4()))

    assert token_1 != token_2


####################################################################


def test_decode_access_token_rejects_invalid_token():
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token("not_a_real_token")


def test_decode_refresh_token_rejects_invalid_token():
    with pytest.raises(jwt.InvalidTokenError):
        decode_refresh_token("not_a_real_token")
        

####################################################################


def test_token_expired_true_when_expired():
    payload = {"exp": int(time.time()) - 10}

    assert token_expired(payload) is True


def test_token_expired_false_when_valid():
    payload = {"exp": int(time.time()) + 10}

    assert token_expired(payload) is False
