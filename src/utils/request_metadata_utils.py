from fastapi import Request

# Functions below get various metadata from request headers.

def get_client_ip(request: Request) -> str | None:
    # IP address depends on if the app is behind a reverse
    # proxy, load balancer, CDN, hosting platform like Fly.io,
    # Cloudflare, etc. This header only exists when the app is 
    # behind a proxy, so check to see if it's there.
    forwarded = request.headers.get("X-Forwarded-For")

    # If it is, it will look something like:
    #
    #    X-Forwarded-For: 73.42.118.201, 10.0.0.1
    #
    # We want the first part (the real client IP address). The 
    # second part is the proxy IP.
    if forwarded:
        return forwarded.split(",")[0].strip()

    # Otherwise, fall back to FastAPI's built-in client tuple, which
    # will look something like:
    #
    #     request.client = ("127.0.0.1", 54321)
    #
    # where index 0 is the IP address and index 1 is the port.
    return request.client[0] if request.client else None

def get_user_agent(request: Request) -> str | None:
    # The browser automatically includes user agent info as
    # part of the header. Useful for session tracking, device
    # identification, secruity audits, logout-everywhere, user data export,
    # active sessions, etc.
    # 
    # It will look something like:
    #     User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...
    return request.headers.get("user-agent")
