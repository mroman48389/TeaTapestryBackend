from fastapi.testclient import TestClient
import sys
import os

from src.app.main import app

sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..")))

# FastAPI provides the TestClient helper for simulating HTTP requests without
# running a server. It's like a mock browser.
client = TestClient(app)

def test_lifespan():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        
def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Tea Tapestry backend is alive!"}

def test_get_version():
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json() == {"version": "1.0.0"}

