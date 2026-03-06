"""Application settings and configuration."""

import os
from typing import List, Optional, Any, Dict

from pydantic import BaseModel, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.logging import logger


def parse_tracked_channels(value: Any) -> List[str]:
    """Utility function to parse tracked channels."""
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [ch.strip() for ch in value.split(",") if ch.strip()]
    if isinstance(value, list):
        return [str(ch) for ch in value if ch]
    return []


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
    channel_duration_thresholds_raw: Optional[str] = Field(
        default=None,
        alias="CHANNEL_DURATION_THRESHOLDS",
        description="Comma-separated list of channel:minutes pairs (e.g., @stripe:20,@AlexHormozi:5)",
        exclude=True,
    )
    bypass_lookback_channels_raw: Optional[str] = Field(
        default=None,
        alias="BYPASS_LOOKBACK_CHANNELS",
        description="Comma-separated list of channel names/handles to bypass lookback limits",
        exclude=True,
    )
    extended_lookback_hours: int = Field(
        default=720,  # 30 days
        ge=1,
        description="Hours to look back for VIP channels",
        alias="EXTENDED_LOOKBACK_HOURS",
    )

    # Supabase Configuration
    supabase_url: str = Field(..., alias="SUPABASE_PROJECT_URL")
    supabase_key: str = Field(..., alias="SUPABASE_API_KEY")

    # YouTube API Configuration
    google_credentials_json_path: str = Field(
        ..., alias="GOOGLE_CREDENTIALS_JSON_PATH"
    )
    google_token_file: str = Field(
        default=".tokens/token.json", alias="GOOGLE_TOKEN_FILE"
    )

    # Orchestrator Configuration
    processing_batch_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of videos to process in a single batch",
        alias="PROCESSING_BATCH_SIZE",
    )
    max_retry_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of retry attempts for failed operations",
        alias="MAX_RETRY_ATTEMPTS",
    )
    processing_timeout_minutes: int = Field(
        default=30,
        ge=5,
        le=180,
        description="Timeout for processing operations in minutes",
        alias="PROCESSING_TIMEOUT_MINUTES",
    )
    default_pipeline_date: Optional[str] = Field(
        default=None,
        description="Default date for testing pipeline (YYYY-MM-DD format)",
        alias="DEFAULT_PIPELINE_DATE",
    )

    # Transcript Service Configuration
    transcript_io_api_key: Optional[str] = Field(
        default=None,
        description="API key for transcript.io service (with 'Basic ' prefix)",
        alias="TRANSCRIPT_IO_API_KEY",
    )
    transcript_io_base_url: str = Field(
        default="https://www.youtube-transcript.io/api",
        description="Base URL for transcript.io API",
        alias="TRANSCRIPT_IO_BASE_URL",
    )
    transcript_language_code: str = Field(
        default="en",
        description="Default language code for transcript extraction",
        alias="TRANSCRIPT_LANGUAGE_CODE",
    )

    # Gemini Configuration
    google_api_key: Optional[str] = Field(
        default=None,
        description="Google API key for Gemini models",
        alias="GOOGLE_API_KEY"
    )

    # Opik Configuration
    opik_api_key: Optional[str] = Field(
        default=None,
        description="Opik API key for observability and prompt management",
        alias="OPIK_API_KEY"
    )
    opik_project_name: Optional[str] = Field(
        default=None,
        description="Opik project name",
        alias="OPIK_PROJECT_NAME"
    )
    opik_workspace: Optional[str] = Field(
        default=None,
        description="Opik workspace",
        alias="OPIK_WORKSPACE"
    )

    # Video Analysis Configuration
    analysis_model_name: str = Field(
        default="gemini-3-flash-preview",
        description="Model name for video analysis (valid options: gemini-3-flash-preview, gemini-3-pro-preview)",
        alias="ANALYSIS_MODEL_NAME"
    )
    analysis_timeout_seconds: int = Field(
        default=300,
        description="Timeout for video analysis in seconds",
        alias="ANALYSIS_TIMEOUT_SECONDS"
    )

    # Email Service Configuration (Resend)
    resend_api_key: Optional[str] = Field(
        default=None,
        description="Resend API key for sending digest emails",
        alias="RESEND_API_KEY"
    )
    email_from: str = Field(
        default="Daily AI <digest@yourdomain.com>",
        description="From address for digest emails",
        alias="EMAIL_FROM"
    )

    # X/Twitter API Configuration (OAuth 2.0 PKCE only)
    twitter_oauth2_client_id: Optional[str] = Field(
        default=None,
        description="X/Twitter OAuth 2.0 Client ID",
        alias="TWITTER_OAUTH2_CLIENT_ID"
    )
    twitter_oauth2_client_secret: Optional[str] = Field(
        default=None,
        description="X/Twitter OAuth 2.0 Client Secret",
        alias="TWITTER_OAUTH2_CLIENT_SECRET"
    )
    twitter_oauth2_access_token: Optional[str] = Field(
        default=None,
        description="X/Twitter OAuth 2.0 Access Token (generated via PKCE)",
        alias="TWITTER_OAUTH2_ACCESS_TOKEN"
    )
    twitter_oauth2_refresh_token: Optional[str] = Field(
        default=None,
        description="X/Twitter OAuth 2.0 Refresh Token (for auto-refresh)",
        alias="TWITTER_OAUTH2_REFRESH_TOKEN"
    )

    auto_post_to_x: bool = Field(
        default=False,
        description="Automatically post digest to X as Phase 5 of daily pipeline",
        alias="AUTO_POST_TO_X"
    )

    # Digest Schema Configuration
    digest_schema_version: str = Field(
        default="v3",
        description="Schema version for digest generation: 'v3' (minimalist) or 'v2' (layered)",
        alias="DIGEST_SCHEMA_VERSION"
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

    @computed_field
    @property
    def channel_duration_thresholds(self) -> Dict[str, int]:
        """Parse CHANNEL_DURATION_THRESHOLDS into a dictionary mapping channel names to minutes."""
        if self.channel_duration_thresholds_raw is None or not self.channel_duration_thresholds_raw.strip():
            return {}
        
        thresholds = {}
        for pair in self.channel_duration_thresholds_raw.split(","):
            pair = pair.strip()
            if ":" in pair:
                channel, minutes_str = pair.rsplit(":", 1)
                channel = channel.strip()
                try:
                    minutes = int(minutes_str.strip())
                    if minutes >= 0:  # Validate non-negative
                        thresholds[channel.lower()] = minutes
                except ValueError:
                    logger.warning(f"Invalid threshold value '{minutes_str}' for channel '{channel}', skipping")
        
        return thresholds

    @computed_field
    @property
    def bypass_lookback_channels(self) -> List[str]:
        """Parse BYPASS_LOOKBACK_CHANNELS from comma-separated string."""
        if self.bypass_lookback_channels_raw is None or not self.bypass_lookback_channels_raw.strip():
            return []
        return [ch.strip() for ch in self.bypass_lookback_channels_raw.split(",") if ch.strip()]

settings = Settings()

