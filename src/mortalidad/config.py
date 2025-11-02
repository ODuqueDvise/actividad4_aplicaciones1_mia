"""Configuration management using Pydantic Settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or `.env`."""

    env: str = "development"
    port: int = 8050
    cache_timeout: int = 300
    mapbox_token: str | None = None
    data_dir: Path = Path("data/raw")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False,
    )

    @field_validator("env")
    @classmethod
    def _validate_env(cls, value: str) -> str:
        normalized = value.lower().strip()
        if normalized not in {"development", "dev", "production", "prod"}:
            raise ValueError("ENV debe ser 'development'/'dev' o 'production'/'prod'.")
        return normalized

    @field_validator("data_dir")
    @classmethod
    def _validate_data_dir(cls, value: Path) -> Path:
        if not value.exists():
            value.mkdir(parents=True, exist_ok=True)
        return value

    @property
    def is_development(self) -> bool:
        """Return True if the environment is development."""
        return self.env in {"development", "dev"}

    @property
    def is_production(self) -> bool:
        """Return True if the application runs in production mode."""
        return self.env in {"production", "prod"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance to avoid repeated parsing."""
    return Settings()


__all__ = ["Settings", "get_settings"]
