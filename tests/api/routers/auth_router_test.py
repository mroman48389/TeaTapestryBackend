from starlette import status

from src.db.models.user_models import UserInternalModel
from src.utils.auth.password_utils import verify_password, hash_password
from src.constants.route_constants import (
    AUTH_SIGNUP_PREFIX,
    AUTH_LOGIN_PREFIX,
    AUTH_LOGOUT_PREFIX,
    AUTH_REFRESH_PREFIX,
    AUTH_ME_PREFIX
)

# ---------------------------------------------------------
# SIGNUP
# ---------------------------------------------------------

class TestAuthSignup:

    def test_signup_creates_user(self, client, create_test_db):
        payload = {
            "email": "someUser@gmail.com",
            "password": "MyPassword@123",
            "display_name": "Some User"
        }

        response = client.post(AUTH_SIGNUP_PREFIX, json = payload)

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()

        assert "id" in data
        assert "created_at" in data
        assert data["email"] == payload["email"]

        # Verify user exists in DB
        user = create_test_db.query(UserInternalModel).filter_by(email = payload["email"]).first()

        assert user is not None

    # Note that we need the create_test_db fixture even though we're not using it in 
    # the body of the test because the client fixture overrides FastAPI's get_session 
    # dependency. If we don't include it, the test database will not exist.
    def test_signup_duplicate_email_rejected(self, client, create_test_db):
        payload = {
            "email": "someUser@gmail.com",
            "password": "MyPassword@123",
            "display_name": "Some User"
        }

        # Sign up once.
        client.post(AUTH_SIGNUP_PREFIX, json = payload)

        # A second signup should fail.
        response = client.post(AUTH_SIGNUP_PREFIX, json = payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"]


    def test_signup_hashes_password(self, client, create_test_db):
        payload = {
            "email": "someUser@gmail.com",
            "password": "MyPassword@123",
            "display_name": "Some User"
        }

        client.post(AUTH_SIGNUP_PREFIX, json = payload)

        user = create_test_db.query(UserInternalModel).filter_by(email = payload["email"]).first()

        assert user is not None
        assert user.hashed_password != payload["password"]
        assert verify_password(payload["password"], user.hashed_password)


# ---------------------------------------------------------
# LOGIN
# ---------------------------------------------------------

class TestAuthLogin:

    def test_login_success(self, client, create_test_db):
        # Create and add a user. 
        # 
        # NOTE: the domain gets normalized by EmailStr to all lowercase, so do NOT include
        # uppercase letters in the domain name or the tests will fail!
        user = UserInternalModel(
            email = "someUsername@somedomain.com",
            hashed_password = hash_password("MyPassword@123"),
            display_name = "Some User"
        )
        create_test_db.add(user)
        create_test_db.commit()

        print(create_test_db.query(UserInternalModel).all())

        # Log in with the same email and password.
        payload = {
            "email": "someUsername@somedomain.com",
            "password": "MyPassword@123"
        }

        response = client.post(AUTH_LOGIN_PREFIX, json = payload)

        assert response.status_code == status.HTTP_200_OK


    def test_login_invalid_password(self, client, create_test_db):
        # Create and add a user.
        user = UserInternalModel(
            email = "someUsername@somedomain.com",
            hashed_password = hash_password("MyPassword@123"),
            display_name = "Some User"
        )
        create_test_db.add(user)
        create_test_db.commit()

        # Try to log in with the same email but the wrong password.
        payload = {
            "email": "someUsername@somedomain.com",
            "password": "WrongPassword@123"
        }

        response = client.post(AUTH_LOGIN_PREFIX, json = payload)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid email or password" in response.json()["detail"]


    def test_login_unknown_email(self, client):
        # Try to log in with an account that doesn't exist in the database.
        payload = {
            "email": "someUsername@somedomain.com",
            "password": "MyPassword@123"
        }

        response = client.post(AUTH_LOGIN_PREFIX, json = payload)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------

class TestAuthLogout:

    def test_logout_deletes_cookie(self, client):
        response = client.post(AUTH_LOGOUT_PREFIX)

        # The logout endpoint should send a Set-Cookie header that deletes the cookie.
        set_cookie_header = response.headers.get("set-cookie")

        assert set_cookie_header is not None
        assert "refresh_token=" in set_cookie_header
        assert "Max-Age=0" in set_cookie_header or "expires=" in set_cookie_header

        assert response.json()["message"] == "Logged out"


# ---------------------------------------------------------
# REFRESH
# ---------------------------------------------------------

class TestAuthRefresh:

    def test_refresh_issues_new_access_token(
        self, 
        client, 
        test_user, 
        refresh_token_for_test_user
    ):
        response = client.post(
            AUTH_REFRESH_PREFIX,
            cookies = {"refresh_token": refresh_token_for_test_user}
        )

        assert response.status_code == status.HTTP_200_OK

        set_cookie_header = response.headers.get("set-cookie")
        assert "access_token=" in set_cookie_header



    def test_refresh_rotates_refresh_token(
        self, 
        client,
        test_user,
        refresh_token_for_test_user
    ):
        response = client.post(
            AUTH_REFRESH_PREFIX,
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


# ---------------------------------------------------------
# REFRESH
# ---------------------------------------------------------

class TestAuthMe:

    def test_me_returns_user_details(
        self, 
        client, 
        test_user, 
        access_token_for_test_user
    ):
        response = client.get(
            AUTH_ME_PREFIX,
            cookies = {"access_token": access_token_for_test_user}
        )

        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["id"] == str(test_user.id)
        assert data["email"] == test_user.email
        assert data["created_at"] != ""
