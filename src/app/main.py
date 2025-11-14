# Use FastAPI framework to get decorators like @app.get, routing, validation,
# and docs.
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from src.db.base import Base, engine
from src.seed.seed_tea_profiles import seed_tea_profiles
from db.models.tea_profiles_model import TeaProfile
from constants.tea_profiles_constants import REQUIRED_TEA_PROFILE_FIELDS
from ingest.ingest import ingest_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    # This code runs before the app starts:

    # Create tables for all models that inherit from Base 
    # if they don't exist yet. Only needs to run once.
    Base.metadata.create_all(bind=engine)

    seed_tea_profiles()
    ingest_data("data/ingestion/new_teas.csv", TeaProfile, REQUIRED_TEA_PROFILE_FIELDS, ["name"])

    # Tell FastAPI that startup is Continues startup
    yield

    ###################################################

    # This code runs on shutdown, if needed:

# Create instance of FastAPI. All routes, middleware, and configurations will
# flow through this.
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
