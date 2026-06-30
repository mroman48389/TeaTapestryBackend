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
    assert response.json()["message"].startswith("Login successful")


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