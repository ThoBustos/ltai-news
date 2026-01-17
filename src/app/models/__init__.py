"""Data models for channel tracking and video collection."""

from app.models.channel import Channel, ChannelSyncResult, ChannelTrackerResult
from app.models.video import Video, VideoProcessingStatus
from app.models.daily_digest import (
    DailyDigestDB,
    DailyDigestState,
    DigestContentResponse,
    DigestGenerationResult,
    DigestMetrics,
    DigestReference,
    DigestSendResult,
)
from app.models.weekly_digest import (
    WeeklyDigestDB,
    WeeklyDigestGenerationResult,
    WeeklyContentResponse,
    WeeklyStats,
    # V2 models
    TheOneThing,
    QuoteOfTheWeek,
    WatchOne,
    NumberThatMatters,
    ContrarianTake,
    ConceptOfTheWeek,
    ThemeV2,
    CategoryVideo,
    WeeklyReference,
)

__all__ = [
    "Channel",
    "Video",
    "VideoProcessingStatus",
    "ChannelSyncResult",
    "ChannelTrackerResult",
    # Daily Digest models
    "DailyDigestDB",
    "DailyDigestState",
    "DigestContentResponse",
    "DigestGenerationResult",
    "DigestMetrics",
    "DigestReference",
    "DigestSendResult",
    # Weekly Digest V2 models
    "WeeklyDigestDB",
    "WeeklyDigestGenerationResult",
    "WeeklyContentResponse",
    "WeeklyStats",
    "TheOneThing",
    "QuoteOfTheWeek",
    "WatchOne",
    "NumberThatMatters",
    "ContrarianTake",
    "ConceptOfTheWeek",
    "ThemeV2",
    "CategoryVideo",
    "WeeklyReference",
]

