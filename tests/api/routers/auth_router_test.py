from starlette import status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, Query
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
    AUTH_CONFIRM_PASSWORD_PREFIX,
)
from src.constants.dsar_constants import (
    DSAR_REQUEST_DELETE_USER_DATA,
    DSAR_REQUEST_EXPORT_USER_DATA,
    DSAR_STATUS_FULFILLED,
    DSAR_STATUS_FAILED
)
from src.constants.auth_constants import (
    CONCURRENT_REFRESH_GRACE_SECONDS
)
from src.db.models.auth.verification_token_model import VerificationTokenModel
from src.db.models.auth.dsar_log_model import DSARLogModel
from src.db.models.auth.password_confirmation_model import PasswordConfirmationModel
from src.app.services.user_data_export_services import UserDataExportService
from src.app.services.user_data_deletion_services import (
    UserDataDeletionService, 
    UserAccountDeletionService
)
from src.constants.token_constants import (
    EMAIL_VERIFICATION,
    PASSWORD_RESET,
)
from src.constants.jwt_constants import REFRESH_TOKEN_LIFETIME_DAYS
from src.constants.cookie_constants import SAME_SITE_VALUE
from src.utils.auth.jwt_utils import (
    create_access_token,
    decode_access_token
)
from tests.utils.test_utils import (
    fake_create_token_factory
)
from src.utils.auth.jwt_utils import create_refresh_token
from src.api.routers.auth_router import DUMMY_PASSWORD_HASH
from src.api.routers.auth_router import verify_password as original_verify_password

# ---------------------------------------------------------
# SIGNUP
# ---------------------------------------------------------

class TestAuthSignup:

    def test_signup_creates_user(self, client, create_test_db):
        signup_payload = {
            "email": "someUser@gmail.com",
            "password": "MyPassword@123",
            "display_name": "Some User"
        }

        signup_response = client.post(AUTH_SIGNUP_PREFIX, json = signup_payload)

        assert signup_response.status_code == status.HTTP_201_CREATED

        signup_data = signup_response.json()

        assert "id" in signup_data
        assert "created_at" in signup_data
        assert signup_data["email"] == signup_payload["email"]
        assert signup_data["display_name"] == signup_payload["display_name"]

        # Sensitive fields must not leak.
        assert "password" not in signup_data
        assert "hashed_password" not in signup_data

        # Make sure we have a user in the DB.
        user = create_test_db.query(UserInternalModel).filter_by(
            email = signup_payload["email"]
        ).first()

        assert user is not None

        # Password must be hashed, not stored in plaintext.
        assert user.hashed_password != signup_payload["password"]

        # Password must be verifiable with the hashing function.
        assert verify_password(signup_payload["password"], user.hashed_password)

        # Default verification state must be correct
        assert user.is_verified is False
        assert user.verified_at is None

        # Now we check the verfication token that was created.
        verification_token = create_test_db.query(VerificationTokenModel).filter_by(
            user_id = user.id
        ).first()

        assert verification_token is not None
        assert verification_token.user_id == user.id
        assert verification_token.token_hash is not None
        assert verification_token.purpose == EMAIL_VERIFICATION
        assert verification_token.used is False

        now = datetime.now(timezone.utc)
        expires_at = verification_token.expires_at.replace(tzinfo = timezone.utc)
        assert expires_at > now


    # Note that we need the create_test_db fixture even though we're not using it in 
    # the body of the test because the client fixture overrides FastAPI's get_session 
    # dependency. If we don't include it, the test database will not exist.
    def test_signup_duplicate_email_rejected(self, monkeypatch, client, create_test_db):
        signup_payload = {
            "email": "someUser@gmail.com",
            "password": "MyPassword@123",
            "display_name": "Some User"
        }

        # Sign up once.
        first_signup_response = client.post(AUTH_SIGNUP_PREFIX, json = signup_payload)
        assert first_signup_response.status_code == status.HTTP_201_CREATED

        # A second signup should fail.
        second_signup_response = client.post(AUTH_SIGNUP_PREFIX, json = signup_payload)

        assert second_signup_response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in second_signup_response.json()["detail"]


    def test_signup_integrity_error(self, monkeypatch, client, create_test_db):
        # Patch the commit method of the Session class so all session instances fail.
        def raise_integrity_error(*args, **kwargs):
            raise IntegrityError(
                "duplicate key", 
                params = None, 
                orig = Exception("duplicate key")
            )

        monkeypatch.setattr(Session, "commit", raise_integrity_error)

        signup_payload = {
            "email": "someUser@gmail.com",
            "password": "MyPassword@123",
            "display_name": "Some User"
        }

        signup_response = client.post(AUTH_SIGNUP_PREFIX, json = signup_payload)

        assert signup_response.status_code == status.HTTP_400_BAD_REQUEST
        assert signup_response.json()["detail"] == "A user with this email address already exists."

        # Ensure no user was created.
        user = create_test_db.query(UserInternalModel).filter_by(
            email = signup_payload["email"]
        ).first()
        assert user is None

        # Ensure no verification token was created
        verification_token = create_test_db.query(VerificationTokenModel).filter_by(
            purpose = EMAIL_VERIFICATION
        ).first()
        assert verification_token is None


    def test_signup_hashes_password(self, client, create_test_db):
        signup_payload = {
            "email": "someUser@gmail.com",
            "password": "MyPassword@123",
            "display_name": "Some User"
        }

        signup_response = client.post(AUTH_SIGNUP_PREFIX, json = signup_payload)

        assert signup_response.status_code == status.HTTP_201_CREATED

        user = create_test_db.query(UserInternalModel).filter_by(
            email = signup_payload["email"]
        ).first()

        # User must exist.
        assert user is not None

        # Password must not be stored in plaintext.
        assert user.hashed_password != signup_payload["password"]

        # Hash must be a bcrypt hash (starts with $2b$ or $2a$).
        assert user.hashed_password.startswith("$2"), "Password hash is not bcrypt"

        # Hash must validate correctly.
        assert verify_password(signup_payload["password"], user.hashed_password)

        # Hash must be stable across refresh.
        create_test_db.refresh(user)
        assert verify_password(signup_payload["password"], user.hashed_password)


    def test_signup_creates_verification_token(self, client, create_test_db):
        signup_payload = {
            "email": "someUser@gmail.com",
            "password": "MyPassword@123",
            "display_name": "Some User"
        }

        signup_response = client.post(AUTH_SIGNUP_PREFIX, json = signup_payload)
        assert signup_response.status_code == status.HTTP_201_CREATED

        user_id = uuid.UUID(signup_response.json()["id"])

        # Check DB for email verification token.
        verification_token = create_test_db.query(VerificationTokenModel).filter_by(
            user_id = uuid.UUID(signup_response.json()["id"]),
            purpose = EMAIL_VERIFICATION
        ).first()

        # Token must exist.
        assert verification_token is not None

        # Token must belong to the correct user
        assert verification_token.user_id == user_id

        # Token must be unused.
        assert verification_token.used is False

        # Token must expire in the future.
        now = datetime.now(timezone.utc)
        expires_at = verification_token.expires_at.replace(tzinfo = timezone.utc)
        assert expires_at > now

        # Token must have a reasonable expiration window (we use 30 minutes).
        delta = expires_at - now
        assert timedelta(minutes = 25) < delta < timedelta(hours = 35)

        # Token hash should be a SHA-256 hex digest, which is always exactly 64 characters.
        assert isinstance(verification_token.token_hash, str)
        assert len(verification_token.token_hash) == 64

        # Token must not be mutated after refresh.
        create_test_db.refresh(verification_token)
        assert verification_token.used is False

        now = datetime.now(timezone.utc)
        expires_at = verification_token.expires_at.replace(tzinfo = timezone.utc)
        assert expires_at > now


    def test_signup_raw_token_none(self, monkeypatch, client, create_test_db):
        # patch create_raw_verification_token where it is used. Force the raw_token to
        # have a value of None.
        monkeypatch.setattr(
            "src.api.routers.auth_router.create_raw_verification_token", 
            lambda *args, **kwargs: None
        )

        signup_payload = {
            "email": "someUser@gmail.com",
            "password": "MyPassword@123",
            "display_name": "Some User"
        }

        signup_response = client.post(AUTH_SIGNUP_PREFIX, json = signup_payload)

        assert signup_response.status_code == status.HTTP_201_CREATED
        signup_data = signup_response.json()

        assert signup_data["email"] == signup_payload["email"]

        # User must exist in the DB.
        user = create_test_db.query(UserInternalModel).filter_by(
            email = signup_payload["email"]
        ).first()
        assert user is not None

        # No verification token should be created.
        verification_token = create_test_db.query(VerificationTokenModel).filter_by(
            user_id = user.id,
            purpose = EMAIL_VERIFICATION
        ).first()
        assert verification_token is None


# ---------------------------------------------------------
# SEND VERIFICATION
# ---------------------------------------------------------

class TestAuthSendVerification:

    def test_send_verification_resend_creates_new_token(self, client, create_test_db):
        # Sign up a user.
        signup_payload = {
            "email": "someUser@gmail.com",
            "password": "MyPassword@123",
            "display_name": "Some User"
        }

        signup_response = client.post(AUTH_SIGNUP_PREFIX, json = signup_payload)
        assert signup_response.status_code == status.HTTP_201_CREATED

        user_id = uuid.UUID(signup_response.json()["id"])

        # Sign in to authenticate the user.
        login_payload = {
            "email": signup_payload["email"],
            "password": signup_payload["password"]
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

        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Resend a verification link so we can see if we get a different token back from
        # the database. The first verification link should have been sent when we signed up
        # initially.
        send_verification_response = client.post(AUTH_SEND_VERIFICATION_PREFIX, headers = headers)
        assert send_verification_response.status_code == status.HTTP_200_OK
        assert send_verification_response.json()["message"] == "Verification email sent."

        # We should have started with one token and should now have two.
        verification_tokens = create_test_db.query(VerificationTokenModel).filter_by(
            user_id = user_id,
            purpose = EMAIL_VERIFICATION
        ).all()

        # There should be just one token because send_verificaiton deletes any previous tokens
        # for a given user.
        assert len(verification_tokens) == 1

        new_token = verification_tokens[0]

        # New token must be different.
        assert new_token.token_hash != email_verification_token_hash

        # Token must belong to correct user
        assert new_token.user_id == user_id

        # Token must expire in the future 
        now = datetime.now(timezone.utc)
        expires_at = new_token.expires_at.replace(tzinfo = timezone.utc)
        assert expires_at > now


    def test_send_verification_raw_token_none(
        self, 
        monkeypatch, 
        client, 
        create_test_db
    ):
        # Sign up a user.
        signup_payload = {
            "email": "someUser@gmail.com",
            "password": "MyPassword@123",
            "display_name": "Some User"
        }

        signup_response = client.post(AUTH_SIGNUP_PREFIX, json = signup_payload)
        assert signup_response.status_code == status.HTTP_201_CREATED

        user_id = uuid.UUID(signup_response.json()["id"])

        # Verify a real token exists BEFORE monkeypatching
        original_token = create_test_db.query(VerificationTokenModel).filter_by(
            user_id = user_id,
            purpose = EMAIL_VERIFICATION
        ).first()
        assert original_token is not None

        # Log in to authenticate the user.
        login_payload = {
            "email": signup_payload["email"],
            "password": signup_payload["password"]
        }

        login_response = client.post(AUTH_LOGIN_PREFIX, json = login_payload)
        assert login_response.status_code == status.HTTP_200_OK

        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # patch create_raw_verification_token where it is used. Force the raw_token to
        # have a value of None.
        monkeypatch.setattr(
            "src.api.routers.auth_router.create_raw_verification_token", 
            lambda *args, **kwargs: None
        )

        # It should have failed to create the token but still returned a 200.
        send_verification_response = client.post(AUTH_SEND_VERIFICATION_PREFIX, headers = headers)

        assert send_verification_response.status_code == status.HTTP_200_OK
        assert send_verification_response.json()["message"] == "Failed to create token."

        # Ensure the old token was deleted
        remaining_tokens = create_test_db.query(VerificationTokenModel).filter_by(
            user_id = user_id,
            purpose = EMAIL_VERIFICATION
        ).all()
        assert remaining_tokens == []  


    def test_send_verification_requires_auth(self, client):
        send_verification_response = client.post(AUTH_SEND_VERIFICATION_PREFIX)

        assert send_verification_response.status_code == status.HTTP_401_UNAUTHORIZED


    def test_send_verification_user_already_verified(self, client, create_test_db):
        # Sign up a user.
        signup_payload = {
            "email": "someUser@gmail.com",
            "password": "MyPassword@123",
            "display_name": "Some User"
        }

        signup_response = client.post(AUTH_SIGNUP_PREFIX, json = signup_payload)
        assert signup_response.status_code == status.HTTP_201_CREATED

        user_id = uuid.UUID(signup_response.json()["id"])

        # Mark the user as verified.
        user = create_test_db.get(UserInternalModel, user_id)
        user.is_verified = True
        create_test_db.commit()

        login_payload = {
            "email": signup_payload["email"],
            "password": signup_payload["password"]
        }

        # Authenticate
        login_response = client.post(AUTH_LOGIN_PREFIX, json = login_payload)

        assert login_response.status_code == status.HTTP_200_OK

        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Attempt to resend verification should fail since the user is already
        # verified.
        send_verification_response = client.post(AUTH_SEND_VERIFICATION_PREFIX, headers = headers)

        assert send_verification_response.status_code == status.HTTP_400_BAD_REQUEST
        assert send_verification_response.json()["detail"] == "Email is already verified."


    def test_send_verification_token_deletion_failure(self, monkeypatch, client, create_test_db):
        # Create and authenticate user.
        signup_payload = {
            "email": "someUser@gmail.com",
            "password": "MyPassword@123",
            "display_name": "Some User"
        }

        signup_response = client.post(AUTH_SIGNUP_PREFIX, json = signup_payload)
        assert signup_response.status_code == status.HTTP_201_CREATED

        user_id = uuid.UUID(signup_response.json()["id"])

        login_payload = {
            "email": signup_payload["email"],
            "password": signup_payload["password"]
        }

        login_response = client.post(AUTH_LOGIN_PREFIX, json = login_payload)
        assert login_response.status_code == status.HTTP_200_OK

        # Patch commit to fail during deletion stage. Be sure to wait until after login, 
        # which also uses commit().
        def raise_exception(*args, **kwargs):
            raise Exception("delete failure")

        monkeypatch.setattr(Session, "commit", raise_exception)

        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Should hit the deletion commit failure path.
        send_verification_response = client.post(AUTH_SEND_VERIFICATION_PREFIX, headers = headers)

        assert send_verification_response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert send_verification_response.json()["detail"] == (
            "An unexpected error occurred while preparing the verification token."
        )

         # Original signup token should still be intact.
        remaining_tokens = create_test_db.query(VerificationTokenModel).filter_by(
            user_id = user_id,
            purpose = EMAIL_VERIFICATION
        ).all()
        assert len(remaining_tokens) == 1 


    def test_send_verification_token_commit_failure(self, monkeypatch, client, create_test_db):
        # Create and authenticate user.
        signup_payload = {
            "email": "someUser@gmail.com",
            "password": "MyPassword@123",
            "display_name": "Some User"
        }

        client.post(AUTH_SIGNUP_PREFIX, json = signup_payload)

        login_payload = {
            "email": signup_payload["email"],
            "password": signup_payload["password"]
        }

        login_response = client.post(AUTH_LOGIN_PREFIX, json = login_payload)

        assert login_response.status_code == status.HTTP_200_OK

        # Allow the deletion commit, fail only the second commit. We can simulate
        # this using a stateful monkeypatch for the commit. Be sure to wait after 
        # login, since it also uses commit().
        call_count = {"n": 0}

        def conditional_fail_commit(*args, **kwargs):
            call_count["n"] += 1

            if call_count["n"] == 2:  
                raise Exception("Token commit failure.")

        monkeypatch.setattr(Session, "commit", conditional_fail_commit)

        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Should hit the token commit failure path.
        send_verification_response = client.post(AUTH_SEND_VERIFICATION_PREFIX, headers = headers)

        assert send_verification_response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert send_verification_response.json()["detail"] == "Failed to create verification token."


    def test_send_verification_email_failure(self, monkeypatch, client, create_test_db):
        # Patch email sending to fail. You can't normally raise an error with a lambda
        # function, so use "(_ for _ in ())" to create an empty generator, which has a
        # .throw() method that raises an exception.
        monkeypatch.setattr(
            "src.api.routers.auth_router.send_verification_email",
            lambda *args, **kwargs: (_ for _ in ()).throw(Exception("email failure"))
        )

        # Create and authenticate user.
        signup_payload = {
            "email": "emailFail@gmail.com",
            "password": "MyPassword@123",
            "display_name": "User"
        }

        signup_response = client.post(AUTH_SIGNUP_PREFIX, json = signup_payload)
        assert signup_response.status_code == status.HTTP_201_CREATED

        user_id = uuid.UUID(signup_response.json()["id"])

        login_payload = {
            "email": signup_payload["email"],
            "password": signup_payload["password"]
        }

        login_response = client.post(AUTH_LOGIN_PREFIX, json = login_payload)
        assert login_response.status_code == status.HTTP_200_OK

        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Should still succeed.
        send_verification_response = client.post(AUTH_SEND_VERIFICATION_PREFIX, headers = headers)

        assert send_verification_response.status_code == status.HTTP_200_OK
        assert send_verification_response.json()["message"] == "Verification email sent."

        user = create_test_db.get(UserInternalModel, user_id)
        verification_token = create_test_db.query(VerificationTokenModel).filter_by(
            user_id = user.id,
            purpose = EMAIL_VERIFICATION
        ).first()

        assert verification_token is not None


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
        signup_payload = {
            "email": "someUser@gmail.com",
            "password": "MyPassword@123",
            "display_name": "Some User"
        }

        signup_response = client.post(AUTH_SIGNUP_PREFIX, json = signup_payload)
        assert signup_response.status_code == status.HTTP_201_CREATED

        user_id = uuid.UUID(signup_response.json()["id"])

        raw_token = "success_token"

        # Confirm that a verification token was created.
        expected_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        verification_token_original = create_test_db.query(VerificationTokenModel).filter_by(
            user_id = user_id,
            purpose = EMAIL_VERIFICATION
        ).first()

        assert verification_token_original is not None
        assert verification_token_original.token_hash == expected_hash
        assert verification_token_original.user_id == user_id

        # Send a verification email.
        verify_email_response = client.post(f"{AUTH_VERIFY_EMAIL_PREFIX}?token={raw_token}")
        assert verify_email_response.status_code == status.HTTP_200_OK
        assert verify_email_response.json()["message"] == "Email verified successfully."

        # Force SQLAlchemy to reload fresh state. Needed because two different SQLAlchemy
        # sessions mutate the same row and we don't want stale data.
        create_test_db.expire_all()

       # Check to see that the verification token is now marked as used.
        verification_token_modified = create_test_db.query(VerificationTokenModel).filter_by(
            user_id = user_id,
            purpose = EMAIL_VERIFICATION
        ).first()
        assert verification_token_modified.used is True

        # Check to see that the user is verified and the verification is time stamped.
        user = create_test_db.query(UserInternalModel).filter_by(id = user_id).first()
        assert user.is_verified is True
        assert user.verified_at is not None

        # The verification token should not be expired.
        now = datetime.now(timezone.utc)
        expires_at = verification_token_modified.expires_at.replace(tzinfo = timezone.utc)
        assert expires_at > now


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
        signup_payload = {
            "email": "someUser@gmail.com",
            "password": "MyPassword@123",
            "display_name": "Some User"
        }

        signup_response = client.post(AUTH_SIGNUP_PREFIX, json = signup_payload)
        assert signup_response.status_code == status.HTTP_201_CREATED

        user_id = uuid.UUID(signup_response.json()["id"])

        raw_token = "expired_token"

        # Confirm that a verification token was created. 
        expected_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        verification_token_original = create_test_db.query(VerificationTokenModel).filter_by(
            user_id = user_id,
            purpose = EMAIL_VERIFICATION
        ).first()

        assert verification_token_original is not None
        assert verification_token_original.token_hash == expected_hash
        assert verification_token_original.user_id == user_id

        # Force the token to be expired.
        verification_token_original.expires_at = datetime.now(timezone.utc) - timedelta(hours = 1)
        create_test_db.commit()

        # Confirm expiration.
        now = datetime.now(timezone.utc)
        expires_at = verification_token_original.expires_at.replace(tzinfo = timezone.utc)
        assert expires_at < now

        # If we try sending an email verification link, it should fail (since we forced 
        # the token to be expired).
        verify_email_response = client.post(f"{AUTH_VERIFY_EMAIL_PREFIX}?token={raw_token}")
        assert verify_email_response.status_code == status.HTTP_400_BAD_REQUEST
        assert verify_email_response.json()["detail"] == "This verification link has expired."

        # The verification token should not be marked used.
        verification_token_modified = create_test_db.query(VerificationTokenModel).filter_by(
            user_id = user_id,
            purpose = EMAIL_VERIFICATION
        ).first()
        assert verification_token_modified.used is False


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
        signup_payload = {
            "email": "someUser@gmail.com",
            "password": "MyPassword@123",
            "display_name": "Some User"
        }

        signup_response = client.post(AUTH_SIGNUP_PREFIX, json = signup_payload)
        assert signup_response.status_code == status.HTTP_201_CREATED

        user_id = uuid.UUID(signup_response.json()["id"])

        raw_token = "used_token"

        # Confirm the token was actually created.
        expected_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        verification_token = create_test_db.query(VerificationTokenModel).filter_by(
            user_id = user_id,
            purpose = EMAIL_VERIFICATION
        ).first()

        assert verification_token is not None
        assert verification_token.token_hash == expected_hash
        assert verification_token.user_id == user_id

        # Mark the verification token as used.
        verification_token.used = True
        create_test_db.commit()

        # Make sure it's used in the DB.
        assert verification_token.used is True

        # If we try sending an email verification link, it should fail (since we marked 
        # the token as used).
        verify_email_response = client.post(f"{AUTH_VERIFY_EMAIL_PREFIX}?token={raw_token}")
        assert verify_email_response.status_code == status.HTTP_400_BAD_REQUEST
        assert verify_email_response.json()["detail"] == (
            "This verification link has already been used."
        )


    def test_verify_email_invalid_token(self, client, create_test_db):
        # Use a token that does not exist in the database
        verify_email = client.post(f"{AUTH_VERIFY_EMAIL_PREFIX}?token=invalid_token")

        assert verify_email.status_code == status.HTTP_400_BAD_REQUEST
        assert verify_email.json()["detail"] == "Invalid or unknown verification token."


    def test_verify_email_token_deleted_with_user(self, client, create_test_db, monkeypatch):
        raw_token = "raw_token"

        # Patch token creation so signup uses a known raw token.
        monkeypatch.setattr(
            "src.api.routers.auth_router.create_raw_verification_token",
            fake_create_token_factory(EMAIL_VERIFICATION, raw_token)
        )

        signup_payload = {
            "email": "someUser@gmail.com",
            "password": "MyPassword@123",
            "display_name": "Some User"
        }

        # Sign up to create a user and verification token.
        signup_response = client.post(AUTH_SIGNUP_PREFIX, json = signup_payload)
        assert signup_response.status_code == status.HTTP_201_CREATED

        user_id = uuid.UUID(signup_response.json()["id"])
    
        # Confirm that the verification token exists for this user.
        expected_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        verification_token = create_test_db.query(VerificationTokenModel).filter_by(
            user_id = user_id,
            purpose = EMAIL_VERIFICATION
        ).first()

        assert verification_token is not None
        assert verification_token.token_hash == expected_hash

        # Delete the user. The model deletes on cascade, so the verification token should
        # also get deleted.
        user = create_test_db.get(UserInternalModel, user_id)
        create_test_db.delete(user)
        create_test_db.commit()

        # Now, trying to verify with the old token should fail because the token no longer exists.
        verify_email_response = client.post(f"{AUTH_VERIFY_EMAIL_PREFIX}?token={raw_token}")

        assert verify_email_response.status_code == status.HTTP_400_BAD_REQUEST
        assert verify_email_response.json()["detail"] == "Invalid or unknown verification token."


    def test_verify_email_commit_failure(self, client, create_test_db, monkeypatch):
        raw_token = "raw_token"

        # Patch token creation so signup uses a known raw token
        monkeypatch.setattr(
            "src.api.routers.auth_router.create_raw_verification_token",
            fake_create_token_factory(EMAIL_VERIFICATION, raw_token)
        )

        signup_payload = {
            "email": "commitfail@gmail.com",
            "password": "MyPassword@123",
            "display_name": "Commit Fail User"
        }

        # Sign up.
        signup_response = client.post(AUTH_SIGNUP_PREFIX, json = signup_payload)
        assert signup_response.status_code == status.HTTP_201_CREATED

        user_id = uuid.UUID(signup_response.json()["id"])

        # Confirm that the token exists.
        expected_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        verification_token = create_test_db.query(VerificationTokenModel).filter_by(
            user_id = user_id,
            purpose = EMAIL_VERIFICATION
        ).first()

        assert verification_token is not None
        assert verification_token.token_hash == expected_hash

        # Monkeypatch commit to fail on the endpoint's commit.
        call_count = {"n": 0}

        def fail_on_first_commit(*args, **kwargs):
            call_count["n"] += 1

            if call_count["n"] == 1:
                raise Exception("Forced commit failure.")

        monkeypatch.setattr(Session, "commit", fail_on_first_commit)

        # If we try to verify, it should tell us an error occurred.
        verify_email_response = client.post(f"{AUTH_VERIFY_EMAIL_PREFIX}?token={raw_token}")

        assert verify_email_response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert verify_email_response.json()["detail"] == (
            "An unexpected error occurred while verifying the email."
        )

        # Confirm the failed commit's rollback actually reverted the
        # in-memory mutations the endpoint made before commit() was called.
        # (verification_token.used, user.is_verified, user.verified_at).
        create_test_db.expire_all()

        user_after_verify = create_test_db.query(UserInternalModel).filter_by(
            id = user_id
        ).first()
        assert user_after_verify.is_verified is False
        assert user_after_verify.verified_at is None
 
        verif_token_after_verify = create_test_db.query(VerificationTokenModel).filter_by(
            user_id = user_id,
            purpose = EMAIL_VERIFICATION
        ).first()
        assert verif_token_after_verify.used is False
 

# ---------------------------------------------------------
# REQUEST PASSWORD RESET
# ---------------------------------------------------------

class TestAuthRequestPasswordReset:

    def test_request_password_reset_success(
        self, 
        client, 
        create_test_db, 
        create_test_user, 
        monkeypatch
    ):

        user = create_test_user()

        # Confirm user exists.
        assert create_test_db.query(UserInternalModel).filter_by(
            email = user.email
        ).first() is not None

        raw_token = "reset_token"

        # Monkeypatch token creation so we know the raw token.
        monkeypatch.setattr(
            "src.api.routers.auth_router.create_raw_verification_token",
            fake_create_token_factory(PASSWORD_RESET, raw_token)
        )

        expected_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        request_password_reset_payload = {"email": user.email}

        request_password_reset_response = client.post(
            AUTH_REQUEST_PASSWORD_RESET_PREFIX, 
            json = request_password_reset_payload
        )

        # Force SQLAlchemy to reload fresh state. Needed because two different SQLAlchemy
        # sessions mutate the same row and we don't want stale data.
        create_test_db.expire_all()   

        # Recall that we should always get back OK as a security measure.
        assert request_password_reset_response.status_code == status.HTTP_200_OK
        assert request_password_reset_response.json()["message"] == (
            "If the email exists, a reset link has been sent."
        )

        # A password reset verification token should exist.
        verification_token = create_test_db.query(VerificationTokenModel).filter_by(
            user_id = user.id,
            purpose = PASSWORD_RESET
        ).first()
        assert verification_token is not None
        assert verification_token.token_hash == expected_hash
        assert verification_token.user_id == user.id
        assert verification_token.used is False

        now = (datetime.now(timezone.utc))
        expires_at = verification_token.expires_at.replace(tzinfo = timezone.utc)
        assert expires_at > now


    def test_request_password_reset_nonexistent_email(self, client, create_test_db):

        # We could create a user and use a nonexistent email to be perfectly explicit,
        # but it's not necessary.
        request_password_reset_payload = {"email": "someUsername@somedomain.com"}

        request_password_reset_response = client.post(
            AUTH_REQUEST_PASSWORD_RESET_PREFIX, 
            json = request_password_reset_payload
        )

        # Recall that we should always get back OK as a security measure.
        assert request_password_reset_response.status_code == status.HTTP_200_OK
        assert request_password_reset_response.json()["message"] == (
            "If the email exists, a reset link has been sent."
        )

        # No token should have been created.
        verification_tokens = create_test_db.query(VerificationTokenModel).all()
        assert len(verification_tokens) == 0


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
        old_verification_token = VerificationTokenModel(
            user_id = user.id,
            token_hash = "old_hash",
            purpose = PASSWORD_RESET,
            expires_at = datetime.now(timezone.utc) + timedelta(hours = 1),
            used = False
        )
        create_test_db.add(old_verification_token)
        create_test_db.commit()

        # Confirm old token exists.
        assert create_test_db.query(VerificationTokenModel).filter_by(
            user_id = user.id,
            purpose = PASSWORD_RESET
        ).count() == 1

        raw_token = "new_token"

        expected_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        # Monkeypatch new token creation.
        monkeypatch.setattr(
            "src.api.routers.auth_router.create_raw_verification_token",
            fake_create_token_factory(PASSWORD_RESET, raw_token)
        )

        request_password_reset_payload = {"email": "someUsername@somedomain.com"}

        # Recall that we should always get back OK as a security measure.
        request_password_reset_response = client.post(
            AUTH_REQUEST_PASSWORD_RESET_PREFIX, 
            json = request_password_reset_payload
        )
        assert request_password_reset_response.status_code == status.HTTP_200_OK
        assert request_password_reset_response.json()["message"] == (
            "If the email exists, a reset link has been sent."
        )

        # Force SQLAlchemy to reload fresh state. Needed because two different SQLAlchemy
        # sessions mutate the same row and we don't want stale data.
        create_test_db.expire_all()  

        # The old token should be have been deleted, and there should be only 
        # the new one in the database.

        verification_tokens = create_test_db.query(VerificationTokenModel).filter_by(
            user_id = user.id,
            purpose = PASSWORD_RESET
        ).all()
        assert len(verification_tokens) == 1
        assert verification_tokens[0].token_hash == expected_hash
        assert verification_tokens[0].user_id == user.id

        now = datetime.now(timezone.utc)
        expires_at = verification_tokens[0].expires_at.replace(tzinfo = timezone.utc)
        assert expires_at > now


    def test_request_password_reset_email_send_failure(self, client, create_test_db, monkeypatch):

        # Create a user manually (no signup needed) and add them to the database.
        user = UserInternalModel(
            email = "someUsername@somedomain.com",
            hashed_password = hash_password("MyPassword@123"),
            display_name = "Some User"
        )
        create_test_db.add(user)
        create_test_db.commit()

        # Confirm user exists.
        assert create_test_db.query(UserInternalModel).filter_by(
            email = user.email
        ).first() is not None

        raw_token = "reset_token"

        expected_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        # Monkeypatch token creation so we know the raw token.
        monkeypatch.setattr(
            "src.api.routers.auth_router.create_raw_verification_token",
            fake_create_token_factory(PASSWORD_RESET, raw_token)
        )

        # Monkeypatch email sending to fail.
        def fail_email(*args, **kwargs):
            raise Exception("Forced email failure.")

        monkeypatch.setattr(
            "src.api.routers.auth_router.send_password_reset_email",
            fail_email
        )

        request_password_reset_payload = {"email": "someUsername@somedomain.com"}

        request_password_reset_response = client.post(
            AUTH_REQUEST_PASSWORD_RESET_PREFIX,
            json = request_password_reset_payload
        )

        # Force SQLAlchemy to reload fresh state. Needed because two different SQLAlchemy
        # sessions mutate the same row and we don't want stale data.
        create_test_db.expire_all()

        # Recall that we should always get back OK as a security measure.
        assert request_password_reset_response.status_code == status.HTTP_200_OK
        assert request_password_reset_response.json()["message"] == (
            "If the email exists, a reset link has been sent."
        )

        # A password reset verification token should exist.
        verification_token = create_test_db.query(VerificationTokenModel).filter_by(
            user_id = user.id,
            purpose = PASSWORD_RESET
        ).first()

        assert verification_token is not None
        assert verification_token.token_hash == expected_hash
        assert verification_token.user_id == user.id
        assert verification_token.used is False

        now = datetime.now(timezone.utc)
        expires_at = verification_token.expires_at.replace(tzinfo = timezone.utc)
        assert expires_at > now


# ---------------------------------------------------------
# RESET PASSWORD
# ---------------------------------------------------------

class TestAuthResetPassword:

    def test_reset_password_success(self, client, create_test_db):

        # Create a user manually (no signup needed) and add them to the database.
        user = UserInternalModel(
            email = "someUsername@somedomain.com",
            hashed_password = hash_password("OldPassword@123"),
            display_name = "Some User"
        )
        create_test_db.add(user)
        create_test_db.commit()

        # Confirm user exists.
        assert create_test_db.query(UserInternalModel).filter_by(
            id = user.id
        ).first() is not None

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

        # Confirm token exists.
        assert create_test_db.query(VerificationTokenModel).filter_by(
            user_id = user.id,
            purpose = PASSWORD_RESET
        ).count() == 1

        # Create an active session token to ensure we test token revocation.
        active_session = SessionTokenModel(
            user_id = user.id,
            refresh_token_hash = "some_session_hash",
            created_at = datetime.now(timezone.utc),
            expires_at = datetime.now(timezone.utc) + timedelta(days = 7),
            revoked_at = None,
            user_agent = "pytest",
            ip_address = "127.0.0.1"
        )
        create_test_db.add(active_session)
        create_test_db.commit()

        # Set cookies so deletion behavior can be asserted.
        client.cookies.set("access_token", "raw_fake_access_token")
        client.cookies.set("refresh_token", "raw_fake_refresh_token")

        reset_password_payload = {
            "token": raw_token,
            "new_password": "NewPassword@123"
        }

        # Recall that we should always get back OK as a security measure.
        reset_password_response = client.post(
            AUTH_RESET_PASSWORD_PREFIX, 
            json = reset_password_payload
        )
        assert reset_password_response.status_code == status.HTTP_200_OK
        assert reset_password_response.json()["message"] == "Password reset successfully."

        set_cookie_header = reset_password_response.headers.get("set-cookie", "")
        assert 'access_token=""' in set_cookie_header
        assert 'refresh_token=""' in set_cookie_header

        # Force SQLAlchemy to reload fresh state. Needed because two different SQLAlchemy
        # sessions mutate the same row and we don't want stale data.
        create_test_db.expire_all()

        # Token should be marked used.
        verif_token_after_reset = (
            create_test_db.query(VerificationTokenModel).filter_by(user_id = user.id).first()
        )
        assert verif_token_after_reset.used is True
        assert verif_token_after_reset.token_hash == token_hash
        assert verif_token_after_reset.purpose == PASSWORD_RESET
        assert verif_token_after_reset.user_id == user.id

        expires_at = verif_token_after_reset.expires_at.replace(tzinfo = timezone.utc)
        now = datetime.now(timezone.utc)
        assert expires_at > now

        # Password should be updated
        updated_user = create_test_db.query(UserInternalModel).filter_by(id = user.id).first()
        assert verify_password("NewPassword@123", updated_user.hashed_password)
        assert not verify_password("OldPassword@123", updated_user.hashed_password)

        # The session should be revoked.
        session_after_reset = create_test_db.query(SessionTokenModel).filter_by(
            id = active_session.id
        ).first()
        assert session_after_reset.revoked_at is not None


    def test_reset_password_invalid_token(self, client, create_test_db):
        # We could create a user to be perfectly explicit, but it's not necessary for this test.
        reset_password_payload = {
            "token": "invalid",
            "new_password": "NewPassword@123"
        }

        reset_password_response = client.post(
            AUTH_RESET_PASSWORD_PREFIX, 
            json = reset_password_payload
        )
        assert reset_password_response.status_code == status.HTTP_400_BAD_REQUEST
        assert reset_password_response.json()["detail"] == (
            "Invalid or unknown password reset token."
        )


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

        reset_password_payload = {
            "token": raw_token,
            "new_password": "NewPassword@123"
        }

        reset_password_response = client.post(
            AUTH_RESET_PASSWORD_PREFIX, 
            json = reset_password_payload
        )
        assert reset_password_response.status_code == status.HTTP_400_BAD_REQUEST
        assert reset_password_response.json()["detail"] == (
            "This password reset link has expired."
        )

        # Force SQLAlchemy to reload fresh state. Needed because two different SQLAlchemy
        # sessions mutate the same row and we don't want stale data.
        create_test_db.expire_all()

        # The password should not have changed and the verification token should be
        # unused.
        user_after_reset = create_test_db.query(UserInternalModel).filter_by(
            id = user.id
        ).first()
        assert verify_password("OldPassword@123", user_after_reset.hashed_password)

        verif_token_after_reset = create_test_db.query(VerificationTokenModel).filter_by(
            user_id = user.id
        ).first()
        assert verif_token_after_reset.used is False


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

        reset_password_payload = {
            "token": raw_token,
            "new_password": "NewPassword@123"
        }

        reset_password_response = client.post(
            AUTH_RESET_PASSWORD_PREFIX, 
            json = reset_password_payload
        )
        assert reset_password_response.status_code == status.HTTP_400_BAD_REQUEST
        assert reset_password_response.json()["detail"] == (
            "This password reset link has already been used."
        )

        # Force SQLAlchemy to reload fresh state. Needed because two different SQLAlchemy
        # sessions mutate the same row and we don't want stale data.
        create_test_db.expire_all()

        # The password should not have changed, but the verification token should still
        # be marked as used.
        user_after_reset = create_test_db.query(UserInternalModel).filter_by(
            id = user.id
        ).first()
        assert verify_password("OldPassword@123", user_after_reset.hashed_password)

        verif_token_after_reset = create_test_db.query(VerificationTokenModel).filter_by(
            user_id = user.id
        ).first()
        assert verif_token_after_reset.used is True


    def test_reset_password_token_deleted_with_user(self, client, create_test_db):

        # Create a user manually.
        user = UserInternalModel(
            email = "someUsername@somedomain.com",
            hashed_password = hash_password("OldPassword@123"),
            display_name = "Some User"
        )
        create_test_db.add(user)
        create_test_db.commit()

        # Confirm user exists.
        assert create_test_db.query(UserInternalModel).filter_by(
            id = user.id
        ).first() is not None

        # Create a valid token for the user.
        raw_token = "raw_token"
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

        # Deleting the user should cascade-delete the token. If cascade failed and the
        # token survived, the endpoint should return "The user does not exist." instead
        # of "Invalid or unknown password reset token." This assertion confirms cascade
        # behavior indirectly.
        create_test_db.delete(user)
        create_test_db.commit()

        # Confirm the user is gone.
        assert create_test_db.query(UserInternalModel).filter_by(
            id = user.id
        ).first() is None

        reset_password_payload = {
            "token": raw_token,
            "new_password": "NewPassword@123"
        }

        reset_password_response = client.post(
            AUTH_RESET_PASSWORD_PREFIX, 
            json = reset_password_payload
        )
        assert reset_password_response.status_code == status.HTTP_400_BAD_REQUEST
        assert reset_password_response.json()["detail"] == (
            "Invalid or unknown password reset token."
        )


    def test_reset_password_weak_password(self, client, create_test_db):

        # Create a user and add to the DB.
        user = UserInternalModel(
            email = "someUsername@somedomain.com",
            hashed_password = hash_password("OldPassword@123"),
            display_name = "Some User"
        )
        create_test_db.add(user)
        create_test_db.commit()

        raw_token = "raw_token"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        # Create and add password reset verification token.
        verification_token = VerificationTokenModel(
            user_id = user.id,
            token_hash = token_hash,
            purpose = PASSWORD_RESET,
            expires_at = datetime.now(timezone.utc) + timedelta(hours = 1),
            used = False
        )
        create_test_db.add(verification_token)
        create_test_db.commit()

        # Try to reset password with a very weak password.
        reset_password_payload = {
            "token": raw_token,
            "new_password": "weakpassword"   
        }

        reset_password_response = client.post(
            AUTH_RESET_PASSWORD_PREFIX, 
            json = reset_password_payload
        )
        assert reset_password_response.status_code == status.HTTP_400_BAD_REQUEST
        assert reset_password_response.json()["detail"] == (
            "Password must contain at least one uppercase letter."
        )

        # Force SQLAlchemy to reload fresh state. Needed because two different SQLAlchemy
        # sessions mutate the same row and we don't want stale data.
        create_test_db.expire_all()

        # Password should not change.
        user_after_reset = create_test_db.query(UserInternalModel).filter_by(
            id = user.id
        ).first()
        assert verify_password("OldPassword@123", user_after_reset.hashed_password)

        # Token should remain unused.
        verif_token_after_reset = create_test_db.query(VerificationTokenModel).filter_by(
            token_hash = token_hash
        ).first()
        assert verif_token_after_reset.used is False


    def test_reset_password_commit_failure(self, client, create_test_db, monkeypatch):
        # Create a user
        user = UserInternalModel(
            email = "someUsername@somedomain.com",
            hashed_password = hash_password("OldPassword@123"),
            display_name = "Some User"
        )
        create_test_db.add(user)
        create_test_db.commit()

        raw_token = "raw_token"
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

        # Monkeypatch commit to fail
        call_count = {"n": 0}

        def fail_commit(*args, **kwargs):
            call_count["n"] += 1

            if call_count["n"] == 1:
                raise Exception("Forced commit failure.")

        monkeypatch.setattr(Session, "commit", fail_commit)

        reset_password_payload = {
            "token": raw_token,
            "new_password": "NewPassword@123"
        }

        reset_password_response = client.post(
            AUTH_RESET_PASSWORD_PREFIX, 
            json = reset_password_payload
        )
        assert reset_password_response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert reset_password_response.json()["detail"] == (
            "An unexpected error occurred while resetting the password."
        )

        # Force SQLAlchemy to reload fresh state. Needed because two different SQLAlchemy
        # sessions mutate the same row and we don't want stale data.
        create_test_db.expire_all()

        # Password should not change.
        user_after_reset = create_test_db.query(UserInternalModel).filter_by(
            id = user.id
        ).first()
        assert verify_password("OldPassword@123", user_after_reset.hashed_password)

        # Token should remain unused.
        verif_token_after_reset = create_test_db.query(VerificationTokenModel).filter_by(
            token_hash = token_hash
        ).first()
        assert verif_token_after_reset.used is False


    def test_reset_password_revokes_all_active_sessions(self, client, create_test_db):
        # Create a user
        user = UserInternalModel(
            email = "someUsername@somedomain.com",
            hashed_password = hash_password("OldPassword@123"),
            display_name = "Some User"
        )
        create_test_db.add(user)
        create_test_db.commit()

        # Create two active session tokens.
        active_session_token_1 = SessionTokenModel(
            user_id = user.id, 
            refresh_token_hash = "hash1",
            created_at = datetime.now(timezone.utc),
            expires_at = datetime.now(timezone.utc) + timedelta(days = 30),
            revoked_at = None
        )

        active_session_token_2 = SessionTokenModel(
            user_id = user.id, 
            refresh_token_hash = "hash2",
            created_at = datetime.now(timezone.utc),
            expires_at = datetime.now(timezone.utc) + timedelta(days = 30),
            revoked_at = None
        )

        # Create an already-revoked session token.
        revoked_session_token = SessionTokenModel(
            user_id = user.id,
            refresh_token_hash = "hash3",
            created_at = datetime.now(timezone.utc),
            expires_at = datetime.now(timezone.utc) + timedelta(days = 30),
            revoked_at = datetime.now(timezone.utc) - timedelta(days = 1)
        )

        # Add all tokens to DB.
        create_test_db.add_all([
            active_session_token_1, active_session_token_2, revoked_session_token
        ])
        create_test_db.commit()

        raw_token = "raw_token"

        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        # Create and add password reset verification token.
        verification_token = VerificationTokenModel(
            user_id = user.id,
            token_hash = token_hash,
            purpose = PASSWORD_RESET,
            expires_at = datetime.now(timezone.utc) + timedelta(hours = 1),
            used = False
        )
        create_test_db.add(verification_token)
        create_test_db.commit()

        # Create a second user with their own active session to ensure 
        # revocation is scoped correctly.
        other_user = UserInternalModel(
            email = "otherUser@somedomain.com",
            hashed_password = hash_password("OtherPassword@123"),
            display_name = "Other User"
        )
        create_test_db.add(other_user)
        create_test_db.commit()

        other_users_session = SessionTokenModel(
            user_id = other_user.id,
            refresh_token_hash = "other_hash",
            created_at = datetime.now(timezone.utc),
            expires_at = datetime.now(timezone.utc) + timedelta(days = 30),
            revoked_at = None
        )
        create_test_db.add(other_users_session)
        create_test_db.commit()

        # Reset password.
        reset_password_payload = {
            "token": raw_token,
            "new_password": "NewPassword@123"
        }

        reset_password_response = client.post(
            AUTH_RESET_PASSWORD_PREFIX, 
            json = reset_password_payload
        )
        assert reset_password_response.status_code == status.HTTP_200_OK
        assert reset_password_response.json()["message"] == "Password reset successfully."

        # Force SQLAlchemy to reload fresh state. Needed because two different SQLAlchemy
        # sessions mutate the same row and we don't want stale data.
        create_test_db.expire_all()

        # Confirm the other user's session was not revoked.
        other_users_session_after_reset = create_test_db.query(SessionTokenModel).filter_by(
            id = other_users_session.id
        ).first()
        assert other_users_session_after_reset.revoked_at is None

        # All active sessions should now be revoked, and there should be 
        # 3 revoked tokens total (the original one and now the two that were previously
        # active).
        session_tokens_after_reset = create_test_db.query(SessionTokenModel).filter(
            SessionTokenModel.user_id == user.id,
            SessionTokenModel.revoked_at.isnot(None)
        ).all()
        assert len(session_tokens_after_reset) == 3  

        # Previously revoked token should retain its original timestamp
        revoked_session_token_after_reset = create_test_db.query(SessionTokenModel).filter(
            SessionTokenModel.id == revoked_session_token.id
        ).first()
        assert revoked_session_token_after_reset.revoked_at == revoked_session_token.revoked_at

        # Password should be updated.
        user_after_reset = create_test_db.query(UserInternalModel).filter_by(
            id = user.id
        ).first()
        assert verify_password("NewPassword@123", user_after_reset.hashed_password)

        # Token should be marked used.
        verif_token_after_reset = create_test_db.query(VerificationTokenModel).filter_by(
            token_hash = token_hash
        ).first()
        assert verif_token_after_reset.used is True


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
        login_payload = {
            "email": "someUsername@somedomain.com",
            "password": "MyPassword@123"
        }

        login_response = client.post(AUTH_LOGIN_PREFIX, json = login_payload)
        assert login_response.status_code == status.HTTP_200_OK

        login_response_body = login_response.json()
        assert login_response_body["token_type"] == "bearer"
        assert "access_token" in login_response_body

        # Cookies should be set.
        assert login_response.cookies.get("refresh_token") is not None
        assert login_response.cookies.get("access_token") is not None

        # Force SQLAlchemy to reload fresh state. Needed because two different SQLAlchemy
        # sessions mutate the same row and we don't want stale data.
        create_test_db.expire_all()

        # Make sure a session token was created.
        session_token = create_test_db.query(SessionTokenModel).filter_by(
            user_id = user.id
        ).first()
        assert session_token is not None
        assert session_token.revoked_at is None
        now = datetime.now(timezone.utc)
        expires_at = session_token.expires_at.replace(tzinfo = timezone.utc)
        assert expires_at > now

        # The refresh_token cookie must match the DB session.
        raw_refresh_token = login_response.cookies.get("refresh_token")
        expected_hash = hashlib.sha256(raw_refresh_token.encode()).hexdigest()
        assert session_token.refresh_token_hash == expected_hash

        # last_login should now be set.
        user_after_login = create_test_db.query(UserInternalModel).filter_by(
            id = user.id
        ).first()
        assert user_after_login.last_login is not None


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
        login_payload = {
            "email": "someUsername@somedomain.com",
            "password": "WrongPassword@123"
        }

        login_response = client.post(AUTH_LOGIN_PREFIX, json = login_payload)

        assert login_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert login_response.json()["detail"] == "Invalid email or password."

        # No cookies should be set.
        assert login_response.cookies.get("refresh_token") is None
        assert login_response.cookies.get("access_token") is None

        # Force SQLAlchemy to reload fresh state. Needed because two different SQLAlchemy
        # sessions mutate the same row and we don't want stale data.
        create_test_db.expire_all()

        # No session token should be created
        assert create_test_db.query(SessionTokenModel).count() == 0

        # last_login should not be updated.
        user_after_login = create_test_db.query(UserInternalModel).filter_by(
            id = user.id
        ).first()
        assert user_after_login.last_login is None


    def test_login_unknown_email(self, client, create_test_db):
        # Try to log in with an account that doesn't exist in the database.
        login_payload = {
            "email": "someUsername@somedomain.com",
            "password": "MyPassword@123"
        }

        login_response = client.post(AUTH_LOGIN_PREFIX, json = login_payload)

        assert login_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert login_response.json()["detail"] == "Invalid email or password."

        # No cookies should be set.
        assert login_response.cookies.get("refresh_token") is None
        assert login_response.cookies.get("access_token") is None

        # No session token should be created.
        assert create_test_db.query(SessionTokenModel).count() == 0


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

        login_payload = {
            "email": "someUsername@somedomain.com",
            "password": "MyPassword@123",
        }

        # Log the user in.
        login_response = client.post(AUTH_LOGIN_PREFIX, json = login_payload)
        assert login_response.status_code == status.HTTP_200_OK

        login_response_body = login_response.json()
        assert login_response_body["token_type"] == "bearer"

        # Make sure the email_verified field in the decoded access token is false.
        access_token = login_response.json()["access_token"]
        decoded_access_token = decode_access_token(access_token)

        assert decoded_access_token.email_verified is False

        # Force SQLAlchemy to reload fresh state. Needed because two different SQLAlchemy
        # sessions mutate the same row and we don't want stale data.
        create_test_db.expire_all()

        # Make sure a session token was created.
        session_token = create_test_db.query(SessionTokenModel).filter_by(
            user_id = user.id
        ).first()
        assert session_token is not None

        # last_login should be updated.
        user_after_login = create_test_db.query(UserInternalModel).filter_by(
            id = user.id
        ).first()
        assert user_after_login.last_login is not None


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

        login_payload = {
            "email": "someUsername@somedomain.com",
            "password": "MyPassword@123",
        }

        # Log the user in.
        login_response = client.post(AUTH_LOGIN_PREFIX, json = login_payload)
        assert login_response.status_code == status.HTTP_200_OK

        # Make sure the email_verified field in the decoded access token is true.
        access_token = login_response.json()["access_token"]
        decoded_access_token = decode_access_token(access_token)

        assert decoded_access_token.email_verified is True

         # Cookies must be set.
        assert login_response.cookies.get("refresh_token") is not None
        assert login_response.cookies.get("access_token") is not None

        # Force SQLAlchemy to reload fresh state. Needed because two different SQLAlchemy
        # sessions mutate the same row and we don't want stale data.
        create_test_db.expire_all()

        # A session_token should have been created and last_login should no longer be None.
        session_token = create_test_db.query(SessionTokenModel).filter_by(
            user_id = user.id
        ).first()
        assert session_token is not None

        # last_login updated
        user_after_login = create_test_db.query(UserInternalModel).filter_by(
            id = user.id
        ).first()
        assert user_after_login.last_login is not None


    def test_login_commit_failure(self, client, create_test_db, monkeypatch):
        # Create and add a new verified user.
        user = UserInternalModel(
            email = "someUsername@somedomain.com",
            hashed_password = hash_password("MyPassword@123"),
            display_name = "Mike Smith",
            is_verified = True
        )
        create_test_db.add(user)
        create_test_db.commit()

        # Monkeypatch commit to fail.
        call_count = {"n": 0}

        def fail_commit(*args, **kwargs):
            call_count["n"] += 1

            if call_count["n"] == 1:
                raise Exception("Forced commit failure.")

        monkeypatch.setattr(Session, "commit", fail_commit)

        login_payload = {
            "email": "someUsername@somedomain.com",
            "password": "MyPassword@123"
        }

        login_response = client.post(AUTH_LOGIN_PREFIX, json = login_payload)

        assert login_response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert login_response.json()["detail"] == "Could not create session token."

        # No cookies should be set.
        assert login_response.cookies.get("refresh_token") is None
        assert login_response.cookies.get("access_token") is None

        # Force SQLAlchemy to reload fresh state. Needed because two different SQLAlchemy
        # sessions mutate the same row and we don't want stale data.
        create_test_db.expire_all()

        # No session token should exit.
        assert create_test_db.query(SessionTokenModel).count() == 0

        # last_login should not be updated.
        user_after_login = create_test_db.query(UserInternalModel).filter_by(
            id = user.id
        ).first()
        assert user_after_login.last_login is None


    def test_login_session_token_fields(self, client, create_test_db):
        # Create and add a new verified user.
        user = UserInternalModel(
            email = "someUsername@somedomain.com",
            hashed_password = hash_password("MyPassword@123"),
            display_name = "Mike Smith",
            is_verified = True
        )
        create_test_db.add(user)
        create_test_db.commit()

        login_payload = {
            "email": "someUsername@somedomain.com",
            "password": "MyPassword@123"
        }

        login_response = client.post(AUTH_LOGIN_PREFIX, json = login_payload)
        assert login_response.status_code == status.HTTP_200_OK

        # Force SQLAlchemy to reload fresh state. Needed because two different SQLAlchemy
        # sessions mutate the same row and we don't want stale data.
        create_test_db.expire_all()

        # A session token should have been created.
        session_token = create_test_db.query(SessionTokenModel).filter_by(
            user_id = user.id
        ).first()

        assert session_token is not None

        # refresh_token_hash must be a valid SHA256 hex string.
        assert len(session_token.refresh_token_hash) == 64
        int(session_token.refresh_token_hash, 16)  # must be valid hex

        # created_at must be recent.
        now = datetime.now(timezone.utc)
        created_at = session_token.created_at

        # Normalize SQLite naive datetime to UTC aware
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo = timezone.utc)

        assert (now - created_at).total_seconds() < 5

        expires_at = session_token.expires_at

        # Normalize SQLite naive datetime to UTC aware.
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo = timezone.utc)

        # expires_at must be in the future.
        assert expires_at > now

        # user_agent and ip_address must be set.
        assert session_token.user_agent is not None
        assert session_token.ip_address is not None

        # revoked_at must be None.
        assert session_token.revoked_at is None


    def test_login_cookie_flags(self, client, create_test_db):
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
            "password": "MyPassword@123"
        }

        response = client.post(AUTH_LOGIN_PREFIX, json = payload)
        assert response.status_code == status.HTTP_200_OK

        # Cookies must exist.
        refresh_cookie = response.cookies.get("refresh_token")
        access_cookie = response.cookies.get("access_token")
        assert refresh_cookie is not None
        assert access_cookie is not None

        # Extract all Set-Cookie headers safely.
        set_cookie_header = response.headers.get("set-cookie", "")

        # Both cookies must have HttpOnly.
        assert set_cookie_header.count("HttpOnly") == 2

        # Both cookies must have Path=/
        assert set_cookie_header.count("Path=/") == 2

        # Both cookies must have correct SameSite
        assert set_cookie_header.count(f"SameSite={SAME_SITE_VALUE}") == 2

        # Secure must NOT appear in testserver environment
        assert "Secure" not in set_cookie_header

        # max_age must be correct
        assert (
            f"Max-Age={REFRESH_TOKEN_LIFETIME_DAYS * 24 * 60 * 60}" 
            in set_cookie_header
        )


    def test_login_access_token_claims(self, client, create_test_db):
        # Create and add a new verified user.
        user = UserInternalModel(
            email = "someUsername@somedomain.com",
            hashed_password = hash_password("MyPassword@123"),
            display_name = "Mike Smith",
            is_verified = True
        )
        create_test_db.add(user)
        create_test_db.commit()

        login_payload = {
            "email": "someUsername@somedomain.com",
            "password": "MyPassword@123"
        }

        login_response = client.post(AUTH_LOGIN_PREFIX, json=login_payload)
        assert login_response.status_code == status.HTTP_200_OK

        access_token = login_response.json()["access_token"]
        decoded_access_token = decode_access_token(access_token)

        # Claims
        assert decoded_access_token.sub == user.id
        assert decoded_access_token.email_verified is True

        # Expiration must be in the future
        now = datetime.now(timezone.utc)
        assert decoded_access_token.exp > now.timestamp()


    def test_login_unknown_email_calls_verify_password(self, client, create_test_db, monkeypatch):
        # Spy to capture calls to verify_password
        calls = []

        def spy_verify_password(password_arg, hash_arg):
            calls.append((password_arg, hash_arg))
            return original_verify_password(password_arg, hash_arg)

        # Patch verify_password inside the auth_router
        monkeypatch.setattr(
            "src.api.routers.auth_router.verify_password",
            spy_verify_password
        )

        # Attempt login with an email that does not exist
        login_payload = {
            "email": "nonexistent@somedomain.com",
            "password": "SomePassword@123"
        }

        login_response = client.post(AUTH_LOGIN_PREFIX, json = login_payload)

        # Response must still be the generic 401.
        assert login_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert login_response.json()["detail"] == "Invalid email or password."

        # verify_password must have been called exactly once.
        assert len(calls) == 1

        # Make sure it was called with the dummy hash.
        assert calls[0][1] == DUMMY_PASSWORD_HASH


# ---------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------

class TestAuthLogout:

    def test_logout_revokes_session(
        self,
        client,
        refresh_token_bundle_for_test_user,
        create_test_db
    ):
        raw_refresh_token = refresh_token_bundle_for_test_user["raw"]
        hashed_refresh_token = refresh_token_bundle_for_test_user["hashed"]

        client.cookies.set("refresh_token", raw_refresh_token)
        response = client.post(AUTH_LOGOUT_PREFIX)

        assert response.status_code == status.HTTP_200_OK

        # Make sure cookies were cleared.
        set_cookie_header = response.headers.get("set-cookie", "")
        assert "refresh_token=" in set_cookie_header
        assert "access_token=" in set_cookie_header
        assert ("Max-Age=0" in set_cookie_header) or ("expires=" in set_cookie_header.lower())

        # Make sure the session row is revoked.
        session_token = create_test_db.query(SessionTokenModel).filter(
            SessionTokenModel.refresh_token_hash == hashed_refresh_token
        ).first()

        assert session_token is not None
        assert session_token.revoked_at is not None


    def test_logout_deletes_cookie(self, client, refresh_token_bundle_for_test_user):

        raw_refresh_token = refresh_token_bundle_for_test_user["raw"]

        client.cookies.set("refresh_token", raw_refresh_token)
        client.cookies.set("access_token", "dummy_access")
        
        response = client.post(AUTH_LOGOUT_PREFIX)

        # The logout endpoint should send a Set-Cookie header that deletes the cookie.
        set_cookie_header = response.headers.get("set-cookie")

        assert set_cookie_header is not None
        assert "refresh_token=" in set_cookie_header
        assert "access_token=" in set_cookie_header
        assert ("Max-Age=0" in set_cookie_header) or ("expires=" in set_cookie_header)

        assert response.json()["message"] == "Logged out"


    def test_logout_with_invalid_refresh_token(self, client, create_test_db):
        raw_refresh_token = "invalid_token"

        # Set a refresh token cookie that does not correspond to any session row.
        client.cookies.set("refresh_token", raw_refresh_token)

        logout_response = client.post(AUTH_LOGOUT_PREFIX)
        assert logout_response.status_code == status.HTTP_200_OK

        # No session row should exist for this hash.
        refresh_token_hash = hashlib.sha256(raw_refresh_token.encode()).hexdigest()
        session_token = create_test_db.query(SessionTokenModel).filter_by(
            refresh_token_hash = refresh_token_hash
        ).first()

        assert session_token is None


    def test_logout_with_nonexistent_session_token(self, client, create_test_db):
        # Create a valid-looking refresh token for a fake user. 
        # Do not insert a session row.
        raw_refresh_token = create_refresh_token(
            user_id = str(uuid.uuid4()),
            email_verified = True,
            refresh_token_id = str(uuid.uuid4())
        )

        client.cookies.set("refresh_token", raw_refresh_token)

        logout_response = client.post(AUTH_LOGOUT_PREFIX)
        assert logout_response.status_code == status.HTTP_200_OK

        refresh_token_hash = hashlib.sha256(raw_refresh_token.encode()).hexdigest()
        session_token = create_test_db.query(SessionTokenModel).filter_by(
            refresh_token_hash = refresh_token_hash
        ).first()

        assert session_token is None


    def test_logout_revocation_commit_failure(
        self,
        client,
        refresh_token_bundle_for_test_user,
        create_test_db,
        monkeypatch
    ):
        raw_refresh_token = refresh_token_bundle_for_test_user["raw"]
        refresh_token_hash = refresh_token_bundle_for_test_user["hashed"]

        # Force commit to fail.
        def fail_commit(self, *args, **kwargs):
            raise Exception("DB failure")

        monkeypatch.setattr(Session, "commit", fail_commit)

        client.cookies.set("refresh_token", raw_refresh_token)
        logout_response = client.post(AUTH_LOGOUT_PREFIX)

        assert logout_response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert logout_response.json()["detail"] == "Could not revoke session token."

        # Cookies should still be cleared even on failure.
        set_cookie_header = logout_response.headers.get("set-cookie", "")
        assert "refresh_token=" in set_cookie_header
        assert "access_token=" in set_cookie_header
        assert ("Max-Age=0" in set_cookie_header) or ("expires=" in set_cookie_header.lower())

        # Ensure the session row was not revoked.
        create_test_db.expire_all()
        session_token = create_test_db.query(SessionTokenModel).filter_by(
            refresh_token_hash = refresh_token_hash
        ).first()

        assert session_token is not None
        assert session_token.revoked_at is None


# ---------------------------------------------------------
# LOGOUT ALL
# ---------------------------------------------------------

class TestAuthLogoutAll:

    def test_logout_all_without_cookie_succeeds_and_deletes_cookies(
        self,
        client,
        create_test_db
    ):
        # Purposefully don't set a refresh token cookie so we can ensure
        # the endpoint still succeeds and deletes auth cookies.
        logout_response = client.post(AUTH_LOGOUT_ALL_PREFIX)

        assert logout_response.status_code == status.HTTP_200_OK
        assert logout_response.json()["message"] == "Logged out of all devices."

        set_cookie_headers = logout_response.headers.get_list("set-cookie")

        # The response should delete both cookies and make them expired.

        assert any("refresh_token=" in h for h in set_cookie_headers)
        assert any("access_token=" in h for h in set_cookie_headers)
        assert any("Max-Age=0" in h or "expires=" in h for h in set_cookie_headers)


    def test_logout_all_with_invalid_refresh_token_deletes_cookies(
        self,
        client,
        create_test_db
    ):
        # Set a refresh token cookie that does NOT correspond to any session.
        client.cookies.set("refresh_token", "fake token")

        logout_response = client.post(AUTH_LOGOUT_ALL_PREFIX)

        assert logout_response.status_code == status.HTTP_200_OK
        assert logout_response.json()["message"] == "Logged out of all devices."

        # The response should delete both cookies.
        set_cookie_headers = logout_response.headers.get_list("set-cookie")

        assert any("refresh_token=" in h for h in set_cookie_headers)
        assert any("access_token=" in h for h in set_cookie_headers)
        assert any("Max-Age=0" in h or "expires=" in h for h in set_cookie_headers)

        # No sessions should be revoked.
        user_sessions = create_test_db.query(SessionTokenModel).all()
        assert len(user_sessions) == 0


    def test_logout_all_revokes_all_sessions_for_user(
        self,
        client,
        refresh_token_bundle_for_test_user,
        create_test_db
    ):
        # This time, we set a refresh cookie so the endpoint can identify 
        # the user and revoke all their sessions.
        user = refresh_token_bundle_for_test_user["user"]

        raw_refresh_token = refresh_token_bundle_for_test_user["raw"]
        client.cookies.set("refresh_token", raw_refresh_token)

        # Create a second user to ensure revocation is scoped correctly.
        other_user = UserInternalModel(
            email = "other@somedomain.com",
            hashed_password = hash_password("OtherPassword@123"),
            display_name = "Other User"
        )
        create_test_db.add(other_user)
        create_test_db.commit()

        other_users_session = SessionTokenModel(
            user_id = other_user.id,
            refresh_token_hash = "other_hash",
            created_at = datetime.now(timezone.utc),
            expires_at = datetime.now(timezone.utc) + timedelta(days = 30),
            revoked_at = None
        )
        create_test_db.add(other_users_session)
        create_test_db.commit()

        # Create an already‑revoked session for the main user
        already_revoked_session = SessionTokenModel(
            user_id = user.id,
            refresh_token_hash = "revoked_hash",
            created_at = datetime.now(timezone.utc),
            expires_at = datetime.now(timezone.utc) + timedelta(days = 30),
            revoked_at = datetime.now(timezone.utc) - timedelta(days = 1)
        )
        create_test_db.add(already_revoked_session)
        create_test_db.commit()

        logout_response = client.post(AUTH_LOGOUT_ALL_PREFIX)

        create_test_db.expire_all()

        assert logout_response.status_code == status.HTTP_200_OK
        assert logout_response.json()["message"] == "Logged out of all devices."

        # All sessions for this user should now be revoked.
        user_sessions = create_test_db.query(SessionTokenModel).filter(
            SessionTokenModel.user_id == user.id
        ).all()

        assert len(user_sessions) > 0
        for s in user_sessions:
            assert s.revoked_at is not None

        # Ensure the other user's session was not revoked.
        other_users_session_after = create_test_db.query(SessionTokenModel).filter_by(
            id = other_users_session.id
        ).first()
        assert other_users_session_after.revoked_at is None

        # Ensure already‑revoked session preserved its timestamp.
        preserved = create_test_db.query(SessionTokenModel).filter_by(
            id = already_revoked_session.id
        ).first()
        assert preserved.revoked_at == already_revoked_session.revoked_at


    def test_logout_all_with_valid_refresh_token_but_no_session(self, client, create_test_db):
        # Create a valid refresh token for a fake user. 
        # Do not insert a session row.
        raw_refresh_token = create_refresh_token(
            user_id = str(uuid.uuid4()),
            email_verified = True,
            refresh_token_id = str(uuid.uuid4())
        )

        client.cookies.set("refresh_token", raw_refresh_token)

        logout_response = client.post(AUTH_LOGOUT_ALL_PREFIX)

        assert logout_response.status_code == status.HTTP_200_OK
        assert logout_response.json()["message"] == "Logged out of all devices."

        # No session row should exist for this hash.
        refresh_token_hash = hashlib.sha256(raw_refresh_token.encode()).hexdigest()
        session_token = create_test_db.query(SessionTokenModel).filter_by(
            refresh_token_hash = refresh_token_hash
        ).first()

        assert session_token is None


    def test_logout_all_revocation_commit_failure(
        self,
        client,
        refresh_token_bundle_for_test_user,
        create_test_db,
        monkeypatch
    ):
        raw_refresh_token = refresh_token_bundle_for_test_user["raw"]
        refresh_token_hash = refresh_token_bundle_for_test_user["hashed"]

        # Force commit to fail.
        def fail_commit(self, *args, **kwargs):
            raise Exception("DB failure")

        monkeypatch.setattr(Session, "commit", fail_commit)

        client.cookies.set("refresh_token", raw_refresh_token)
        logout_response = client.post(AUTH_LOGOUT_ALL_PREFIX)

        assert logout_response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert logout_response.json()["detail"] == "Could not revoke all session tokens."

        # Cookies should not be cleared on failure (logout_all differs from logout).
        set_cookie_header = logout_response.headers.get("set-cookie")
        assert set_cookie_header is None or set_cookie_header == ""

        # Ensure no session was revoked.
        create_test_db.expire_all()
        session_token = create_test_db.query(SessionTokenModel).filter_by(
            refresh_token_hash = refresh_token_hash
        ).first()

        assert session_token is not None
        assert session_token.revoked_at is None


# ---------------------------------------------------------
# ACTIVE SESSIONS
# ---------------------------------------------------------

class TestAuthActiveSessions:

    def test_active_sessions_returns_all_sessions_sorted(
        self,
        client,
        refresh_token_bundle_for_test_user,
        create_test_db
    ):
        user = refresh_token_bundle_for_test_user["user"]

        # The user already has one session from the fixture. Create a second one
        # manually to make sure sorting works.
        now = datetime.now(timezone.utc)
        later = now + timedelta(minutes = 5)

        second_session = SessionTokenModel(
            user_id = user.id,
            refresh_token_hash = "fake_refresh_token_hash",
            refresh_token_id = uuid.uuid4(),
            created_at = later,
            expires_at = later + timedelta(days = 30),
            user_agent = "pytest-agent",
            ip_address = "127.0.0.1"
        )
        create_test_db.add(second_session)
        create_test_db.commit()

        # Create another user with their own session.
        other_user = UserInternalModel(
            email = "other@somedomain.com",
            hashed_password = hash_password("OtherPassword@123"),
            display_name = "Other User",
            is_verified = True
        )
        create_test_db.add(other_user)
        create_test_db.commit()

        other_session = SessionTokenModel(
            user_id = other_user.id,
            refresh_token_hash = "other_hash",
            refresh_token_id = uuid.uuid4(),
            created_at = datetime.now(timezone.utc),
            expires_at = datetime.now(timezone.utc) + timedelta(days = 30),
            user_agent = "other-agent",
            ip_address = "10.0.0.1"
        )
        create_test_db.add(other_session)
        create_test_db.commit()

        # Create a revoked session for the first user.
        revoked_session = SessionTokenModel(
            user_id = user.id,
            refresh_token_hash = "revoked_hash",
            refresh_token_id = uuid.uuid4(),
            created_at = now - timedelta(minutes = 10),
            expires_at = now + timedelta(days = 30),
            revoked_at = now - timedelta(days = 1),
            user_agent = "revoked-agent",
            ip_address = "127.0.0.1"
        )
        create_test_db.add(revoked_session)
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
        client.cookies.set("access_token", create_access_token(str(user.id), True))
        action_sessions_response = client.get(AUTH_ACTIVE_SESSIONS_PREFIX)

        assert action_sessions_response.status_code == status.HTTP_200_OK

        sessions = action_sessions_response.json()["sessions"]
        assert len(sessions) == 3

        # Sessions should be sorted by created_at in descending order.
        created_at_times = [s["created_at"] for s in sessions]
        assert created_at_times == sorted(created_at_times, reverse = True)

        # Make sure the other user's session is not included and the
        # revoked session is included.
        session_ids = {s["id"] for s in sessions}
        assert str(other_session.id) not in session_ids
        assert str(revoked_session.id) in session_ids

        # Validate fields for one of the sessions.
        first_session = sessions[0]
        assert "user_agent" in first_session
        assert "ip_address" in first_session
        assert "expires_at" in first_session
        assert "revoked_at" in first_session

        assert first_session["user_agent"] == "pytest-agent"
        assert first_session["ip_address"] == "127.0.0.1"
        assert first_session["revoked_at"] is None


    def test_active_sessions_fails_if_no_access_token(
        self,
        client
    ):
        active_sessions_response = client.get(AUTH_ACTIVE_SESSIONS_PREFIX)

        assert active_sessions_response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------
# TERMINATE SESSION
# ---------------------------------------------------------

class TestAuthTerminateSession:

    def test_terminate_session_successfully_revokes_session(
        self,
        client,
        refresh_token_bundle_for_test_user,
        create_test_db
    ):
        user = refresh_token_bundle_for_test_user["user"]

        # Authenticate the user.
        client.cookies.set("access_token", create_access_token(str(user.id), True))

        # Get the test user's existing session (which we get from a fixture).
        session_token = create_test_db.query(SessionTokenModel).filter(
            SessionTokenModel.user_id == user.id
        ).first()

        terminate_session_response = (
            client.post(f"{AUTH_TERMINATE_SESSION_PREFIX}/{session_token.id}")
        )

        assert terminate_session_response.status_code == status.HTTP_200_OK
        assert terminate_session_response.json()["message"] == "Session terminated successfully."

        # The session should now be revoked. Grab the updated row from the DB. Otherwise, 
        # we may have a stale session_token.
        create_test_db.refresh(session_token)

        assert session_token.revoked_at is not None


    def test_terminate_session_already_revoked(
        self,
        client,
        refresh_token_bundle_for_test_user,
        create_test_db
    ):
        user = refresh_token_bundle_for_test_user["user"]

        # Authenticate the user.
        client.cookies.set("access_token", create_access_token(str(user.id), True))

        # Revoke the session manually.
        session_token = create_test_db.query(SessionTokenModel).filter(
            SessionTokenModel.user_id == user.id
        ).first()
        session_token.revoked_at = datetime.now(timezone.utc)
        create_test_db.commit()

        terminate_session_response = (
            client.post(f"{AUTH_TERMINATE_SESSION_PREFIX}/{session_token.id}")
        )

        assert terminate_session_response.status_code == status.HTTP_200_OK
        assert terminate_session_response.json()["message"] == "Session already terminated."


    def test_terminate_session_not_found(
        self,
        client,
        refresh_token_bundle_for_test_user
    ):
        user = refresh_token_bundle_for_test_user["user"]

        # Authenticate the user.
        client.cookies.set("access_token", create_access_token(str(user.id), True))

        # Use a random UUID that does not exist in the database.
        random_id = uuid.uuid4()

        terminate_session_response = (
            client.post(f"{AUTH_TERMINATE_SESSION_PREFIX}/{random_id}")
        )

        assert terminate_session_response.status_code == status.HTTP_404_NOT_FOUND
        assert terminate_session_response.json()["detail"] == "Session not found."


    def test_terminate_session_commit_failure(
        self,
        client,
        refresh_token_bundle_for_test_user,
        create_test_db,
        monkeypatch
    ):
        user = refresh_token_bundle_for_test_user["user"]

        # Authenticate the user.
        client.cookies.set("access_token", create_access_token(str(user.id), True))

        # Get the user's session.
        session_token = create_test_db.query(SessionTokenModel).filter(
            SessionTokenModel.user_id == user.id
        ).first()

        # Force commit to fail.
        def fail_commit(self, *args, **kwargs):
            raise Exception("Commit failure.")

        monkeypatch.setattr(Session, "commit", fail_commit)

        terminate_session_response = (
            client.post(f"{AUTH_TERMINATE_SESSION_PREFIX}/{session_token.id}")
        )

        assert terminate_session_response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert terminate_session_response.json()["detail"] == "Failed to terminate session."

        # Ensure the session was not revoked.
        create_test_db.expire_all()
        session_token_after_terminate = create_test_db.query(SessionTokenModel).filter(
            SessionTokenModel.id == session_token.id
        ).first()

        assert session_token_after_terminate.revoked_at is None


    def test_terminate_session_requires_authentication(self, client):

        terminate_session_response = (
            client.post(f"{AUTH_TERMINATE_SESSION_PREFIX}/{uuid.uuid4()}")
        )

        assert terminate_session_response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_terminate_session_belonging_to_another_user_returns_not_found(
        self, 
        client, 
        refresh_token_bundle_for_test_user, 
        create_test_db
    ):
        user = refresh_token_bundle_for_test_user["user"]

        # Set the access token for our test user but not for a secondary, other user.
        client.cookies.set("access_token", create_access_token(str(user.id), True))

        # Create and add another user with accompanying session.
        other_user = UserInternalModel(
            email = "otherUser@somedomain.com",
            hashed_password = hash_password("OtherPassword@123"),
            display_name = "Other User",
            is_verified = True
        )
        create_test_db.add(other_user)
        create_test_db.commit()

        other_session = SessionTokenModel(
            user_id = other_user.id, 
            refresh_token_hash = "other_hash", 
            refresh_token_id = uuid.uuid4(),
            created_at = datetime.now(timezone.utc), 
            expires_at = datetime.now(timezone.utc) + timedelta(days = 30),
            user_agent = "other-agent", 
            ip_address = "10.0.0.1"
        )
        create_test_db.add(other_session)
        create_test_db.commit()

        # Try to terminate the other user's session.
        terminate_session_response = (
            client.post(f"{AUTH_TERMINATE_SESSION_PREFIX}/{other_session.id}")
        )

        # It should fail, since we did not set an access token.
        assert terminate_session_response.status_code == status.HTTP_404_NOT_FOUND
        assert terminate_session_response.json()["detail"] == "Session not found."

        create_test_db.expire_all()

        # Make sure the other user's session still exists.
        other_session_after_terminate = create_test_db.query(SessionTokenModel).filter_by(
            id = other_session.id
        ).first()
        assert other_session_after_terminate.revoked_at is None

# ---------------------------------------------------------
# REFRESH
# ---------------------------------------------------------

class TestAuthRefresh:

    def test_refresh_issues_new_access_token(
        self,
        client,
        refresh_token_bundle_for_test_user,
        create_test_db
    ):
        user = refresh_token_bundle_for_test_user["user"]
        original_raw_refresh_token = refresh_token_bundle_for_test_user["raw"]

        client.cookies.set("refresh_token", original_raw_refresh_token)

        refresh_response = client.post(AUTH_REFRESH_PREFIX)

        assert refresh_response.status_code == status.HTTP_200_OK

        # We should have a new access token.
        body = refresh_response.json()
        assert "access_token" in body

        # The new access token should differ from the old one.
        # The fixture does not expose the old access token, but we can assert
        # that the new one is structurally valid and non-empty.
        new_access_token = body["access_token"]
        assert isinstance(new_access_token, str)
        assert len(new_access_token) > 10  

        # There should be a new session token in the DB
        session_tokens = create_test_db.query(SessionTokenModel).filter(
            SessionTokenModel.user_id == user.id
        ).all()

        # There should be exactly two tokens, the original (now revoked) one,
        # and a newly created one.
        assert len(session_tokens) == 2

        revoked_sessions = [s for s in session_tokens if s.revoked_at is not None]
        live_sessions = [s for s in session_tokens if s.revoked_at is None]

        assert len(revoked_sessions) == 1
        assert len(live_sessions) == 1

        # The live token should correspond to the new access token.
        assert live_sessions[0].refresh_token_hash is not None


    def test_refresh_rotates_refresh_token(
        self,
        client,
        refresh_token_bundle_for_test_user,
        create_test_db
    ):
        user = refresh_token_bundle_for_test_user["user"]
        old_raw_refresh_token = refresh_token_bundle_for_test_user["raw"]
        old_hashed_refresh_token = refresh_token_bundle_for_test_user["hashed"]

        client.cookies.set("refresh_token", old_raw_refresh_token)

        refresh_response = client.post(AUTH_REFRESH_PREFIX)

        assert refresh_response.status_code == status.HTTP_200_OK

        # Extract the new refresh token from the cookie header. It should be
        # different from the original one.
        set_cookie_header = refresh_response.headers.get("set-cookie")
        assert set_cookie_header is not None
        assert "refresh_token=" in set_cookie_header

        new_raw_refresh_token = set_cookie_header.split("refresh_token=")[1].split(";")[0]
        assert new_raw_refresh_token != old_raw_refresh_token

        # The DB should reflect the rotation.
        session_tokens = create_test_db.query(SessionTokenModel).filter(
            SessionTokenModel.user_id == user.id
        ).all()

        # There should be exactly two tokens, the original (now revoked) one,
        # and a newly created one.
        assert len(session_tokens) == 2

        revoked_sessions = ([
            s for s in session_tokens 
            if s.refresh_token_hash == old_hashed_refresh_token
        ])
        live_sessions = ([
            s for s in session_tokens 
            if s.refresh_token_hash != old_hashed_refresh_token
        ])

        assert len(revoked_sessions) == 1
        assert revoked_sessions[0].revoked_at is not None

        assert len(live_sessions) == 1
        assert live_sessions[0].revoked_at is None

        # The live token's hash must match the new cookie value.
        expected_hash = hashlib.sha256(new_raw_refresh_token.encode()).hexdigest()
        assert live_sessions[0].refresh_token_hash == expected_hash


    def test_refresh_replay_within_grace_window_is_treated_as_benign(
        self,
        client,
        refresh_token_bundle_for_test_user,
        create_test_db
    ):
        # An initial call to refresh should be successful.
        user = refresh_token_bundle_for_test_user["user"]
        original_raw_refresh_token = refresh_token_bundle_for_test_user["raw"]

        client.cookies.set("refresh_token", original_raw_refresh_token)

        # This should revoke one session and create a new one with a new
        # refresh token id and hash, as well as revoked_at of None.
        first_refresh_response = client.post(AUTH_REFRESH_PREFIX)

        assert first_refresh_response.status_code == status.HTTP_200_OK

        # Save the revoked_at timestamp for the original session.
        rotated_session = create_test_db.query(SessionTokenModel).filter(
            SessionTokenModel.user_id == user.id,
            SessionTokenModel.revoked_at.isnot(None)
        ).first()
        original_revoked_at = rotated_session.revoked_at

        # Immediately replay the now-rotated original token, well within
        # CONCURRENT_REFRESH_GRACE_SECONDS. This should be treated as benign
        # concurrency, not reuse. No account-wide revocation, but the refresh
        # should fail. We should have the same two tokens as we did immediately
        # after the first refresh.
        client.cookies.clear()
        client.cookies.set("refresh_token", original_raw_refresh_token)

        second_refresh_response = client.post(AUTH_REFRESH_PREFIX)

        assert second_refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert second_refresh_response.json()["detail"] == "Refresh token expired or stale."

        # We should have one removked token from the first refresh + one new sesion token.
        # The benign replay (second call to refresh) should produce no more tokens.
        session_tokens = create_test_db.query(SessionTokenModel).filter(
            SessionTokenModel.user_id == user.id
        ).all()
        assert len(session_tokens) == 2

        unrevoked_tokens = [s for s in session_tokens if s.revoked_at is None]
        assert len(unrevoked_tokens) == 1 

        # The revoked_at timestamp should not have changed if we correctly identified the 
        # benign replay.
        revoked_tokens = [
            s for s in session_tokens if s.revoked_at is not None
        ][0]
        assert revoked_tokens.revoked_at == original_revoked_at


    def test_refresh_replay_outside_grace_window_is_treated_as_reuse(
        self,
        client,
        refresh_token_bundle_for_test_user,
        create_test_db,
        create_test_user,
    ):
        # An initial call to refresh should be successful.
        user = refresh_token_bundle_for_test_user["user"]
        original_raw_refresh_token = refresh_token_bundle_for_test_user["raw"]
        original_hashed_token = refresh_token_bundle_for_test_user["hashed"]

        client.cookies.set("refresh_token", original_raw_refresh_token)

        # This should revoke one session and create a new one with a new
        # refresh token id and hash, as well as revoked_at of None.
        first_refresh_response = client.post(AUTH_REFRESH_PREFIX)

        assert first_refresh_response.status_code == status.HTTP_200_OK

        # Create another user and session to ensure isolation.
        other_user = create_test_user(
            email = "otherUser@somedomain.com",
            password = "OtherPassword@123",
            display_name = "Other User",
            is_verified = True
        )

        other_session = SessionTokenModel(
            user_id = other_user.id,
            refresh_token_hash = "other_hash",
            refresh_token_id = uuid.uuid4(),
            created_at = datetime.now(timezone.utc),
            expires_at = datetime.now(timezone.utc) + timedelta(days = 30),
            revoked_at = None
        )
        create_test_db.add(other_session)
        create_test_db.commit()

        # Backdate the original (now rotated) session token's revoked_at so it
        # falls outside CONCURRENT_REFRESH_GRACE_SECONDS. This simulates a
        # genuinely stale/stolen token being replayed well after rotation,
        # without needing the test to actually sleep. The refresh should fail.
        rotated_session_token = create_test_db.query(SessionTokenModel).filter(
            SessionTokenModel.refresh_token_hash == original_hashed_token
        ).first()

        rotated_session_token.revoked_at = (
            datetime.now(timezone.utc)
            - timedelta(seconds = CONCURRENT_REFRESH_GRACE_SECONDS + 1)
        )
        create_test_db.commit()

        client.cookies.clear()
        client.cookies.set("refresh_token", original_raw_refresh_token)

        second_refresh_response = client.post(AUTH_REFRESH_PREFIX)

        assert second_refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert second_refresh_response.json()["detail"] == (
            "Refresh token reuse detected. All sessions revoked."
        )

        # All sessions for the test user should be revoked to protect against malicious 
        # attacks.
        session_tokens = create_test_db.query(SessionTokenModel).filter(
            SessionTokenModel.user_id == user.id
        ).all()

        assert len(session_tokens) > 0
        for s in session_tokens:
            assert s.revoked_at is not None

        # The other user's session must remain untouched.
        other_session_after = create_test_db.query(SessionTokenModel).filter_by(
            id = other_session.id
        ).first()
        assert other_session_after.revoked_at is None


    def test_refresh_missing_cookie_returns_401(self, client):
        # Do not set a refresh token cookie.
        refresh_response = client.post(AUTH_REFRESH_PREFIX)

        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert refresh_response.json()["detail"] == "Missing refresh token."


    def test_refresh_invalid_refresh_token_returns_401(self, client, create_test_db):
        # Set a refresh token cookie that does not correspond to any session.
        client.cookies.set("refresh_token", "fakeToken")

        refresh_response = client.post(AUTH_REFRESH_PREFIX)

        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert refresh_response.json()["detail"] == "Invalid refresh token."


    def test_refresh_expired_refresh_token_returns_401(
        self,
        client,
        refresh_token_bundle_for_test_user,
        create_test_db
    ):
        raw_refresh_token = refresh_token_bundle_for_test_user["raw"]
        refresh_token_hash = refresh_token_bundle_for_test_user["hashed"]

        # Expire the session token manually.
        session_token = create_test_db.query(SessionTokenModel).filter(
            SessionTokenModel.refresh_token_hash == refresh_token_hash
        ).first()

        session_token.expires_at = datetime.now(timezone.utc) - timedelta(days = 1)
        create_test_db.commit()

        client.cookies.set("refresh_token", raw_refresh_token)

        refresh_response = client.post(AUTH_REFRESH_PREFIX)

        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert refresh_response.json()["detail"] == "Refresh token expired."


    def test_refresh_atomic_update_fails_returns_401(
        self,
        client,
        refresh_token_bundle_for_test_user,
        create_test_db,
        monkeypatch
    ):
        raw_refresh_token = refresh_token_bundle_for_test_user["raw"]
        hashed_refresh_token = refresh_token_bundle_for_test_user["hashed"]
        user_id = refresh_token_bundle_for_test_user["user"].id

        client.cookies.set("refresh_token", raw_refresh_token)

        # Monkeypatch Query.update to simulate atomic update failure.
        original_update = Query.update
        call_count = {"n": 0}

        def selective_fail_update(self, *args, **kwargs):
            call_count["n"] += 1

            # The rotation CAS is the first (and only) update call on this path
            if call_count["n"] == 1:
                return 0
            
            return original_update(self, *args, **kwargs)

        monkeypatch.setattr(Query, "update", selective_fail_update)

        refresh_response = client.post(AUTH_REFRESH_PREFIX)

        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert refresh_response.json()["detail"] == "Refresh token expired."

        create_test_db.expire_all()

        session_token_after = create_test_db.query(SessionTokenModel).filter_by(
            refresh_token_hash = hashed_refresh_token
        ).first()

        # The original session must still exist and not be revoked.
        assert session_token_after is not None
        assert session_token_after.revoked_at is None

        # No new session should have been created.
        all_sessions = create_test_db.query(SessionTokenModel).filter(
            SessionTokenModel.user_id == user_id
        ).all()
        assert len(all_sessions) == 1


# ---------------------------------------------------------
# ME
# ---------------------------------------------------------

class TestAuthMe:

    def test_me_returns_user_details(
        self, 
        client, 
        access_token_for_test_user
    ):
        user = access_token_for_test_user["user"]
        access_token = access_token_for_test_user["access_token"]

        client.cookies.set("access_token", access_token)
        me_response = client.get(AUTH_ME_PREFIX)

        me_data = me_response.json()

        assert me_response.status_code == status.HTTP_200_OK
        assert me_data["id"] == str(user.id)
        assert me_data["email"] == user.email
        assert me_data["created_at"] != ""


# ---------------------------------------------------------
# EXPORT USER DATA
# ---------------------------------------------------------

class TestAuthExportUserData:

    def test_export_user_data_success(
        self,
        client,
        refresh_token_bundle_for_test_user,
        create_test_db
    ):
        user = refresh_token_bundle_for_test_user["user"]

        # Simulate a fresh login by setting last_login to now. Recall that the
        # endpoint requires the user to have logged in within the last 5 minutes.
        user.last_login = datetime.now(timezone.utc)
        create_test_db.commit()

        # Authenticate the user.
        client.cookies.set("access_token", create_access_token(str(user.id), True))

        export_user_data_response = client.get(AUTH_EXPORT_USER_DATA_PREFIX)

        assert export_user_data_response.status_code == status.HTTP_200_OK

        # The response body should be gzip-compressed bytes.
        decompressed = gzip.decompress(export_user_data_response.content)
        data = json.loads(decompressed)

        # Verify that one of the expected fields is in the file. The user id should be
        # that of our test user.
        assert isinstance(data, dict)

        assert "user" in data  
        assert data["user"]["id"] == str(user.id)

        assert "session_tokens" in data
        assert len(data["session_tokens"]) >= 1

        assert "verification_tokens" in data

        assert "user_tea_profile_notes" in data

        # Verify that a DSAR log was created and fulfilled.
        dsar_logs = create_test_db.query(DSARLogModel).filter_by(user_id = user.id).all()

        assert len(dsar_logs) == 1
        assert dsar_logs[0].request_type == DSAR_REQUEST_EXPORT_USER_DATA
        assert dsar_logs[0].status == DSAR_STATUS_FULFILLED
        assert dsar_logs[0].fulfilled_at is not None


    def test_export_user_data_fails_if_no_access_token(
        self,
        client,
        create_test_user,
        create_test_db
    ):
        user = create_test_user()

        export_user_data_response = client.get(AUTH_EXPORT_USER_DATA_PREFIX)

        assert export_user_data_response.status_code == status.HTTP_401_UNAUTHORIZED

        # No DSAR log should be created.
        dsar_logs = create_test_db.query(DSARLogModel).filter_by(
            user_id = user.id
        ).all()
        assert dsar_logs == []


    def test_export_user_data_marks_dsar_failed_on_exception(
        self,
        client,
        refresh_token_bundle_for_test_user,
        create_test_db,
        monkeypatch
    ):
        user = refresh_token_bundle_for_test_user["user"]

        user.last_login = datetime.now(timezone.utc)
        create_test_db.commit()

        client.cookies.set("access_token", create_access_token(str(user.id), True))

        def export_user_data_exception(*args, **kwargs):
            raise Exception("Failed to export user data.")

        monkeypatch.setattr(
            UserDataExportService,
            "export_user_data",
            export_user_data_exception
        )

        export_user_data_response = client.get(AUTH_EXPORT_USER_DATA_PREFIX)

        assert export_user_data_response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

        # Verify DSAR log marked FAILED.
        dsar_logs = create_test_db.query(DSARLogModel).filter_by(user_id = user.id).all()

        assert len(dsar_logs) == 1
        assert dsar_logs[0].status == DSAR_STATUS_FAILED
        assert dsar_logs[0].notes == "Failed to export user data."
        assert dsar_logs[0].fulfilled_at is None


    def test_export_user_data_requires_fresh_login(
        self,
        client,
        refresh_token_bundle_for_test_user,
        create_test_db
    ):
        user = refresh_token_bundle_for_test_user["user"]

        # Set last_login far in the past.
        user.last_login = datetime.now(timezone.utc) - timedelta(days = 30)
        create_test_db.commit()

        # Authenticate user.
        client.cookies.set("access_token", create_access_token(str(user.id), True))

        export_user_data_response = client.get(AUTH_EXPORT_USER_DATA_PREFIX)

        assert export_user_data_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "log in again" in export_user_data_response.json()["detail"]

        # Make sure a new DSAR log was not created.
        assert create_test_db.query(DSARLogModel).filter_by(
            user_id = user.id
        ).all() == []


    def test_export_user_data_returns_valid_gzip(
        self,
        client,
        refresh_token_bundle_for_test_user,
        create_test_db
    ):
        user = refresh_token_bundle_for_test_user["user"]

        user.last_login = datetime.now(timezone.utc)
        create_test_db.commit()

        client.cookies.set("access_token", create_access_token(str(user.id), True))

        export_user_data_response = client.get(AUTH_EXPORT_USER_DATA_PREFIX)

        assert export_user_data_response.status_code == status.HTTP_200_OK

        # Validate gzip header (first two bytes should be 0x1f, 0x8b)
        compressed = export_user_data_response.content
        assert compressed[:2] == b"\x1f\x8b"

        # We should be able to load the decompressed file without an error.
        decompressed = gzip.decompress(compressed)
        json.loads(decompressed)


    def test_export_user_data_does_not_include_other_users_data(
        self,
        client,
        refresh_token_bundle_for_test_user,
        create_test_user,
        create_test_db
    ):
        user = refresh_token_bundle_for_test_user["user"]
        refresh_token_hash = refresh_token_bundle_for_test_user["hashed"]
        user.last_login = datetime.now(timezone.utc)
        create_test_db.commit()

        client.cookies.set("access_token", create_access_token(str(user.id), True))

        # Create another user, session, and tea notes
        other_user = create_test_user(
            email = "otherUser@somedomain.com",
            password = "OtherPassword@123",
            display_name = "Other User",
            is_verified = True
        )

        other_session = SessionTokenModel(
            user_id = other_user.id,
            refresh_token_hash = "other_hash",
            refresh_token_id = uuid.uuid4(),
            created_at = datetime.now(timezone.utc),
            expires_at = datetime.now(timezone.utc) + timedelta(days = 30),
        )
        create_test_db.add(other_session)
        create_test_db.commit()

        export_response = client.get(AUTH_EXPORT_USER_DATA_PREFIX)

        decompressed = gzip.decompress(export_response.content)
        data = json.loads(decompressed)

        # The user id should not be that of the other user we created and their
        # sessions should be different.
        assert str(other_user.id) != data["user"]["id"]
        assert all(s["id"] != str(other_session.id) for s in data["session_tokens"])

        # Confirm the test user's session is present.
        user_session_after_export = create_test_db.query(SessionTokenModel).filter_by(
            refresh_token_hash = refresh_token_hash
        ).first()
        assert any(s["id"] == str(user_session_after_export.id) for s in data["session_tokens"])


# ---------------------------------------------------------
# DELETE USER DATA
# ---------------------------------------------------------

class TestAuthDeleteUserData:

    def test_delete_user_data_success(
        self,
        client,
        refresh_token_bundle_for_test_user,
        create_test_db,
        user_tea_profile_notes_repo,
        empty_user_tea_profile_notes_inbound,
        long_jing_tea_profile_id
    ):
        user = refresh_token_bundle_for_test_user["user"]

        # Simulate a fresh login.
        user.last_login = datetime.now(timezone.utc)
        create_test_db.commit()

        # Create some user-generated data.
        user_tea_profile_notes_repo.create(
            user_id = user.id,
            tea_profile_id = long_jing_tea_profile_id,
            inbound_schema = empty_user_tea_profile_notes_inbound
        )

        # Authenticate the user.
        client.cookies.set("access_token", create_access_token(str(user.id), True))

        delete_user_data_response = client.delete(AUTH_DELETE_USER_DATA_PREFIX)

        assert delete_user_data_response.status_code == status.HTTP_204_NO_CONTENT

        # Verify that user-generated data was deleted.
        user_tea_profile_notes = user_tea_profile_notes_repo.get_by_user_id(user.id)
        assert user_tea_profile_notes == []

        # Verify the user account still exists.
        user = create_test_db.get(UserInternalModel, user.id)
        assert user is not None

        # Verify that a DSAR log was created and fulfilled.
        dsar_logs = create_test_db.query(DSARLogModel).filter_by(user_id = user.id).all()

        assert len(dsar_logs) == 1
        assert dsar_logs[0].request_type == DSAR_REQUEST_DELETE_USER_DATA
        assert dsar_logs[0].status == DSAR_STATUS_FULFILLED
        assert dsar_logs[0].fulfilled_at is not None


    def test_delete_user_data_fails_if_no_access_token(
        self, 
        client,
        create_test_user,
        create_test_db
    ):
        user = create_test_user()

        delete_user_data_response = client.delete(AUTH_DELETE_USER_DATA_PREFIX)

        assert delete_user_data_response.status_code == status.HTTP_401_UNAUTHORIZED

        # No DSAR log should be created.
        dsar_logs = create_test_db.query(DSARLogModel).filter_by(user_id = user.id).all()
        assert dsar_logs == []


    def test_delete_user_data_marks_dsar_failed_on_exception(
        self,
        client,
        refresh_token_bundle_for_test_user,
        create_test_db,
        user_tea_profile_notes_repo,
        empty_user_tea_profile_notes_inbound,
        long_jing_tea_profile_id,
        monkeypatch
    ):
        user = refresh_token_bundle_for_test_user["user"]

        user.last_login = datetime.now(timezone.utc)

        user_tea_profile_notes_repo.create(
            user_id = user.id,
            tea_profile_id = long_jing_tea_profile_id,
            inbound_schema = empty_user_tea_profile_notes_inbound
        )
        create_test_db.commit() 

        client.cookies.set("access_token", create_access_token(str(user.id), True))

        def delete_user_data_exception(*args, **kwargs):
            raise Exception("Failed to delete user data.")

        monkeypatch.setattr(
            UserDataDeletionService,
            "delete_user_data",
            delete_user_data_exception
        )

        delete_user_data_response = client.delete(AUTH_DELETE_USER_DATA_PREFIX)

        assert delete_user_data_response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

        # Verify DSAR log marked FAILED.
        dsar_logs = create_test_db.query(DSARLogModel).filter_by(user_id = user.id).all()

        assert len(dsar_logs) == 1
        assert dsar_logs[0].status == DSAR_STATUS_FAILED
        assert dsar_logs[0].notes == "Failed to delete user data."
        assert dsar_logs[0].fulfilled_at is None

        # Verify that user-generated data was not deleted.
        user_tea_profile_notes = user_tea_profile_notes_repo.get_by_user_id(user.id)
        assert user_tea_profile_notes != []


# ---------------------------------------------------------
# DELETE USER ACCOUNT
# ---------------------------------------------------------

class TestAuthDeleteUserAccount:

    def test_delete_user_account_success(
        self,
        client,
        refresh_token_bundle_for_test_user,
        create_test_db,
        user_tea_profile_notes_repo,
        long_jing_tea_profile_id,
        empty_user_tea_profile_notes_inbound,
    ):
        user = refresh_token_bundle_for_test_user["user"]
        user_id = user.id

        # Simulate a fresh login.
        user.last_login = datetime.now(timezone.utc)
        create_test_db.commit()

        # Create some user-generated data.
        user_tea_profile_notes_repo.create(
            user_id = user_id,
            tea_profile_id = long_jing_tea_profile_id,
            inbound_schema = empty_user_tea_profile_notes_inbound
        )

        # Authenticate the user.
        client.cookies.set("access_token", create_access_token(str(user_id), True))

        # Confirm password first.
        confirm_payload = { "password": "MyPassword@123" }
        confirm_response = client.post(AUTH_CONFIRM_PASSWORD_PREFIX, json = confirm_payload)
        assert confirm_response.status_code == status.HTTP_204_NO_CONTENT

        delete_user_account_response = client.delete(AUTH_DELETE_USER_ACCOUNT_PREFIX)
        assert delete_user_account_response.status_code == status.HTTP_204_NO_CONTENT

        # Verify user-generated data was deleted.
        user_tea_profile_notes = user_tea_profile_notes_repo.get_by_user_id(user_id)
        assert user_tea_profile_notes == []

        # Verify the user account was deleted.
        user = create_test_db.get(UserInternalModel, user_id)
        assert user is None

        # There should be no dsar logs, since they cascade on delete with the user_id.
        dsar_logs = create_test_db.query(DSARLogModel).filter_by(user_id = user_id).all()
        assert len(dsar_logs) == 0


    def test_delete_user_account_fails_if_no_access_token(
        self, 
        client,
        create_test_user,
        create_test_db
    ):
        user = create_test_user()

        delete_user_account_response = client.delete(AUTH_DELETE_USER_ACCOUNT_PREFIX)

        assert delete_user_account_response.status_code == status.HTTP_401_UNAUTHORIZED

        # No DSAR log should be created.
        dsar_logs = create_test_db.query(DSARLogModel).filter_by(user_id = user.id).all()
        assert dsar_logs == []


    def test_delete_user_account_marks_dsar_failed_on_exception(
        self,
        client,
        refresh_token_bundle_for_test_user,
        create_test_db,
        user_tea_profile_notes_repo,
        empty_user_tea_profile_notes_inbound,
        long_jing_tea_profile_id,
        monkeypatch
    ):
        user = refresh_token_bundle_for_test_user["user"]
        user_id = user.id

        user.last_login = datetime.now(timezone.utc)
        
        user_tea_profile_notes_repo.create(
            user_id = user_id,
            tea_profile_id = long_jing_tea_profile_id,
            inbound_schema = empty_user_tea_profile_notes_inbound
        )
        create_test_db.commit()

        client.cookies.set("access_token", create_access_token(str(user_id), True))

        def delete_user_account_exception(*args, **kwargs):
            raise Exception("Failed to delete user account.")

        # Confirm password first.
        client.post(
            AUTH_CONFIRM_PASSWORD_PREFIX,
            json = {"password": "MyPassword@123"}
        )

        monkeypatch.setattr(
            UserAccountDeletionService,
            "delete_user_account",
            delete_user_account_exception
        )

        delete_user_account_response = client.delete(AUTH_DELETE_USER_ACCOUNT_PREFIX)

        assert delete_user_account_response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

        # Verify DSAR log marked FAILED.
        dsar_logs = create_test_db.query(DSARLogModel).filter_by(user_id = user_id).all()

        assert len(dsar_logs) == 1
        assert dsar_logs[0].status == DSAR_STATUS_FAILED
        assert dsar_logs[0].notes == "Failed to delete user account."
        assert dsar_logs[0].fulfilled_at is None

        # Verify that the user account was not deleted.
        user = create_test_db.get(UserInternalModel, user_id)
        assert user is not None

        # Verify that user-generated data was not deleted either.
        user_tea_profile_notes = user_tea_profile_notes_repo.get_by_user_id(user_id)
        assert user_tea_profile_notes != []


    def test_delete_user_account_requires_password_confirmation(
        self,
        client,
        refresh_token_bundle_for_test_user,
        create_test_db
    ):
        user = refresh_token_bundle_for_test_user["user"]
        user_id = user.id

        # Simulate a fresh login.
        user.last_login = datetime.now(timezone.utc)
        create_test_db.commit()

        # Authenticate.
        client.cookies.set("access_token", create_access_token(str(user_id), True))

        # Try deleting the user's account without confirming their password
        delete_account_response = client.delete(AUTH_DELETE_USER_ACCOUNT_PREFIX)

        # It should fail.
        assert delete_account_response.status_code == status.HTTP_403_FORBIDDEN
        assert delete_account_response.json()["detail"] == "Password confirmation required."

        # User should still exist.
        assert create_test_db.get(UserInternalModel, user_id) is not None


    def test_delete_user_account_success_after_confirmation(
        self,
        client,
        refresh_token_bundle_for_test_user,
        create_test_db,
        user_tea_profile_notes_repo,
        long_jing_tea_profile_id,
        empty_user_tea_profile_notes_inbound,
    ):
        user = refresh_token_bundle_for_test_user["user"]
        user_id = user.id

        # Simulate a fresh login.
        user.last_login = datetime.now(timezone.utc)
        create_test_db.commit()

        # Create some user-generated data.
        user_tea_profile_notes_repo.create(
            user_id = user_id,
            tea_profile_id = long_jing_tea_profile_id,
            inbound_schema = empty_user_tea_profile_notes_inbound
        )
        create_test_db.commit()

        # Authenticate.
        client.cookies.set("access_token", create_access_token(str(user_id), True))

        # Confirm password.
        confirm_payload = { "password": "MyPassword@123" }
        confirm_response = client.post(AUTH_CONFIRM_PASSWORD_PREFIX, json = confirm_payload)
        assert confirm_response.status_code == status.HTTP_204_NO_CONTENT

        # Delete account.
        delete_account_response = client.delete(AUTH_DELETE_USER_ACCOUNT_PREFIX)
        assert delete_account_response.status_code == status.HTTP_204_NO_CONTENT

        create_test_db.expire_all()

        # User should be deleted.
        assert create_test_db.get(UserInternalModel, user_id) is None

        # Notes should be deleted.
        assert user_tea_profile_notes_repo.get_by_user_id(user_id) == []

        # DSAR logs should be gone.
        dsar_logs = create_test_db.query(DSARLogModel).filter_by(user_id = user_id).all()
        assert dsar_logs == []


# ---------------------------------------------------------
# PASSWORD CONFIRMATION
# ---------------------------------------------------------

class TestAuthPasswordConfirmation:

    def test_confirm_password_success(
        self,
        client,
        create_test_db,
        create_test_user,
    ):
        user = create_test_user() 

        # Simulate a fresh login.
        user.last_login = datetime.now(timezone.utc)
        create_test_db.commit()

        # Authenticate user.
        client.cookies.set("access_token", create_access_token(str(user.id), True))

        confirm_password_payload = { "password": "MyPassword@123" }

        confirm_password_response = client.post(
            AUTH_CONFIRM_PASSWORD_PREFIX, json = confirm_password_payload
        )

        assert confirm_password_response.status_code == status.HTTP_204_NO_CONTENT

        # Force SQLAlchemy to reload fresh state.
        create_test_db.expire_all()

        # One confirmation should exist.
        confirmations = (
            create_test_db.query(PasswordConfirmationModel)
            .filter_by(user_id = user.id)
            .all()
        )
        assert len(confirmations) == 1


    def test_confirm_password_invalid_password(
        self,
        client,
        create_test_db,
        create_test_user,
    ):
        user = create_test_user()

        # Simulate a fresh login.
        user.last_login = datetime.now(timezone.utc)
        create_test_db.commit()

        client.cookies.set("access_token", create_access_token(str(user.id), True))

        confirm_password_payload = { "password": "WrongPassword@123" }

        confirm_password_response = client.post(
            AUTH_CONFIRM_PASSWORD_PREFIX, 
            json = confirm_password_payload
        )

        assert confirm_password_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert confirm_password_response.json()["detail"] == "Invalid password."

        create_test_db.expire_all()

        # No confirmation should be created.
        assert (
            create_test_db.query(PasswordConfirmationModel)
            .filter_by(user_id = user.id)
            .count()
            == 0
        )

