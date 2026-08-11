from fastapi import Response, Request

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
