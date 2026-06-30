from starlette import status

from src.db.models.user_models import UserInternalModel
from src.utils.auth.password_utils import verify_password, hash_password

def test_signup_creates_user(client, create_test_db):
    payload = {
        "email": "someUser@gmail.com",
        "password": "MyPassword@123"
    }

    response = client.post("/auth/signup", json = payload)

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()

    assert "id" in data
    assert "created_at" in data
    assert data["email"] == payload["email"]

    # Verify user exists in DB
    user = create_test_db.query(UserInternalModel).filter_by(email = payload["email"]).first()

    assert user is not None

# Note that we need the create_test_db fixture even though we're not using it in the body of the
# test because the client fixture overrides FastAPI's get_session dependency. If we don't include
# it, the test database will not exist.
def test_signup_duplicate_email_rejected(client, create_test_db):
    payload = {
        "email": "someUser@gmail.com",
        "password": "MyPassword@123"
    }

    # Sign up once.
    client.post("/auth/signup", json = payload)

    # A second signup should fail.
    response = client.post("/auth/signup", json = payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in response.json()["detail"]


def test_signup_hashes_password(client, create_test_db):
    payload = {
        "email": "someUser@gmail.com",
        "password": "MyPassword@123"
    }

    client.post("/auth/signup", json = payload)

    user = create_test_db.query(UserInternalModel).filter_by(email = payload["email"]).first()

    assert user is not None
    assert user.hashed_password != payload["password"]
    assert verify_password(payload["password"], user.hashed_password)

#################################################################################################

def test_login_success(client, create_test_db):
    # Create and add a user. 
    # 
    # NOTE: the domain gets normalized by EmailStr to all lowercase, so do NOT include
    # uppercase letters in the domain name or the tests will fail!
    user = UserInternalModel(
        email = "someUsername@somedomain.com",
        hashed_password = hash_password("MyPassword@123")
    )
    create_test_db.add(user)
    create_test_db.commit()

    print(create_test_db.query(UserInternalModel).all())

    # Log in with the same email and password.
    payload = {
        "email": "someUsername@somedomain.com",
        "password": "MyPassword@123"
    }

    response = client.post("/auth/login", json = payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["token_type"] == "bearer"


def test_login_invalid_password(client, create_test_db):
    # Create and add a user.
    user = UserInternalModel(
        email = "someUsername@somedomain.com",
        hashed_password = hash_password("MyPassword@123")
    )
    create_test_db.add(user)
    create_test_db.commit()

    # Try to log in with the same email but the wrong password.
    payload = {
        "email": "someUsername@somedomain.com",
        "password": "WrongPassword@123"
    }

    response = client.post("/auth/login", json = payload)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid email or password" in response.json()["detail"]


def test_login_unknown_email(client):
    # Try to log in with an account that doesn't exist in the database.
    payload = {
        "email": "someUsername@somedomain.com",
        "password": "MyPassword@123"
    }

    response = client.post("/auth/login", json = payload)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

#################################################################################################

def test_logout_deletes_cookie(client):
    response = client.post("/auth/logout")

    # The logout endpoint should send a Set-Cookie header that deletes the cookie.
    set_cookie_header = response.headers.get("set-cookie")

    assert set_cookie_header is not None
    assert "refresh_token=" in set_cookie_header
    assert "Max-Age=0" in set_cookie_header or "expires=" in set_cookie_header

    assert response.json()["message"] == "Logged out"

#################################################################################################

def test_refresh_issues_new_access_token(client, test_user, refresh_token_for_test_user):
    response = client.post(
        "/auth/refresh",
        cookies = {"refresh_token": refresh_token_for_test_user}
    )

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    assert "access_token" in data
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 0


def test_refresh_rotates_refresh_token(
    client,
    test_user,
    refresh_token_for_test_user
):
    response = client.post(
        "/auth/refresh",
        cookies = {"refresh_token": refresh_token_for_test_user}
    )

    assert response.status_code == status.HTTP_200_OK

    # The refresh endpoint should set a new refresh token cookie.
    set_cookie_header = response.headers.get("set-cookie")

    # Parse out the new token
    new_refresh_token = set_cookie_header.split("refresh_token=")[1].split(";")[0]

    assert set_cookie_header is not None
    assert "refresh_token=" in set_cookie_header
    # Ensure the new token is different from the old one.
    assert new_refresh_token != refresh_token_for_test_user

#################################################################################################

def test_me_returns_user_details(client, test_user, access_token_for_test_user):
    # print("DEBUG: test_user.id:", test_user.id, type(test_user.id))
    # print("DEBUG: access_token:", access_token_for_test_user)

    response = client.get(
        "/auth/me",
        headers = {"Authorization": f"Bearer {access_token_for_test_user}"}
    )

    # print("DEBUG: response.status_code:", response.status_code)
    # print("DEBUG: response.text:", response.text)

    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert data["id"] == str(test_user.id)
    assert data["email"] == test_user.email
    assert data["created_at"] != ""
