from starlette import status

from src.constants.route_constants import (
    AUTH_ME_PREFIX
)

def test_get_current_user_valid(client, access_token_for_test_user):
    user = access_token_for_test_user["user"]
    access_token = access_token_for_test_user["access_token"]
    
    client.cookies.set("access_token", access_token)
    response = client.get(AUTH_ME_PREFIX)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(user.id)


def test_get_current_user_invalid_token(client):
    client.cookies.set("access_token", "invalid_token")
    response = client.get(AUTH_ME_PREFIX)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user_wrong_scope(client, refresh_token_for_test_user):
    client.cookies.set("access_token", refresh_token_for_test_user)
    response = client.get(AUTH_ME_PREFIX)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user_missing_token(client):
    response = client.get(AUTH_ME_PREFIX)
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user_user_deleted(
    client, 
    access_token_for_test_user, 
    create_test_db
):
    user = access_token_for_test_user["user"]
    access_token = access_token_for_test_user["access_token"]

    create_test_db.delete(user)
    create_test_db.commit()

    client.cookies.set("access_token", access_token)
    response = client.get(AUTH_ME_PREFIX)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
