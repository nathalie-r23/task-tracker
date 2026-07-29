"""Application configuration.

Loads settings from environment variables (and a local .env file if
present) using pydantic-settings. This keeps PORT and APP_ENV in one
typed place instead of scattered os.getenv calls.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven application settings."""

    PORT: int = 8000
    APP_ENV: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Import this shared instance wherever config is needed.
settings = Settings()