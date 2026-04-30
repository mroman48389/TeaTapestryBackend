import json
from starlette import status
from starlette.requests import Request

from src.api.error_handlers import _get_request_id, _error_response

def test_get_request_id_uses_header():
    scope = {"type": "http", "headers": [(b"x-request-id", b"abc123")]}
    request = Request(scope)

    assert _get_request_id(request) == "abc123"

def test_error_response_structure():
    scope = {"type": "http", "path": "/test", "headers": []}
    request = Request(scope)

    response = _error_response(
        request = request,
        exc_type = "TestError",
        message = "Something went wrong",
        status_code = status.HTTP_400_BAD_REQUEST,
        details={"key": "value"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = json.loads(response.body)

    err = data["error"]
    assert err["type"] == "TestError"
    assert err["message"] == "Something went wrong"
    assert err["status"] == status.HTTP_400_BAD_REQUEST
    assert err["path"] == "/test"
    assert err["details"] == {"key": "value"}
    assert "request_id" in err
    assert "timestamp" in err
