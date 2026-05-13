import os
from src.core.config.local_config import LocalConfig
from src.core.config.staging_config import StagingConfig
from src.core.config.preview_config import PreviewConfig
from src.core.config.production_config import ProductionConfig

# This file allows us to do from core.config import settings to load the correct environment.
# get_settings selects the correct configuration class based on the ENVIRONMENT
# variable and returns a fully‑initialized settings object. This allows the
# application to load environment‑specific settings (local, staging, preview,
# production) without the rest of the code needing to know which environment
# it is running in. Importing `settings` from this package will always give the
# correct configuration for the current environment.

def get_settings():
    env = os.getenv("ENVIRONMENT", "local")

    if env == "production":
        return ProductionConfig() # pyright: ignore[reportCallIssue]
    
    if env == "staging":
        return StagingConfig() # pyright: ignore[reportCallIssue]
    
    if env == "preview":
        return PreviewConfig() # pyright: ignore[reportCallIssue]
    
    return LocalConfig() # pyright: ignore[reportCallIssue]

settings = get_settings()
