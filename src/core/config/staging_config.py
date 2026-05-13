from typing import ClassVar
from pydantic_settings import SettingsConfigDict

from src.core.config.base_config import BaseConfig

class StagingConfig(BaseConfig): 
    model_config: SettingsConfigDict = {"extra": "ignore"}
    
    cors_origins: ClassVar[list[str]] = ["https://staging.teatapestry.com"]
    log_level: ClassVar[str] = "INFO"
