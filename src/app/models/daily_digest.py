"""Daily digest models for newsletter generation and database storage."""

from datetime import datetime, date
from typing import List, Dict, Any, Optional, Literal, TypedDict, NotRequired
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# === LLM Response Schema Models ===

class ChannelStat(BaseModel):
    """Statistics for a single channel in the digest."""
    channel_id: str
    channel_name: str
    video_count: int
    thumbnail_url: Optional[str] = None


class DigestStats(BaseModel):
    """Overall statistics for the digest - V2."""
    video_count: int
    total_duration_minutes: int
    estimated_read_minutes: int = Field(description="Estimated read time based on word count at 200 WPM")
    channels: List[ChannelStat]


# GoldenNugget removed in V2 - VideoSection now has depth fields directly


class VideoSection(BaseModel):
    """Section for a single video in the digest - V2."""
    video_id: str
    title: str
    channel_name: str
    # thumbnail_url removed in V2 - text-focused digest
    duration_minutes: int = Field(description="Video duration in minutes")
    speakers: List[str] = Field(default_factory=list, description="Main speakers if identifiable")
    tags: List[str] = Field(default_factory=list, description="3-5 topic tags for categorization")

    # Core summary
    condensed_summary: str = Field(
        description="2-3 sentence dense summary with specific takeaways, not generic description"
    )
    structure_overview: str = Field(
        description="Brief outline of video structure/sections for context"
    )

    # V2 depth fields
    key_quotes: List[str] = Field(
        description="2-3 best verbatim quotes from the video"
    )
    frameworks_mentioned: List[str] = Field(
        default_factory=list,
        description="Framework/mental model names referenced"
    )
    key_statistics: List[str] = Field(
        default_factory=list,
        description="Important numbers/statistics mentioned"
    )
    key_analogies: List[str] = Field(
        default_factory=list,
        description="Memorable analogies used to explain concepts"
    )

    # Deep dive
    deep_analysis: str = Field(
        description="2-4 paragraphs connecting ideas, demonstrating implications, "
        "articulating where ideas connect or diverge. Dense with specifics."
    )

    # Cross-video connections
    connections: List[str] = Field(
        default_factory=list,
        description="How this video connects to others in the digest"
    )

    video_url: str


class ContrarianCorner(BaseModel):
    """One counterintuitive insight from the day's content."""
    insight: str = Field(description="The counterintuitive idea")
    source_video_id: str
    why_counterintuitive: str = Field(description="Why this challenges common wisdom")


class ActionItem(BaseModel):
    """Concrete action item derived from the day's insights."""
    action: str = Field(description="What to do")
    context: str = Field(description="Why/how it connects to today's insights")
    difficulty: Literal["quick", "medium", "deep-dive"] = Field(
        description="Effort level required"
    )


class ReferenceItem(BaseModel):
    """A reference (book, framework, concept, etc.) mentioned in the content."""
    name: str
    author: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    source_video_id: Optional[str] = None


class ReferencesIndex(BaseModel):
    """Categorized index of all references from the digest."""
    books: List[ReferenceItem] = Field(default_factory=list)
    papers: List[ReferenceItem] = Field(default_factory=list)
    frameworks: List[ReferenceItem] = Field(default_factory=list)
    concepts: List[ReferenceItem] = Field(default_factory=list)
    people: List[ReferenceItem] = Field(default_factory=list)
    communities: List[ReferenceItem] = Field(default_factory=list)


class DigestContentResponse(BaseModel):
    """Complete LLM response schema for digest generation - V2."""

    title: str = Field(
        description="Clear, specific title that delivers value. Not abstract or hype. "
        "Direct learning statement. Example: 'Specialized AI Models Outperform General Reasoners for Niche Tasks'"
    )
    # title_emoji removed in V2 - no emojis

    # Navigation
    table_of_contents: List[str] = Field(
        description="Section titles for navigation: intro, each video title, action items, references"
    )

    stats: DigestStats = Field(description="Video count, duration, read time, and channels breakdown")
    daily_tldr: str = Field(description="3-4 paragraphs bridging all concepts, non-obvious connections")
    video_sections: List[VideoSection] = Field(description="Per-video content sections with V2 depth")
    contrarian_corner: ContrarianCorner = Field(description="One counterintuitive insight")
    action_items: List[ActionItem] = Field(description="3-5 concrete things to do")
    references_index: ReferencesIndex = Field(description="Categorized references")
    conclusion: str = Field(description="Closing thought that ties everything together")
    keywords: List[str] = Field(description="8-12 keywords for categorization")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Overall confidence (0.0-1.0)")


# === State Models for LangGraph Workflow ===

class DigestMetrics(BaseModel):
    """Processing metrics for digest generation."""

    workflow_version: str = "1.0"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    input_tokens: int = 0
    output_tokens: int = 0
    total_cost: Optional[float] = None
    processing_time_seconds: float = 0.0

    videos_analyzed: int = 0
    references_extracted: int = 0


class DailyDigestState(TypedDict):
    """Type-safe state for daily digest workflow."""

    # Input
    target_date: str  # YYYY-MM-DD format

    # Data loaded in first node
    video_analyses: NotRequired[List[Dict[str, Any]]]
    video_metadata: NotRequired[List[Dict[str, Any]]]

    # LLM output
    digest_content: NotRequired[DigestContentResponse]

    # Rendered output
    formatted_markdown: NotRequired[str]
    formatted_html: NotRequired[str]

    # Processing tracking
    metrics: NotRequired[DigestMetrics]
    errors: NotRequired[List[str]]

    # Result
    digest_id: NotRequired[str]


# === Database Storage Models ===

class DailyDigestDB(BaseModel):
    """Model representing a daily digest in the database."""

    id: Optional[UUID] = None
    publish_date: date
    title: str
    description: Optional[str] = None
    formatted_html: Optional[str] = None
    formatted_markdown: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = None

    # Source tracking
    source_video_ids: List[str] = Field(default_factory=list)
    source_tweet_ids: List[str] = Field(default_factory=list)

    # Stats
    video_count: Optional[int] = None
    channels_included: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    confidence_score: Optional[float] = None

    # AI metadata
    total_tokens_input: Optional[int] = None
    total_tokens_output: Optional[int] = None
    cost_estimate: Optional[float] = None
    agent_metadata: Optional[Dict[str, Any]] = None
    eval_score: Optional[float] = None

    # Status
    is_sent: bool = False
    sent_at: Optional[datetime] = None
    recipient_count: int = 0

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            UUID: str
        }
    )


class DigestReference(BaseModel):
    """Model for cross-day reference tracking."""

    id: Optional[UUID] = None
    reference_type: Literal["book", "paper", "framework", "concept", "person", "community"]
    name: str
    author: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    first_seen_date: date
    mention_count: int = 1
    digest_ids: List[UUID] = Field(default_factory=list)
    video_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            UUID: str
        }
    )


# === API Response Models ===

class DigestGenerationResult(BaseModel):
    """Result from digest generation workflow."""

    success: bool
    digest_id: Optional[str] = None
    publish_date: str
    title: Optional[str] = None

    # Stats
    videos_included: int = 0
    channels_included: int = 0
    references_extracted: int = 0

    # Costs
    total_tokens: int = 0
    total_cost: float = 0.0
    processing_time_seconds: float = 0.0

    errors: List[str] = Field(default_factory=list)

    # Optional rendered content for immediate use
    markdown_preview: Optional[str] = None


class DigestSendResult(BaseModel):
    """Result from sending a digest via email."""

    success: bool
    digest_id: str
    recipients_sent: int = 0
    recipients_failed: int = 0
    sent_at: Optional[datetime] = None
    errors: List[str] = Field(default_factory=list)
