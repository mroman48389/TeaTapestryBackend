from typing import ClassVar
from pydantic_settings import SettingsConfigDict

from src.core.config.base_config import BaseConfig

class LocalConfig(BaseConfig):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # 5173 = local development mode; 4173 = preview mode.
    cors_origins: ClassVar[list[str]] = [            
        "http://localhost:5173", 
        "http://127.0.0.1:5173", 
        "http://localhost:4173",
        "http://127.0.0.1:4173"
    ]