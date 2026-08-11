from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List, Optional

class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=None)

    environment: str = Field("local", alias="ENVIRONMENT")

    # Database
    database_url: str = Field(..., alias="DATABASE_URL")

    # Auth
    access_token_secret: str = Field(..., alias="ACCESS_TOKEN_SECRET")
    access_token_algorithm: str = Field("HS256", alias="ACCESS_TOKEN_ALGORITHM")
    access_token_expires_in: int = Field(3600, alias="ACCESS_TOKEN_EXPIRES_IN")

    refresh_token_secret: str = Field(..., alias="REFRESH_TOKEN_SECRET")
    refresh_token_algorithm: str = Field("HS256", alias="REFRESH_TOKEN_ALGORITHM")

    # CORS
    cors_origins: List[str] = Field(default_factory=list, alias="CORS_ORIGINS")

    # Sentry
    sentry_dsn: Optional[str] = Field(None, alias="SENTRY_DSN")

    # Rate limiting
    rate_limit: str = Field("100/minute", alias="RATE_LIMIT")

    # Cache
    cache_url: Optional[str] = Field(None, alias="CACHE_URL")

    # Logging
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    # API
    api_base_url: Optional[str] = Field(None, alias="API_BASE_URL")

    # Supabase
    supabase_url: Optional[str] = Field(None, alias="SUPABASE_URL")
    supabase_service_role_key: Optional[str] = Field(None, alias="SUPABASE_SERVICE_ROLE_KEY")