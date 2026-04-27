import os 
# Use FastAPI framework to get decorators like @app.get, routing, validation,
# and docs.
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import sentry_sdk
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from .logging_config import configure_logging
from src.db.base import Base
from src.api.routers.tea_profiles_router import router as tea_profiles_router
from src.api.error_handlers import register_exception_handlers

# Check to see if we're doing testing (set in conftest.py) 
IS_TEST = os.environ.get("PYTEST_RUNNING") == "1" #

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
)

configure_logging()

# Create instance of FastAPI. All routes, middleware, and configurations will
# flow through this.
app = FastAPI(lifespan = lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["http://localhost:5173"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)

register_exception_handlers(app)

# Register routes to pick them up with testing.
app.include_router(tea_profiles_router)

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
async def root():
    # Return simple message as a JSON response to confirm server is running.
    return {"message": "Tea Tapestry backend is alive!"}

@app.get("/version")
def get_version():
    # Format: major.minor.patch, where major = breaking changes that affect
    # backwards compatibility, minor = new features, changes that are
    # backward compatible, patch = bug fixes with no breaking changes
    return {"version": "1.0.0"}