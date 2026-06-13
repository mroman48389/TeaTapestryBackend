from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

from src.core.config import settings

def configure_cors(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins = settings.cors_origins,
        allow_credentials = True,
        allow_methods = ["*"],
        allow_headers = ["*"],
        expose_headers=["ETag", "Last-Modified"],  # important for caching
    )