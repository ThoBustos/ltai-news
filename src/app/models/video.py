"""Video model for storing video information before processing."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, field_serializer


class VideoProcessingStatus(str, Enum):
    """Status of video processing pipeline."""

    COLLECTED = "collected"  # Just collected, not processed yet
    PROCESSING = "processing"  # Currently being processed
    PROCESSED = "processed"  # Successfully processed
    FAILED = "failed"  # Processing failed
    SKIPPED = "skipped"  # Manually skipped or filtered out


class Video(BaseModel):
    """Video model for storing video information before processing."""

    # Primary identifiers
    id: str = Field(..., description="YouTube video ID")
    channel_id: str = Field(..., description="YouTube channel ID this video belongs to")

    # Essential metadata (collected at discovery time)
    title: str
    description: Optional[str] = None
    published_at: datetime = Field(..., description="When video was published on YouTube")

    # Basic stats (collected at discovery time)
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    duration: Optional[str] = Field(None, description="ISO 8601 duration (e.g., PT10M30S)")
    duration_seconds: Optional[int] = Field(None, description="Duration in seconds")

    # Media URLs
    thumbnail_url: Optional[str] = None
    url: str = Field(..., description="Full YouTube URL")

    # Processing tracking
    status: VideoProcessingStatus = Field(
        VideoProcessingStatus.COLLECTED,
        description="Current processing status",
    )
    collected_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When we first collected this video",
    )
    processed_at: Optional[datetime] = Field(
        None,
        description="When processing was completed (if applicable)",
    )
    processing_error: Optional[str] = Field(
        None,
        description="Error message if processing failed",
    )

    # Raw metadata (full API response for flexibility)
    raw_metadata: Optional[dict] = Field(None, description="Full YouTube API metadata dict")

    # Optional: Processing metadata (filled later by processing service)
    transcript_fetched: bool = Field(False, description="Whether transcript has been fetched")
    transcript_error: Optional[str] = Field(None, description="Error message if transcript extraction failed")
    summary_generated: bool = Field(False, description="Whether summary has been generated")
    tags_extracted: bool = Field(False, description="Whether tags have been extracted")

    model_config = ConfigDict()

    @field_serializer("published_at", "collected_at", "processed_at")
    def serialize_datetime(self, value: Optional[datetime], _info) -> Optional[str]:
        """Serialize datetime to ISO format string."""
        if value is None:
            return None
        return value.isoformat()

