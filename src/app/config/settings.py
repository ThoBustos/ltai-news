"""Application settings and configuration."""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import BaseModel, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App Configuration
    app_name: str = Field(default="LTAI News", alias="APP_NAME")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Channel Tracking Configuration
    # Store as string to avoid pydantic-settings JSON parsing issues
    tracked_channels_raw: Optional[str] = Field(
        default=None,
        alias="TRACKED_CHANNELS",
        description="Comma-separated list of channel names/handles to track (raw string)",
        exclude=True,  # Don't include in serialization
    )
    content_lookback_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Number of hours to look back for content (1-168 hours)",
        alias="CONTENT_LOOKBACK_HOURS",
    )

    # YouTube API Configuration
    google_credentials_json_path: str = Field(
        ..., alias="GOOGLE_CREDENTIALS_JSON_PATH"
    )
    google_token_file: str = Field(
        default=".tokens/token.json", alias="GOOGLE_TOKEN_FILE"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        case_sensitive=False,
        env_ignore_empty=True,  # Ignore empty env vars
        extra="ignore",  # Ignore extra fields from .env file
    )

    @computed_field
    @property
    def tracked_channels(self) -> List[str]:
        """Parse TRACKED_CHANNELS from comma-separated string."""
        if self.tracked_channels_raw is None or not self.tracked_channels_raw.strip():
            return []
        # Split by comma and strip whitespace
        channels = [
            ch.strip() for ch in self.tracked_channels_raw.split(",") if ch.strip()
        ]
        return channels

    @staticmethod
    def parse_tracked_channels(value) -> List[str]:
        """Utility method to parse tracked channels (for testing)."""
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [ch.strip() for ch in value.split(",") if ch.strip()]
        if isinstance(value, list):
            return value
        return []


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

