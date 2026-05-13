from pydantic_settings import SettingsConfigDict

from src.core.config.base_config import BaseConfig

class LocalConfig(BaseConfig):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
