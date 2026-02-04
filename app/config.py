from __future__ import annotations

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    env: str = Field(default="development", alias="ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    api_auth_token: str | None = Field(default=None, alias="API_AUTH_TOKEN")

    # Database
    database_url: str = Field(default="sqlite:///./app.db", alias="DATABASE_URL")

    # Gemini (Twitter content generation)
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL")

    # Composio (Twitter publishing)
    composio_api_key: str | None = Field(default=None, alias="COMPOSIO_API_KEY")
    composio_user_id: str = Field(default="default", alias="COMPOSIO_USER_ID")

    # Scheduling defaults
    default_timezone: str = Field(default="UTC", alias="DEFAULT_TIMEZONE")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

