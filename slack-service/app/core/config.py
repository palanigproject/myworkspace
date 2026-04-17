from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Slack Service", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_port: int = Field(default=8002, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    mcp_server_url: str = Field(default="http://mcp-server:8000", alias="MCP_SERVER_URL")
    slack_webhook_url: str = Field(default="", alias="SLACK_WEBHOOK_URL")
    slack_api_base_url: str = Field(default="https://slack.com/api", alias="SLACK_API_BASE_URL")
    slack_bot_token: str = Field(default="", alias="SLACK_BOT_TOKEN")
    slack_history_channel_id: str = Field(default="", alias="SLACK_HISTORY_CHANNEL_ID")
    slack_history_limit: int = Field(default=20, alias="SLACK_HISTORY_LIMIT")
    http_timeout: float = Field(default=10.0, alias="HTTP_TIMEOUT")


@lru_cache
def get_settings() -> Settings:
    return Settings()
