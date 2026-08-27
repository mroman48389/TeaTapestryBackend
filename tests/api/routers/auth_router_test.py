from starlette import status
from datetime import datetime, timezone, timedelta
import uuid
import hashlib
import gzip
import json

from src.db.models.auth.user_models import UserInternalModel
from src.db.models.auth.session_token_model import SessionTokenModel
from src.utils.auth.password_utils import verify_password, hash_password
from src.constants.route_constants import (
    AUTH_SIGNUP_PREFIX,
    AUTH_LOGIN_PREFIX,
    AUTH_SEND_VERIFICATION_PREFIX,
    AUTH_VERIFY_EMAIL_PREFIX,
    AUTH_REQUEST_PASSWORD_RESET_PREFIX,
    AUTH_RESET_PASSWORD_PREFIX,
    AUTH_LOGOUT_PREFIX,
    AUTH_LOGOUT_ALL_PREFIX,
    AUTH_ACTIVE_SESSIONS_PREFIX,
    AUTH_TERMINATE_SESSION_PREFIX,
    AUTH_REFRESH_PREFIX,
    AUTH_ME_PREFIX,
    AUTH_EXPORT_USER_DATA_PREFIX,
    AUTH_DELETE_USER_DATA_PREFIX,
    AUTH_DELETE_USER_ACCOUNT_PREFIX,
)
from src.constants.dsar_constants import (
    REQUEST_DELETE_USER_ACCOUNT,
    REQUEST_DELETE_USER_DATA,
    REQUEST_EXPORT_USER_DATA,
    STATUS_FULFILLED,
    STATUS_FAILED
)
from src.db.models.auth.verification_token_model import VerificationTokenModel
from src.db.models.auth.dsar_log_model import DSARLogModel
from src.app.services.user_data_export_services import UserDataExportService
from src.app.services.user_data_deletion_services import (
    UserDataDeletionService, 
    UserAccountDeletionService
)
from src.constants.token_constants import (
    EMAIL_VERIFICATION,
    PASSWORD_RESET,
)
from src.utils.auth.jwt_utils import (
    create_access_token,
    decode_access_token
)
from tests.utils.test_utils import (
    fake_create_token_factory
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
        token = create_test_db.query(VerificationTokenModel).filter_by(
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
        email_verification_token = create_test_db.query(VerificationTokenModel).filter_by(
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
        tokens = create_test_db.query(VerificationTokenModel).filter_by(
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

class TestAuthVerifyEmail:

    def test_verify_email_success(self, client, create_test_db, monkeypatch):
        # monkeypatch token creation so signup uses a known raw token. The real 
        # function generates random tokens and stores only hashes, making them 
        # impossible to retrieve in tests. We need the raw verification token
        # string for the test and shouldn't have signup return it.
        monkeypatch.setattr(
            "src.api.routers.auth_router.create_raw_verification_token",
            fake_create_token_factory(EMAIL_VERIFICATION, "success_token")
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
        verification_token = create_test_db.query(VerificationTokenModel).filter_by(
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
            "src.api.routers.auth_router.create_raw_verification_token",
            fake_create_token_factory(EMAIL_VERIFICATION, "expired_token")
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
        verification_token = create_test_db.query(VerificationTokenModel).filter_by(
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
            "src.api.routers.auth_router.create_raw_verification_token",
            fake_create_token_factory(EMAIL_VERIFICATION, "used_token")
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
        verification_token = create_test_db.query(VerificationTokenModel).filter_by(
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
# REQUEST PASSWORD RESET
# ---------------------------------------------------------

class TestAuthRequestPasswordReset:

    def test_request_password_reset_success(self, client, create_test_db, monkeypatch):

        # Create a user manually (no signup needed) and add them to the database.
        user = UserInternalModel(
            email = "someUsername@somedomain.com",
            hashed_password = hash_password("MyPassword@123"),
            display_name = "Some User"
        )
        create_test_db.add(user)
        create_test_db.commit()

        # Monkeypatch token creation so we know the raw token.
        monkeypatch.setattr(
            "src.api.routers.auth_router.create_raw_verification_token",
            fake_create_token_factory(PASSWORD_RESET, "reset_token")
        )

        payload = {"email": "someUsername@somedomain.com"}

        response = client.post(AUTH_REQUEST_PASSWORD_RESET_PREFIX, json = payload)

        # Recall that we should always get back OK as a security measure.
        assert response.status_code == status.HTTP_200_OK
        assert "reset link" in response.json()["message"]

        # A password reset verification token should exist.
        verification_token = create_test_db.query(VerificationTokenModel).filter_by(
            user_id = user.id,
            purpose = PASSWORD_RESET
        ).first()
        assert verification_token is not None
        assert verification_token.used is False


    def test_request_password_reset_nonexistent_email(self, client, create_test_db):

        # We could create a user and use a nonexistent email to be perfectly explicit,
        # but it's not necessary.
        payload = {"email": "someUsername@somedomain.com"}

        response = client.post(AUTH_REQUEST_PASSWORD_RESET_PREFIX, json = payload)

        # Recall that we should always get back OK as a security measure.
        assert response.status_code == status.HTTP_200_OK
        assert "reset link" in response.json()["message"]

        # No token should have been created.
        tokens = create_test_db.query(VerificationTokenModel).all()
        assert len(tokens) == 0


    def test_request_password_reset_deletes_old_tokens(self, client, create_test_db, monkeypatch):

        # Create a user manually (no signup needed) and add them to the database.
        user = UserInternalModel(
            email = "someUsername@somedomain.com",
            hashed_password = hash_password("MyPassword@123"),
            display_name = "Some User"
        )
        create_test_db.add(user)
        create_test_db.commit()

        # Create an old token and add it to the database.
        old_token = VerificationTokenModel(
            user_id = user.id,
            token_hash = "old_hash",
            purpose = PASSWORD_RESET,
            expires_at = datetime.now(timezone.utc) + timedelta(hours = 1),
            used = False
        )
        create_test_db.add(old_token)
        create_test_db.commit()

        # Monkeypatch new token creation.
        monkeypatch.setattr(
            "src.api.routers.auth_router.create_raw_verification_token",
            fake_create_token_factory(PASSWORD_RESET, "new_token")
        )

        payload = {"email": "someUsername@somedomain.com"}

        # Recall that we should always get back OK as a security measure.
        response = client.post(AUTH_REQUEST_PASSWORD_RESET_PREFIX, json = payload)
        assert response.status_code == status.HTTP_200_OK

        # The old token should be have been deleted, and there should be only 
        # the new one in the database.

        tokens = create_test_db.query(VerificationTokenModel).filter_by(
            user_id = user.id,
            purpose = PASSWORD_RESET
        ).all()
        assert len(tokens) == 1
        assert tokens[0].token_hash == hashlib.sha256("new_token".encode()).hexdigest()


# ---------------------------------------------------------
# RESET PASSWORD
# ---------------------------------------------------------

class TestAuthResetPassword:

    def test_reset_password_success(self, client, create_test_db, monkeypatch):

        # Create a user manually (no signup needed) and add them to the database.
        user = UserInternalModel(
            email = "someUsername@somedomain.com",
            hashed_password = hash_password("OldPassword@123"),
            display_name = "Some User"
        )
        create_test_db.add(user)
        create_test_db.commit()

        # Monkeypatch token creation.
        monkeypatch.setattr(
            "src.api.routers.auth_router.create_raw_verification_token",
            fake_create_token_factory(PASSWORD_RESET, "reset_token")
        )

        # Create token manually (simulate a succesful request_password_reset call).
        raw_token = "reset_token"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        verification_token = VerificationTokenModel(
            user_id = user.id,
            token_hash = token_hash,
            purpose = PASSWORD_RESET,
            expires_at = datetime.now(timezone.utc) + timedelta(hours = 1),
            used = False
        )
        create_test_db.add(verification_token)
        create_test_db.commit()

        payload = {
            "token": raw_token,
            "new_password": "NewPassword@123"
        }

        # Recall that we should always get back OK as a security measure.
        response = client.post(AUTH_RESET_PASSWORD_PREFIX, json = payload)
        assert response.status_code == status.HTTP_200_OK

        # Token should be marked used.
        updated_token = create_test_db.query(VerificationTokenModel).filter_by(
            user_id = user.id
        ).first()
        assert updated_token.used is True

        # Password should be updated
        updated_user = create_test_db.query(UserInternalModel).filter_by(id = user.id).first()
        assert verify_password("NewPassword@123", updated_user.hashed_password)


    def test_reset_password_invalid_token(self, client, create_test_db):
        # We could create a user to be perfectly explicit, but it's not necessary for this test.
        payload = {
            "token": "invalid",
            "new_password": "NewPassword@123"
        }

        response = client.post(AUTH_RESET_PASSWORD_PREFIX, json = payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "unknown" in response.json()["detail"]


    def test_reset_password_expired_token(self, client, create_test_db):

        # Create a user manually (no signup needed) and add them to the database.
        user = UserInternalModel(
            email = "someUsername@somedomain.com",
            hashed_password = hash_password("OldPassword@123"),
            display_name = "Some User"
        )
        create_test_db.add(user)
        create_test_db.commit()

        # Create and add an expired token to the database.
        raw_token = "expired_token"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        verification_token = VerificationTokenModel(
            user_id = user.id,
            token_hash = token_hash,
            purpose = PASSWORD_RESET,
            expires_at = datetime.now(timezone.utc) - timedelta(hours = 1),
            used = False
        )
        create_test_db.add(verification_token)
        create_test_db.commit()

        payload = {
            "token": raw_token,
            "new_password": "NewPassword@123"
        }

        response = client.post(AUTH_RESET_PASSWORD_PREFIX, json = payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "expired" in response.json()["detail"]


    def test_reset_password_used_token(self, client, create_test_db):

        # Create a user manually (no signup needed) and add them to the database.
        user = UserInternalModel(
            email = "someUsername@somedomain.com",
            hashed_password = hash_password("OldPassword@123"),
            display_name = "Some User"
        )
        create_test_db.add(user)
        create_test_db.commit()

        # Create and add a used token to the database.
        raw_token = "used_token"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        token = VerificationTokenModel(
            user_id = user.id,
            token_hash = token_hash,
            purpose = PASSWORD_RESET,
            expires_at = datetime.now(timezone.utc) + timedelta(hours = 1),
            used = True
        )
        create_test_db.add(token)
        create_test_db.commit()

        payload = {
            "token": raw_token,
            "new_password": "NewPassword@123"
        }

        response = client.post(AUTH_RESET_PASSWORD_PREFIX, json = payload)
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
        payload = decode_access_token(access_token)

        assert payload.email_verified is False


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
        payload = decode_access_token(access_token)

        assert payload.email_verified is True


# ---------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------

class TestAuthLogout:

    def test_logout_revokes_session(
        self,
        client,
        test_user,
        refresh_token_bundle_for_test_user,
        create_test_db
    ):
        raw_refresh_token = refresh_token_bundle_for_test_user["raw"]
        hashed_refresh_token = refresh_token_bundle_for_test_user["hashed"]

        client.cookies.set("refresh_token", raw_refresh_token)
        response = client.post(AUTH_LOGOUT_PREFIX)

        assert response.status_code == status.HTTP_200_OK

        # Make sure the session row is revoked.
        session_token = create_test_db.query(SessionTokenModel).filter(
            SessionTokenModel.refresh_token_hash == hashed_refresh_token
        ).first()

        assert session_token is not None
        assert session_token.revoked_at is not None


    def test_logout_deletes_cookie(self, client):
        response = client.post(AUTH_LOGOUT_PREFIX)

        # The logout endpoint should send a Set-Cookie header that deletes the cookie.
        set_cookie_header = response.headers.get("set-cookie")

        assert set_cookie_header is not None
        assert "refresh_token=" in set_cookie_header
        assert ("Max-Age=0" in set_cookie_header) or ("expires=" in set_cookie_header)

        assert response.json()["message"] == "Logged out"


# ---------------------------------------------------------
# LOGOUT ALL
# ---------------------------------------------------------

class TestAuthLogoutAll:

    def test_logout_all_without_cookie_succeeds_and_deletes_cookies(
        self,
        client,
        test_user,
        create_test_db
    ):
        # Purposefully don't set a refresh token cookie so we can ensure
        # the endpoint still succeeds and deletes auth cookies.
        response = client.post(AUTH_LOGOUT_ALL_PREFIX)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Logged out of all devices."

        set_cookie_headers = response.headers.get_list("set-cookie")

        # The response should delete both cookies and make them expired.

        assert any("refresh_token=" in h for h in set_cookie_headers)
        assert any("access_token=" in h for h in set_cookie_headers)
        assert any("Max-Age=0" in h or "expires=" in h for h in set_cookie_headers)


    def test_logout_all_with_invalid_refresh_token_deletes_cookies(
        self,
        client,
        test_user,
        create_test_db
    ):
        # Set a refresh token cookie that does NOT correspond to any session.
        client.cookies.set("refresh_token", "fake token")

        response = client.post(AUTH_LOGOUT_ALL_PREFIX)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Logged out of all devices."

        # The response should delete both cookies.
        set_cookie_headers = response.headers.get_list("set-cookie")

        assert any("refresh_token=" in h for h in set_cookie_headers)
        assert any("access_token=" in h for h in set_cookie_headers)
        assert any("Max-Age=0" in h or "expires=" in h for h in set_cookie_headers)

        # No sessions should be revoked.
        user_sessions = create_test_db.query(SessionTokenModel).filter(
            SessionTokenModel.user_id == test_user.id
        ).all()

        # All sessions should still be unrevoked.
        for s in user_sessions:
            assert s.revoked_at is None


    def test_logout_all_revokes_all_sessions_for_user(
        self,
        client,
        test_user,
        refresh_token_bundle_for_test_user,
        create_test_db
    ):
        # This time, we set a refresh cookie so the endpoint can identify 
        # the user and revoke all their sessions.
        raw_refresh_token = refresh_token_bundle_for_test_user["raw"]
        client.cookies.set("refresh_token", raw_refresh_token)

        response = client.post(AUTH_LOGOUT_ALL_PREFIX)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Logged out of all devices."

        # All sessions for this user should now be revoked.
        user_sessions = create_test_db.query(SessionTokenModel).filter(
            SessionTokenModel.user_id == test_user.id
        ).all()

        assert len(user_sessions) > 0
        for s in user_sessions:
            assert s.revoked_at is not None


# ---------------------------------------------------------
# ACTIVE SESSIONS
# ---------------------------------------------------------

class TestAuthActiveSessions:

    def test_active_sessions_returns_all_sessions_sorted(
        self,
        client,
        test_user,
        refresh_token_bundle_for_test_user,
        create_test_db
    ):
        # The user already has one session from the fixture. Create a second one
        # manually to make sure sorting works.
        now = datetime.now(timezone.utc)
        later = now + timedelta(minutes = 5)

        second_session = SessionTokenModel(
            user_id = test_user.id,
            refresh_token_hash = "fake_refresh_token_hash",
            refresh_token_id = uuid.uuid4(),
            created_at = later,
            expires_at = later + timedelta(days = 30),
            user_agent = "pytest-agent",
            ip_address = "127.0.0.1"
        )
        create_test_db.add(second_session)
        create_test_db.commit()

        # Authenticate the user by setting the access token cookie.
        # get_current_user will read the access token from the cookie and
        # use it to identify the user. The get_active_sessions endpoint
        # uses get_current_user as a dependency. The flow:
        #
        #   1. get_active_sessions called
        #   2. Dependencies are resolved (get_session and get_current_user, in this case).
        #      This will give us a database connection and a user. The latter requires
        #      that we have already set an access token (otherwise, it will return an 
        #      exception). Doing this authenticates the user.
        #   3. get_active_sessions executes.
        client.cookies.set("access_token", create_access_token(str(test_user.id), True))
        response = client.get(AUTH_ACTIVE_SESSIONS_PREFIX)

        assert response.status_code == status.HTTP_200_OK

        sessions = response.json()["sessions"]
        assert len(sessions) == 2

        # Sessions should be sorted by created_at descending.
        assert sessions[0]["created_at"] >= sessions[1]["created_at"]


    def test_active_sessions_fails_if_no_access_token(
        self,
        client
    ):
        response = client.get(AUTH_ACTIVE_SESSIONS_PREFIX)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------
# TERMINATE SESSION
# ---------------------------------------------------------

class TestAuthTerminateSession:

    def test_terminate_session_successfully_revokes_session(
        self,
        client,
        test_user,
        refresh_token_bundle_for_test_user,
        create_test_db
    ):
        # Authenticate the user.
        client.cookies.set("access_token", create_access_token(str(test_user.id), True))

        # Get the test user's existing session (which we get from a fixture).
        session_token = create_test_db.query(SessionTokenModel).filter(
            SessionTokenModel.user_id == test_user.id
        ).first()

        response = client.post(f"{AUTH_TERMINATE_SESSION_PREFIX}/{session_token.id}")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Session terminated successfully."

        # The session should now be revoked.
        updated = create_test_db.query(SessionTokenModel).filter(
            SessionTokenModel.id == session_token.id
        ).first()

        assert updated.revoked_at is not None


    def test_terminate_session_already_revoked(
        self,
        client,
        test_user,
        refresh_token_bundle_for_test_user,
        create_test_db
    ):
        # Authenticate the user.
        client.cookies.set("access_token", create_access_token(str(test_user.id), True))

        # Revoke the session manually.
        session_token = create_test_db.query(SessionTokenModel).filter(
            SessionTokenModel.user_id == test_user.id
        ).first()
        session_token.revoked_at = datetime.now(timezone.utc)
        create_test_db.commit()

        response = client.post(f"{AUTH_TERMINATE_SESSION_PREFIX}/{session_token.id}")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Session already terminated."


    def test_terminate_session_not_found(
        self,
        client,
        test_user,
        refresh_token_bundle_for_test_user
    ):
        # Authenticate the user.
        client.cookies.set("access_token", create_access_token(str(test_user.id), True))

        # Use a random UUID that does not exist in the database.
        random_id = uuid.uuid4()

        response = client.post(f"{AUTH_TERMINATE_SESSION_PREFIX}/{random_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Session not found."


# ---------------------------------------------------------
# REFRESH
# ---------------------------------------------------------

class TestAuthRefresh:

    def test_refresh_issues_new_access_token(
        self, 
        client, 
        test_user, 
        refresh_token_bundle_for_test_user
    ):
        client.cookies.set("refresh_token", refresh_token_bundle_for_test_user["raw"])
        response = client.post(AUTH_REFRESH_PREFIX)

        assert response.status_code == status.HTTP_200_OK

        set_cookie_header = response.headers.get("set-cookie")
        assert "access_token=" in set_cookie_header


    def test_refresh_rotates_refresh_token(
        self, 
        client,
        test_user,
        refresh_token_bundle_for_test_user
    ):
        old_raw_refresh_token = refresh_token_bundle_for_test_user["raw"]

        client.cookies.set("refresh_token", old_raw_refresh_token)
        response = client.post(AUTH_REFRESH_PREFIX)

        assert response.status_code == status.HTTP_200_OK

        # The refresh endpoint should set a new refresh token cookie.
        set_cookie_header = response.headers.get("set-cookie")

        # Parse out the new token
        new_refresh_token = set_cookie_header.split("refresh_token=")[1].split(";")[0]

        assert set_cookie_header is not None
        assert "refresh_token=" in set_cookie_header
        # Ensure the new token is different from the old one.
        assert new_refresh_token != old_raw_refresh_token

    def test_refresh_detects_token_reuse(
        self,
        client,
        test_user,
        refresh_token_bundle_for_test_user,
        create_test_db
    ):
        # As a reminder, token reuse just means that a different refresh token than the one 
        # original associated with the session is being used. 
        # 
        
        # First, we call the refresh endpoint with our original test token in order to rotate it.
        original_raw_refresh_token = refresh_token_bundle_for_test_user["raw"]

        client.cookies.set("refresh_token", original_raw_refresh_token)
        first_response = client.post(AUTH_REFRESH_PREFIX)

        assert first_response.status_code == status.HTTP_200_OK

        # Extract the new refresh token from Set-Cookie. It should be different than the original
        # if the refresh endpoint rotated it properly.
        set_cookie_headers = first_response.headers.get_list("set-cookie")
        new_refresh_cookie = next(h for h in set_cookie_headers if "refresh_token=" in h)
        new_raw_refresh_token = new_refresh_cookie.split("refresh_token=")[1].split(";")[0]

        assert new_raw_refresh_token != original_raw_refresh_token

        # Call the refresh endpoint again using the same original refresh token to trigger 
        # reuse detection. We need to clear the cookies first so starlette doesn't merge them or
        # leave behind anything from the first send.
        client.cookies.clear()
        client.cookies.set("refresh_token", original_raw_refresh_token)
        second_response = client.post(AUTH_REFRESH_PREFIX)

        # The endpoint should revoke all sessions for our test user.
        assert second_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert second_response.json()["detail"] == (
            "Refresh token reuse detected. All sessions revoked."
        )

        user_sessions = create_test_db.query(SessionTokenModel).filter(
            SessionTokenModel.user_id == test_user.id
        ).all()

        assert len(user_sessions) > 0
        for s in user_sessions:
            assert s.revoked_at is not None

# ---------------------------------------------------------
# ME
# ---------------------------------------------------------

class TestAuthMe:

    def test_me_returns_user_details(
        self, 
        client, 
        test_user, 
        access_token_for_test_user
    ):
        client.cookies.set("access_token", access_token_for_test_user)
        response = client.get(AUTH_ME_PREFIX)

        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["id"] == str(test_user.id)
        assert data["email"] == test_user.email
        assert data["created_at"] != ""


# ---------------------------------------------------------
# EXPORT USER DATA
# ---------------------------------------------------------

class TestAuthExportUserData:

    def test_export_user_data_success(
        self,
        client,
        test_user,
        refresh_token_bundle_for_test_user,
        create_test_db
    ):
        # Simulate a fresh login by setting last_login to now. Recall that the
        # endpoint requires the user to have logged in within the last 5 minutes.
        test_user.last_login = datetime.now(timezone.utc)
        create_test_db.commit()

        # Authenticate the user.
        client.cookies.set("access_token", create_access_token(str(test_user.id), True))

        response = client.get(AUTH_EXPORT_USER_DATA_PREFIX)

        assert response.status_code == status.HTTP_200_OK

        # The response body should be gzip-compressed bytes.
        decompressed = gzip.decompress(response.content)
        data = json.loads(decompressed)

        # Verify that one of the expected fields is in the file. The user id should be
        # that of our test user.
        assert isinstance(data, dict)
        assert "user" in data  
        assert data["user"]["id"] == str(test_user.id)

        # Verify that a DSAR log was created and fulfilled.
        dsar_logs = create_test_db.query(DSARLogModel).filter_by(user_id = test_user.id).all()

        assert len(dsar_logs) == 1
        assert dsar_logs[0].request_type == REQUEST_EXPORT_USER_DATA
        assert dsar_logs[0].status == STATUS_FULFILLED
        assert dsar_logs[0].fulfilled_at is not None


    def test_export_user_data_fails_if_no_access_token(
        self,
        client,
        test_user,
        create_test_db
    ):
        response = client.get(AUTH_EXPORT_USER_DATA_PREFIX)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # No DSAR log should be created.
        dsar_logs = create_test_db.query(DSARLogModel).filter_by(user_id = test_user.id).all()
        assert dsar_logs == []


    def test_export_user_data_marks_dsar_failed_on_exception(
        self,
        client,
        test_user,
        refresh_token_bundle_for_test_user,
        create_test_db,
        monkeypatch
    ):
        test_user.last_login = datetime.now(timezone.utc)
        create_test_db.commit()

        client.cookies.set("access_token", create_access_token(str(test_user.id), True))

        # ⭐ NEW — force service to throw
        def export_user_data_exception(*args, **kwargs):
            raise Exception("Failed to export user data.")

        monkeypatch.setattr(
            UserDataExportService,
            "export_user_data",
            export_user_data_exception
        )

        response = client.get(AUTH_EXPORT_USER_DATA_PREFIX)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

        # Verify DSAR log marked FAILED.
        dsar_logs = create_test_db.query(DSARLogModel).filter_by(user_id = test_user.id).all()

        assert len(dsar_logs) == 1
        assert dsar_logs[0].status == STATUS_FAILED
        assert dsar_logs[0].notes == "Failed to export user data."
        assert dsar_logs[0].fulfilled_at is not None


    def test_export_user_data_requires_fresh_login(
        self,
        client,
        test_user,
        refresh_token_bundle_for_test_user,
        create_test_db
    ):
        # Set last_login far in the past.
        test_user.last_login = datetime.now(timezone.utc) - timedelta(days = 30)
        create_test_db.commit()

        # Authenticate user.
        client.cookies.set("access_token", create_access_token(str(test_user.id), True))

        response = client.get(AUTH_EXPORT_USER_DATA_PREFIX)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "log in again" in response.json()["detail"]


    def test_export_user_data_returns_valid_gzip(
        self,
        client,
        test_user,
        refresh_token_bundle_for_test_user,
        create_test_db
    ):

        test_user.last_login = datetime.now(timezone.utc)
        create_test_db.commit()

        client.cookies.set("access_token", create_access_token(str(test_user.id), True))

        response = client.get(AUTH_EXPORT_USER_DATA_PREFIX)

        assert response.status_code == status.HTTP_200_OK

        # Validate gzip header (first two bytes should be 0x1f, 0x8b)
        compressed = response.content
        assert compressed[:2] == b"\x1f\x8b"

        # We should be able to load the decompressed file without an error.
        decompressed = gzip.decompress(compressed)
        json.loads(decompressed)


# ---------------------------------------------------------
# DELETE USER DATA
# ---------------------------------------------------------

class TestAuthDeleteUserData:

    def test_delete_user_data_success(
        self,
        client,
        test_user,
        refresh_token_bundle_for_test_user,
        create_test_db,
        user_tea_profile_notes_repo,
        empty_user_tea_profile_notes_inbound,
    ):
        # Simulate a fresh login.
        test_user.last_login = datetime.now(timezone.utc)
        create_test_db.commit()

        # Create some user-generated data.
        user_tea_profile_notes_repo.create(
            user_id = test_user.id,
            tea_profile_id = 99,
            inbound_schema = empty_user_tea_profile_notes_inbound
        )

        # Authenticate the user.
        client.cookies.set("access_token", create_access_token(str(test_user.id), True))

        response = client.delete(AUTH_DELETE_USER_DATA_PREFIX)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify that user-generated data was deleted.
        user_tea_profile_notes = user_tea_profile_notes_repo.get_by_user_id(test_user.id)
        assert user_tea_profile_notes == []

        # Verify the user account still exists.
        user = create_test_db.get(UserInternalModel, test_user.id)
        assert user is not None

        # Verify that a DSAR log was created and fulfilled.
        dsar_logs = create_test_db.query(DSARLogModel).filter_by(user_id = test_user.id).all()

        assert len(dsar_logs) == 1
        assert dsar_logs[0].request_type == REQUEST_DELETE_USER_DATA
        assert dsar_logs[0].status == STATUS_FULFILLED
        assert dsar_logs[0].fulfilled_at is not None


    def test_delete_user_data_fails_if_no_access_token(
        self, 
        client,
        test_user,
        create_test_db
    ):
        response = client.delete(AUTH_DELETE_USER_DATA_PREFIX)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # No DSAR log should be created.
        dsar_logs = create_test_db.query(DSARLogModel).filter_by(user_id = test_user.id).all()
        assert dsar_logs == []


    def test_delete_user_data_marks_dsar_failed_on_exception(
        self,
        client,
        test_user,
        refresh_token_bundle_for_test_user,
        create_test_db,
        user_tea_profile_notes_repo,
        empty_user_tea_profile_notes_inbound,
        monkeypatch
    ):
        test_user.last_login = datetime.now(timezone.utc)
        create_test_db.commit()

        user_tea_profile_notes_repo.create(
            user_id = test_user.id,
            tea_profile_id = 99,
            inbound_schema = empty_user_tea_profile_notes_inbound
        )

        client.cookies.set("access_token", create_access_token(str(test_user.id), True))

        def delete_user_data_exception(*args, **kwargs):
            raise Exception("Failed to delete user data.")

        monkeypatch.setattr(
            UserDataDeletionService,
            "delete_user_data",
            delete_user_data_exception
        )

        response = client.delete(AUTH_DELETE_USER_DATA_PREFIX)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

        # Verify DSAR log marked FAILED.
        dsar_logs = create_test_db.query(DSARLogModel).filter_by(user_id = test_user.id).all()

        assert len(dsar_logs) == 1
        assert dsar_logs[0].status == STATUS_FAILED
        assert dsar_logs[0].notes == "Failed to delete user data."
        assert dsar_logs[0].fulfilled_at is not None

        # Verify that user-generated data was not deleted.
        user_tea_profile_notes = user_tea_profile_notes_repo.get_by_user_id(test_user.id)
        assert user_tea_profile_notes != []


# ---------------------------------------------------------
# DELETE USER ACCOUNT
# ---------------------------------------------------------

class TestAuthDeleteUserAccount:

    def test_delete_user_account_success(
        self,
        client,
        test_user,
        refresh_token_bundle_for_test_user,
        create_test_db,
        user_tea_profile_notes_repo,
        empty_user_tea_profile_notes_inbound,
    ):
        user_id = test_user.id

        # Simulate a fresh login.
        test_user.last_login = datetime.now(timezone.utc)
        create_test_db.commit()

        # Create some user-generated data.
        user_tea_profile_notes_repo.create(
            user_id = user_id,
            tea_profile_id = 99,
            inbound_schema = empty_user_tea_profile_notes_inbound
        )

        # Authenticate the user.
        client.cookies.set("access_token", create_access_token(str(user_id), True))

        response = client.delete(AUTH_DELETE_USER_ACCOUNT_PREFIX)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify user-generated data was deleted.
        user_tea_profile_notes = user_tea_profile_notes_repo.get_by_user_id(user_id)
        assert user_tea_profile_notes == []

        # Verify the user account was deleted.
        user = create_test_db.get(UserInternalModel, user_id)
        assert user is None

        # Verify that a DSAR log was created and fulfilled.
        dsar_logs = create_test_db.query(DSARLogModel).filter_by(user_id = user_id).all()

        assert len(dsar_logs) == 1
        assert dsar_logs[0].request_type == REQUEST_DELETE_USER_ACCOUNT
        assert dsar_logs[0].status == STATUS_FULFILLED
        assert dsar_logs[0].fulfilled_at is not None


    def test_delete_user_account_fails_if_no_access_token(
        self, 
        client,
        test_user,
        create_test_db
    ):
        response = client.delete(AUTH_DELETE_USER_ACCOUNT_PREFIX)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # No DSAR log should be created.
        dsar_logs = create_test_db.query(DSARLogModel).filter_by(user_id = test_user.id).all()
        assert dsar_logs == []


    def test_delete_user_account_marks_dsar_failed_on_exception(
        self,
        client,
        test_user,
        refresh_token_bundle_for_test_user,
        create_test_db,
        user_tea_profile_notes_repo,
        empty_user_tea_profile_notes_inbound,
        monkeypatch
    ):
        user_id = test_user.id

        test_user.last_login = datetime.now(timezone.utc)
        create_test_db.commit()
        user_tea_profile_notes_repo.create(
            user_id = user_id,
            tea_profile_id = 99,
            inbound_schema = empty_user_tea_profile_notes_inbound
        )

        client.cookies.set("access_token", create_access_token(str(user_id), True))

        def delete_user_account_exception(*args, **kwargs):
            raise Exception("Failed to delete user account.")

        monkeypatch.setattr(
            UserAccountDeletionService,
            "delete_user_account",
            delete_user_account_exception
        )

        response = client.delete(AUTH_DELETE_USER_ACCOUNT_PREFIX)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

        # Verify DSAR log marked FAILED.
        dsar_logs = create_test_db.query(DSARLogModel).filter_by(user_id = user_id).all()

        assert len(dsar_logs) == 1
        assert dsar_logs[0].status == STATUS_FAILED
        assert dsar_logs[0].notes == "Failed to delete user account."
        assert dsar_logs[0].fulfilled_at is not None

        # Verify that the user account was not deleted.
        user = create_test_db.get(UserInternalModel, user_id)
        assert user is not None

        # Verify that user-generated data was not deleted either.
        user_tea_profile_notes = user_tea_profile_notes_repo.get_by_user_id(user_id)
        assert user_tea_profile_notes != []
