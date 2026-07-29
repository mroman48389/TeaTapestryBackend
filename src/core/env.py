import os

# The application's environment is determined by 
#
#     src/core/config/__init__.py
#
# which uses Pydantic settings to read the ENVIRONMENT variable and load the correct
# configuration class (LocalConfig, StagingConfig, PreviewConfig, ProductionConfig);
# If ENVIRONMENT is not set, it defaults to "local". Any module that has
#
#     from src.core.config import settings
#
# receives an instance of the selected configuration class. Since all configuration classes 
# inherit from BaseConfig, they all expose the ENVIRONMENT value through the "environment" 
# field (aliased from ENVIRONMENT).
#
# This module mirrors the ENVIRONMENT variable and provides convenient
# boolean flags (IS_LOCAL_ENV, IS_STAGING_ENV, etc.) so the rest of the codebase
# can avoid repeating string comparisons like 
# 
#     os.getenv("ENVIRONMENT") == "local". 
# 
# It centralizes environment variable checks in one place.
#
# To summarize, Pydantic settings determines the environment, and this module exposes 
# easy-to-use flags based on that environment.

ENV_LOCAL = "local"
ENV_STAGING = "staging"
ENV_PREVIEW = "preview"
ENV_PRODUCTION = "production"

ENVIRONMENT = os.getenv("ENVIRONMENT", ENV_LOCAL)

# Convenience flags
IS_LOCAL_ENV = ENVIRONMENT == ENV_LOCAL
IS_STAGING_ENV = ENVIRONMENT == ENV_STAGING
IS_PREVIEW_ENV = ENVIRONMENT == ENV_PREVIEW
IS_PRODUCTION_ENV = ENVIRONMENT == ENV_PRODUCTION

# Ignore rate limiting for all standard testing via Pytest. Set in conftest.py.
IS_RUNNING_TESTS = os.getenv("PYTEST_RUNNING", "false").lower() == "true"

# DEV_RATE_LIMIT only gets set in the test_rate_limiting.ps1 script, so default to false.
USE_DEV_RATE_LIMIT = os.getenv("DEV_RATE_LIMIT", "false").lower() == "true"
