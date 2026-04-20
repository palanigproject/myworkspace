from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="MCP Server", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_port: int = Field(default=8000, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    chat_api_url: str = Field(
        default="https://chatbotinsightsdev.ckdigital.in/api/chat",
        alias="CHAT_API_URL",
    )
    chat_api_bearer_token: str = Field(default="dummy-bearer-token", alias="CHAT_API_BEARER_TOKEN")
    http_timeout: float = Field(default=30.0, alias="HTTP_TIMEOUT")
    allowed_origins: str = Field(default="http://localhost:5173", alias="ALLOWED_ORIGINS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
