from fastapi import Request

from src.utils.request_metadata_utils import get_client_ip

def test_get_client_ip_forwarded():
    request = Request({
        "type": "http",
        "headers": [(b"x-forwarded-for", b"73.42.118.201, 10.0.0.1")]
    })

    assert get_client_ip(request) == "73.42.118.201"

def test_get_client_ip_fallback():
    scope = {
        "type": "http",
        "client": ("127.0.0.1", 54321),
        "headers": []
    }
    request = Request(scope)
    
    assert get_client_ip(request) == "127.0.0.1"
