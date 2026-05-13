from typing import ClassVar
from pydantic_settings import SettingsConfigDict

from src.core.config.base_config import BaseConfig

class ProductionConfig(BaseConfig):
    model_config: SettingsConfigDict = {"extra": "ignore"}

    cors_origins: ClassVar[list[str]] = ["https://teatapestry.com"]
    log_level: ClassVar[str] = "WARNING"
