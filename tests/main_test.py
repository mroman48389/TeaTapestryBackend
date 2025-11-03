from fastapi.testclient import TestClient
from app.main import app
import sys
import os
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..")))


# FastAPI provides the TestClient helper for simulating HTTP requests without
# running a server. It's like a mock browser.
client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Tea Tapestry backend is alive!"}
