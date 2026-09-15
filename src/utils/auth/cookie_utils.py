from fastapi import Response, Request

from src.constants.jwt_constants import (
    ACCESS_TOKEN_LIFETIME_SECONDS, 
    REFRESH_TOKEN_LIFETIME_SECONDS
)
from src.constants.cookie_constants import SAME_SITE_VALUE

def delete_auth_token_cookies(request: Request, response: Response) -> None:
    # Determine cookie security based on environment. Allows us to ignore
    # secure cookies, which do not work over http (we run locally over http and
    # production over https).
    hostname = request.url.hostname
    is_local = hostname in ("localhost", "127.0.0.1", "testserver")

    # Delete refresh and access token cookies.

    response.delete_cookie(
        key = "refresh_token",
        path = "/",
        secure = not is_local,
        samesite = "lax"
    )
    
    response.delete_cookie(
        key = "access_token",
        path = "/",
        secure = not is_local,
        samesite = "lax"
    )

def set_auth_token_cookies(
    request: Request, 
    response: Response,
    raw_refresh_token: str,
    access_token: str
) -> None:
    # Determine cookie security based on environment. Allows us to ignore
    # secure cookies, which do not work over http (we run locally over http and
    # production over https).
    hostname = request.url.hostname
    is_local = hostname in ("localhost", "127.0.0.1", "testserver")

    response.set_cookie(
        key = "refresh_token",
        value = raw_refresh_token,
        httponly = True,
        secure = not is_local,
        samesite = SAME_SITE_VALUE,
        path = "/",
        max_age = REFRESH_TOKEN_LIFETIME_SECONDS
    )

    response.set_cookie(
        key = "access_token",
        value = access_token,
        httponly = True,
        secure = not is_local,
        samesite = SAME_SITE_VALUE,
        path = "/",
        max_age = ACCESS_TOKEN_LIFETIME_SECONDS
    )