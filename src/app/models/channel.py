"""Channel model for tracking YouTube channels."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict, field_serializer

from app.models.video import Video


class Channel(BaseModel):
    """Channel model for tracking YouTube channels."""

    # Primary identifiers
    id: str = Field(..., description="YouTube channel ID (e.g., UC...)")
    name: str = Field(..., description="Channel display name")

    # Optional identifiers (for easier lookup)
    handle: Optional[str] = Field(None, description="YouTube channel handle (e.g., @LatentSpacePod)")
    x_handle: Optional[str] = Field(None, description="X/Twitter handle (e.g., @LatentSpacePod)")
    custom_url: Optional[str] = Field(None, description="Custom URL if available")

    # Metadata (collected from YouTube API)
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    published_at: Optional[datetime] = None

    # Statistics (snapshot at collection time)
    subscriber_count: Optional[int] = None
    video_count: Optional[int] = None
    view_count: Optional[int] = None

    # Internal tracking
    uploads_playlist_id: Optional[str] = Field(
        None, description="YouTube uploads playlist ID"
    )
    last_synced_at: Optional[datetime] = Field(
        None, description="Last time we synced this channel"
    )
    is_active: bool = Field(True, description="Whether this channel is actively tracked")

    # Raw metadata (for flexibility - store full API response)
    raw_metadata: Optional[dict] = Field(None, description="Full YouTube API metadata dict")

    model_config = ConfigDict()

    @field_serializer("published_at", "last_synced_at")
    def serialize_datetime(self, value: Optional[datetime], _info) -> Optional[str]:
        """Serialize datetime to ISO format string."""
        if value is None:
            return None
        return value.isoformat()


class ChannelSyncResult(BaseModel):
    """Result of syncing a single channel."""

    channel: Channel
    videos_collected: List[Video]
    videos_count: int
    sync_started_at: datetime
    sync_completed_at: datetime
    error: Optional[str] = None

    model_config = ConfigDict()

    @field_serializer("sync_started_at", "sync_completed_at")
    def serialize_datetime(self, value: datetime, _info) -> str:
        """Serialize datetime to ISO format string."""
        return value.isoformat()

    @property
    def duration_seconds(self) -> float:
        """Duration of sync in seconds."""
        return (self.sync_completed_at - self.sync_started_at).total_seconds()


class ChannelTrackerResult(BaseModel):
    """Overall result of channel tracking operation."""

    channels_processed: int
    channels_found: int
    channels_not_found: List[str]  # Channel names that couldn't be resolved
    total_videos_collected: int
    lookback_hours: int
    sync_results: List[ChannelSyncResult]
    started_at: datetime
    completed_at: datetime

    model_config = ConfigDict()

    @field_serializer("started_at", "completed_at")
    def serialize_datetime(self, value: datetime, _info) -> str:
        """Serialize datetime to ISO format string."""
        return value.isoformat()

    @property
    def duration_seconds(self) -> float:
        """Total duration in seconds."""
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def success_rate(self) -> float:
        """Percentage of channels successfully synced."""
        if self.channels_processed == 0:
            return 0.0
        return (self.channels_found / self.channels_processed) * 100

