"""Validated environment-backed application settings."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = Field(default="Forever BIS", min_length=1, max_length=100)
    app_version: str = Field(default="0.1.0", min_length=1, max_length=30)
    app_env: str = Field(default="development", min_length=1, max_length=30)
    log_level: str = Field(default="INFO", min_length=1, max_length=10)
    database_url: str = Field(
        default="postgresql+psycopg://foreverbis:local_dev_password_change_me@localhost:5432/foreverbis",
        min_length=1,
    )
    api_cors_origins: str = Field(default="http://localhost:5173", min_length=1)

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use the postgresql+psycopg driver")
        return value

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
            raise ValueError("LOG_LEVEL must be CRITICAL, ERROR, WARNING, INFO, or DEBUG")
        return normalized

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
