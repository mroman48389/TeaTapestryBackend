from starlette import status

from src.utils.auth.jwt_utils import create_refresh_token

def test_get_current_user_valid(client, test_user, access_token_for_test_user):
    response = client.get(
        "/auth/me",
        cookies = {"access_token": access_token_for_test_user}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(test_user.id)


def test_get_current_user_invalid_token(client):
    response = client.get(
        "/auth/me",
        cookies = {"access_token": "invalid_token"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user_wrong_scope(client, test_user, refresh_token_for_test_user):
    response = client.get(
        "/auth/me",
        cookies = {"access_token": refresh_token_for_test_user}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user_missing_token(client):
    response = client.get("/auth/me")
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user_user_deleted(
    client, 
    test_user, 
    access_token_for_test_user, 
    create_test_db
):
    create_test_db.delete(test_user)
    create_test_db.commit()

    response = client.get(
        "/auth/me",
        cookies = {"access_token": access_token_for_test_user}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
