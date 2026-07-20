from starlette import status
from datetime import datetime, timezone, timedelta
import jwt
import uuid

from src.db.models.user_models import UserInternalModel
from src.utils.auth.password_utils import verify_password, hash_password
from src.utils.auth.email_verification_utils import (
    create_verification_token
)
from src.constants.route_constants import (
    AUTH_SIGNUP_PREFIX,
    AUTH_LOGIN_PREFIX,
    AUTH_SEND_VERIFICATION_PREFIX,
    AUTH_VERIFY_EMAIL_PREFIX,
    AUTH_LOGOUT_PREFIX,
    AUTH_REFRESH_PREFIX,
    AUTH_ME_PREFIX
)
from src.db.models.verification_token_model import VerificationToken
from src.constants.token_constants import EMAIL_VERIFICATION
from src.constants.jwt_constants import JWT_SECRET_KEY, JWT_ALGORITHM
from tests.utils.test_utils import fake_create_token_factory

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

        # Verify user exists in DB.
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

    def test_signup_creates_verification_token(self, client, create_test_db):
        payload = {
            "email": "someUser@gmail.com",
            "password": "MyPassword@123",
            "display_name": "Some User"
        }

        response = client.post(AUTH_SIGNUP_PREFIX, json = payload)
        assert response.status_code == status.HTTP_201_CREATED

        # Check DB for email verification token.
        token = create_test_db.query(VerificationToken).filter_by(
            user_id = uuid.UUID(response.json()["id"]),
            purpose = EMAIL_VERIFICATION
        ).first()

        assert token is not None
        assert token.used is False
        assert token.expires_at.replace(tzinfo = timezone.utc) > datetime.now(timezone.utc)

# ---------------------------------------------------------
# SEND VERIFICATION
# ---------------------------------------------------------

class TestAuthSendVerification:

    def test_send_verification_resend_creates_new_token(self, client, create_test_db):
        # Sign up a user.
        payload = {
            "email": "someUser@gmail.com",
            "password": "MyPassword@123",
            "display_name": "Some User"
        }

        signup_response = client.post(AUTH_SIGNUP_PREFIX, json = payload)
        user_id = uuid.UUID(signup_response.json()["id"])

        # Sign in to authenticate the user.
        login_payload = {
            "email": payload["email"],
            "password": payload["password"]
        }

        login_response = client.post(AUTH_LOGIN_PREFIX, json = login_payload)
        assert login_response.status_code == status.HTTP_200_OK

        # Get email verification token.
        email_verification_token = create_test_db.query(VerificationToken).filter_by(
            user_id = user_id,
            purpose = EMAIL_VERIFICATION
        ).first()
        assert email_verification_token is not None
        email_verification_token_hash = email_verification_token.token_hash

        # Resend a verification link so we can see if we get a different token back from
        # the database. The first verification link should have been sent when we signed up
        # initially.
        send_verification_response = client.post(AUTH_SEND_VERIFICATION_PREFIX)
        assert send_verification_response.status_code == status.HTTP_200_OK

        # We should have started with one token and should now have two.
        tokens = create_test_db.query(VerificationToken).filter_by(
            user_id = user_id,
            purpose = EMAIL_VERIFICATION
        ).all()

        # There should be just one token because send_verificaiton deletes any previous tokens
        # for a given user.
        assert len(tokens) == 1

        # Ensure the new token is different from the first one.
        assert tokens[0].token_hash != email_verification_token_hash


# ---------------------------------------------------------
# VERIFY EMAIL
# ---------------------------------------------------------

class TestVerifyEmail:

    def test_verify_email_success(self, client, create_test_db, monkeypatch):
        # monkeypatch token creation so signup uses a known raw token. The real 
        # function generates random tokens and stores only hashes, making them 
        # impossible to retrieve in tests. We need the raw verification token
        # string for the test and shouldn't have signup return it.
        monkeypatch.setattr(
            "src.api.routers.auth_router.create_verification_token",
            fake_create_token_factory("success_token")
        )

        # Sign up.
        payload = {
            "email": "someUser@gmail.com",
            "password": "MyPassword@123",
            "display_name": "Some User"
        }

        signup_response = client.post(AUTH_SIGNUP_PREFIX, json = payload)
        user_id = uuid.UUID(signup_response.json()["id"])

        raw_token = "success_token"

        # Send a verification email.
        response = client.post(f"{AUTH_VERIFY_EMAIL_PREFIX}?token={raw_token}")
        assert response.status_code == status.HTTP_200_OK

       # Check to see that the verification token is used.
        verification_token = create_test_db.query(VerificationToken).filter_by(
            user_id = user_id
        ).first()
        assert verification_token.used is True

        # Check to see that the user is verified and the verification is time stamped.
        user = create_test_db.query(UserInternalModel).filter_by(id = user_id).first()
        assert user.is_verified is True
        assert user.verified_at is not None


    def test_verify_email_expired(self, client, create_test_db, monkeypatch):
        # monkeypatch token creation so signup uses a known raw token. The real 
        # function generates random tokens and stores only hashes, making them 
        # impossible to retrieve in tests. We need the raw verification token
        # string for the test and shouldn't have signup return it.
        monkeypatch.setattr(
            "src.api.routers.auth_router.create_verification_token",
            fake_create_token_factory("expired_token")
        )

        # Sign up.
        payload = {
            "email": "someUser@gmail.com",
            "password": "MyPassword@123",
            "display_name": "Some User"
        }

        signup_response = client.post(AUTH_SIGNUP_PREFIX, json = payload)
        user_id = uuid.UUID(signup_response.json()["id"])

        raw_token = "expired_token"

        # Get the token created by signup and change the expiration timestamp.
        verification_token = create_test_db.query(VerificationToken).filter_by(
            user_id = user_id
        ).first()
        verification_token.expires_at = datetime.now(timezone.utc) - timedelta(hours = 1)
        create_test_db.commit()

        # If we try sending an email verification link, it should fail (since we forced 
        # the token to be expired).
        response = client.post(f"{AUTH_VERIFY_EMAIL_PREFIX}?token={raw_token}")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "expired" in response.json()["detail"]


    def test_verify_email_used_token(self, client, create_test_db, monkeypatch):
        # monkeypatch token creation so signup uses a known raw token. The real 
        # function generates random tokens and stores only hashes, making them 
        # impossible to retrieve in tests. We need the raw verification token
        # string for the test and shouldn't have signup return it.
        monkeypatch.setattr(
            "src.api.routers.auth_router.create_verification_token",
            fake_create_token_factory("used_token")
        )

        # Sign up.
        payload = {
            "email": "someUser@gmail.com",
            "password": "MyPassword@123",
            "display_name": "Some User"
        }

        signup_response = client.post(AUTH_SIGNUP_PREFIX, json = payload)
        user_id = uuid.UUID(signup_response.json()["id"])

        raw_token = "used_token"

        # Mark the verification token as used.
        verification_token = create_test_db.query(VerificationToken).filter_by(
            user_id = user_id
        ).first()
        verification_token.used = True
        create_test_db.commit()

        # If we try sending an email verification link, it should fail (since we marked 
        # the token as used).
        response = client.post(f"{AUTH_VERIFY_EMAIL_PREFIX}?token={raw_token}")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already been used" in response.json()["detail"]


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


    def test_login_includes_email_verified_false(self, client, create_test_db):
        # Create and add a new unverified user.
        user = UserInternalModel(
            email = "someUsername@somedomain.com",
            hashed_password = hash_password("MyPassword@123"),
            display_name = "Mike Smith",
            is_verified = False
        )
        create_test_db.add(user)
        create_test_db.commit()

        payload = {
            "email": "someUsername@somedomain.com",
            "password": "MyPassword@123",
        }

        # Log the user in.
        response = client.post(AUTH_LOGIN_PREFIX, json = payload)
        assert response.status_code == status.HTTP_200_OK

        # Make sure the email_verified field in the decoded access token is false.
        access_token = response.json()["access_token"]
        decoded_token = jwt.decode(access_token, JWT_SECRET_KEY, algorithms = [JWT_ALGORITHM])

        assert decoded_token["email_verified"] is False


    def test_login_includes_email_verified_true(self, client, create_test_db):
        # Create and add a new verified user.
        user = UserInternalModel(
            email = "someUsername@somedomain.com",
            hashed_password = hash_password("MyPassword@123"),
            display_name = "Mike Smith",
            is_verified = True
        )
        create_test_db.add(user)
        create_test_db.commit()

        payload = {
            "email": "someUsername@somedomain.com",
            "password": "MyPassword@123",
        }

        # Log the user in.
        response = client.post(AUTH_LOGIN_PREFIX, json = payload)
        assert response.status_code == status.HTTP_200_OK

        # Make sure the email_verified field in the decoded access token is true.
        access_token = response.json()["access_token"]
        decoded_token = jwt.decode(access_token, JWT_SECRET_KEY, algorithms = [JWT_ALGORITHM])

        assert decoded_token["email_verified"] is True


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
