import sentry_sdk
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
from fastapi import Request, FastAPI

# Now doing on each route.
# Set up global rate limit The function name is not important. We'll get a 
# bucket with 100 tokens that refills at 100 tokens per minute. Bursts of 
# up to 100 are allowed.
# @app.middleware("http")
# @rate_limiter.limit(GLOBAL_RATE_LIMIT)
# async def global_rate_limit(request, call_next):
#     return await call_next(request)

def register_rate_limit_handlers(app: FastAPI):
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        # Sentry will tell us about endpoints that are hits too often and the
        # abusive IPs. It will help us gauge if our endpoints are too strict as
        # well.
        sentry_sdk.capture_message(
            f"Rate limit exceeded for {request.url.path}",
            level="warning"
        )

        return JSONResponse(
            status_code = 429,
            content={
                "error": {
                    "type": "RateLimitExceeded",
                    "message": "Too many requests",
                    "details": None,
                    "status": 429,
                    "path": request.url.path,
                }
            },
        )
