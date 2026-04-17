from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="MCP Server", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_port: int = Field(default=8000, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    project_service_url: str = Field(default="http://project-service:8001", alias="PROJECT_SERVICE_URL")
    slack_service_url: str = Field(default="http://slack-service:8002", alias="SLACK_SERVICE_URL")
    http_timeout: float = Field(default=10.0, alias="HTTP_TIMEOUT")
    allowed_origins: str = Field(default="http://localhost:5173", alias="ALLOWED_ORIGINS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
