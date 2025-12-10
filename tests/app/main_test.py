# from fastapi.testclient import TestClient
# from fastapi.routing import APIRoute
# import pytest
import sys
import os

# from src.app.main import app
# from tests.utils.test_utils import get_path_with_dummy_params

sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..")))

# FastAPI provides the TestClient helper for simulating HTTP requests without
# running a server. It's like a mock browser.
# client = TestClient(app)

# # Build a list of all registered Route objects.
# @pytest.mark.parametrize(
#     "route", 
#     [r for r in app.routes if isinstance(r, APIRoute)]
# )
# def test_all_routes_have_coverage(route: APIRoute):
#     for method in route.methods:
#         if method in {"GET", "POST", "PUT", "DELETE"}:
#             # Add dummy values to routes with dynamic parameters. We only care that
#             # some test was written for each route, not that it works or not. We just
#             # need the routes to be callable without breaking for that.
#             path = get_path_with_dummy_params(route)

#             if method == "GET":
#                 response = client.get(path)
#             elif method == "POST":
#                 response = client.post(path, json={})
#             elif method == "PUT":
#                 response = client.put(path, json={})
#             elif method == "DELETE":
#                 response = client.delete(path)

#             # Log the route and status code for visibility
#             print(f"{method} {path} --> {response.status_code}")

#             # Assert that the response is not a server error,  Status codes below 500 
#             # are non-server errors.
#             assert response.status_code < 500, f"{path} is not covered."

def test_lifespan(client):
    response = client.get("/")
    assert response.status_code == 200
        
def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Tea Tapestry backend is alive!"}

def test_get_version(client):
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json() == {"version": "1.0.0"}

