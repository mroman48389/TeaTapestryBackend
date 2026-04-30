# This MUST be first. DO NOT REMOVE. The end-of-line comment will prevent 
# fix.ps1 from removing this line.
import src.app.env_loader # noqa: F401

import os 
# Use FastAPI framework to get decorators like @app.get, routing, validation,
# and docs.
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import sentry_sdk
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse

from .logging_config import configure_logging
from .rate_limit import rate_limiter, HIGH_RATE_LIMIT
from src.db.base import Base
from src.api.routers.debug_router import router as debug_router
from src.api.routers.tea_profiles_router import router as tea_profiles_router
from src.api.error_handlers import register_exception_handlers

###############################################################################
##############################   Configuration   ##############################
###############################################################################

# Check to see if we're doing testing (set in conftest.py) 
IS_TEST = os.environ.get("PYTEST_RUNNING") == "1" #

ENV = os.getenv("ENV", "development")

# dsn: Where to send events.
#
# integrations: Instrument SQLAlchemy so we can see DB queries in traces and
#     breadbrumbs. FastAPI is done automatically now.
#
# send_default_pii: Set to false so we don't send personally identifiable information
#     like IP addresses, cookies, user identifiers, request headers.
#
# traces_sample_rate: Control performance tracing where 0.0 = disabled and 
#     1.0 = capture all traces.
sentry_sdk.init(
    dsn = os.getenv("SENTRY_DSN"), # where to send events
    integrations = [
        SqlalchemyIntegration(),
    ],
    send_default_pii = False,
    traces_sample_rate = 0.0,  # will adjust  later
    enable_metrics = True,      # Lets us do metric.incr, .set
)

configure_logging()

###############################################################################
##############################   Create App   #################################
###############################################################################

@asynccontextmanager
async def lifespan(app: FastAPI):
    # This code runs before the app starts:

    # Create tables for all models that inherit from Base
    # if they don't exist yet. Only needs to run once.
    if not IS_TEST: 
        from src.db.engine import engine
        Base.metadata.create_all(bind = engine)

    # Tell FastAPI that startup is Continues startup
    yield

    ###################################################

    # This code runs on shutdown, if needed:

# Create instance of FastAPI. All routes, middleware, and configurations will
# flow through this.
app = FastAPI(lifespan = lifespan)

###############################################################################
#################################   CORS   ####################################
###############################################################################

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["http://localhost:5173"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
    expose_headers=["ETag", "Last-Modified"],  # important for caching
)

###############################################################################
#################################   GZip   ####################################
###############################################################################

# Optimization: Compress HTTP responses before sending them to the browser.
# This will increase load times because our JSON has a lot of repetitive fields.
# Reduces bandwidth usage, which will help with free hosting tiers, bandwidth
# limits, scaling, and rate-limiting synergy.
#
# These needs to go after CORS but before routes
#
# Small responses don't benefit from compression and waste CPU, so start 
# compressing if the payload is 500 B or larger.
app.add_middleware(GZipMiddleware, minimum_size = 500)

###############################################################################
#################################   Exceptions   ##############################
###############################################################################

register_exception_handlers(app)

###############################################################################
##############################   Route Registration   #########################
###############################################################################

# Register routes to pick them up with testing. This must be done before defining
# the global rate limiter so the per route decorators wrap the handler first.

if ENV == "development":
    app.include_router(debug_router)

app.include_router(tea_profiles_router)

###############################################################################
##############################   Rate Limiting   ##############################
###############################################################################

# SlowAPIMiddleware always uses Token Bucket rate limiting. It's a wrapper
# around the limits library, which is what actually implements Token Bucket.
# SlowAPIMiddleware attaches the limiter to the app, intercepts requests,
# checks IPs/users, asks the limiter if the request is allowed, adds rate-limit
# headers, and raises RateLimitExceeded if needed.
#
# Why did we choose Token Bucket? The industry standard. It allows bursts and
# feels natural. It's fair to users and good for social features. 
# 
# Reminder of how it works: Each client receives a "bucket" that holds a fixed 
# number of tokens. Every request consumes one token. Tokens refill at a steady 
# rate over time. If the bucket has tokens, the request is allowed, permitting 
# short bursts. If the bucket is empty, the request is rejected until enough 
# tokens refill. 
app.state.limiter = rate_limiter
app.add_middleware(SlowAPIMiddleware)

# Now doing on each route.
# Set up global rate limit The function name is not important. We'll get a 
# bucket with 100 tokens that refills at 100 tokens per minute. Bursts of 
# up to 100 are allowed.
# @app.middleware("http")
# @rate_limiter.limit(GLOBAL_RATE_LIMIT)
# async def global_rate_limit(request, call_next):
#     return await call_next(request)

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

###############################################################################
##################################   Routes   #################################
###############################################################################

# Simple, inline routes.

# Define GET endpoint, telling FastAPI to respond to HTTP GET requests at the
# root URL. async "root" function allows us to handle concurrent requests
# efficiently.
#
# To test, make sure you're in the virtual environment (venv) first by doing
#     .\venv\Scripts\Activate.ps1
# in the project directory. Then do
#     python -m uvicorn main:app --reload
# to run the server on port 8000. http://127.0.0.1:8000 will show the message
# we're returning,and http://127.0.0.1:8000/docs will have FastAPI's
# auto-generated Swagger UI to explore and test endpoints. Note that http is
# perfect locally because https requires certificates and encryption that are
# not necessary for local testing. There is no data traveling over the
# internet locally, so there is no risk of interception. 127.0.0.1 is a
# loopback address (localhost), a special IP address that always point to one's
# local machine. You can replace the number in the following URL with
# "localhost".

@app.get("/")
@rate_limiter.limit(HIGH_RATE_LIMIT)
async def root(request: Request):
    # Return simple message as a JSON response to confirm server is running.
    return {"message": "Tea Tapestry backend is alive!"}

@app.get("/version")
@rate_limiter.limit(HIGH_RATE_LIMIT)
async def get_version(request: Request):
    # Format: major.minor.patch, where major = breaking changes that affect
    # backwards compatibility, minor = new features, changes that are
    # backward compatible, patch = bug fixes with no breaking changes
    return {"version": "1.0.0"}