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
    user_id = uuid.uuid4()
    token = create_access_token(str(user_id), True)
    payload = decode_access_token(token)

    assert payload.sub == user_id
    assert payload.scope == "access"
    assert isinstance(payload.iat, int)
    assert isinstance(payload.exp, int)


###################################################################


def test_create_refresh_token_payload_correct():
    user_id = uuid.uuid4()
    token = create_refresh_token(str(user_id), True, str(uuid.uuid4()))
    payload = decode_refresh_token(token)

    assert payload.sub == user_id
    assert payload.scope == "refresh"
    assert isinstance(payload.iat, int)
    assert isinstance(payload.exp, int)
    assert isinstance(payload.jti, str)


def test_create_refresh_token_produces_unique_tokens_per_call():
    user_id = uuid.uuid4()
    token_1 = create_refresh_token(str(user_id), True, str(uuid.uuid4()))
    token_2 = create_refresh_token(str(user_id), True, str(uuid.uuid4()))

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


def test_token_expired_true_when_missing_exp():
    payload = {}

    assert token_expired(payload) is True


def test_token_expired_false_when_valid():
    payload = {"exp": int(time.time()) + 10}

    assert token_expired(payload) is False
