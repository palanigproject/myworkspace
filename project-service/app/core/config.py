from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Project Service", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_port: int = Field(default=8001, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    convex_projects_url: str = Field(
        default="https://convexpro.in/waterfall/projects?option=null&statusId=null&search=&pageNo=0&pageSize=200&column=&value=",
        alias="CONVEX_PROJECTS_URL",
    )
    convex_bearer_token: str = Field(default="", alias="CONVEX_BEARER_TOKEN")
    http_timeout: float = Field(default=12.0, alias="HTTP_TIMEOUT")


@lru_cache
def get_settings() -> Settings:
    return Settings()
