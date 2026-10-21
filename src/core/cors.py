from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

from src.core.config import settings

# For expose_headers, "ETag" and "Last-Modified" are important for 
# caching and "Content-Disposition" is needed to include the file name
# for the export user data endpoint.
def configure_cors(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins = settings.cors_origins,
        allow_credentials = True,
        allow_methods = ["*"],
        allow_headers = ["*"],
        expose_headers = ["ETag", "Last-Modified", "Content-Disposition"],
    )