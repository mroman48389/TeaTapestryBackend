from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

def configure_cors(app: FastAPI):
    # 5173 = development mode; 4173 = preview mode.
    app.add_middleware(
        CORSMiddleware,
        allow_origins = [
            "http://localhost:5173", 
            "http://127.0.0.1:5173", 
            "http://localhost:4173",
            "http://127.0.0.1:4173",
            "https://tea-tapestry.netlify.app"],
        allow_credentials = True,
        allow_methods = ["*"],
        allow_headers = ["*"],
        expose_headers=["ETag", "Last-Modified"],  # important for caching
    )