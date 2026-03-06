"""Weekly digest models for aggregated newsletter generation.

V2 Schema - High-signal, minimalist weekly digest format.
"""

from datetime import datetime, date
from typing import List, Dict, Any, Optional, Literal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.daily_digest import Speaker, ReferenceItem, SocialLinks


# === LLM Response Schema Models (V2) ===

class WeeklyStats(BaseModel):
    """Statistics for the weekly digest."""
    total_videos: int = Field(description="Total videos across all days")
    total_watch_time_minutes: int = Field(description="Sum of all video durations")
    estimated_read_minutes: int = Field(description="Estimated read time at 200 WPM")
    days_covered: int = Field(description="Number of days with content (0-7)")
    channels: List[str] = Field(default_factory=list, description="Unique channels included")


# === V2 New Section Models ===

class TheOneThing(BaseModel):
    """The week's single most important insight."""
    headline: str = Field(description="Punchy, specific statement. Not generic.")
    subtext: str = Field(description="One sentence expanding on why this matters")


class QuoteOfTheWeek(BaseModel):
    """The most memorable verbatim quote from any video."""
    text: str = Field(description="The actual quote from the content")
    speaker: str = Field(description="Who said it")
    source_video_id: str = Field(description="Video ID where this quote appears")


class WatchOne(BaseModel):
    """If someone only watches ONE video this week, which one?"""
    video_id: str
    title: str
    channel: str
    duration_minutes: int
    why: str = Field(description="What makes this the essential watch")


class NumberThatMatters(BaseModel):
    """A striking statistic or number from the week."""
    number: str = Field(description="Formatted number with unit: $100B, 75%, 45x")
    context: str = Field(description="The 'so what' in <5 words")


class ContrarianTake(BaseModel):
    """The most counterintuitive insight from the week."""
    conventional: str = Field(description="What most people believe")
    actual: str = Field(description="What the evidence/experts say")


class ConceptOfTheWeek(BaseModel):
    """One framework/concept worth knowing."""
    term: str = Field(description="Short name or acronym")
    full_name: Optional[str] = Field(default=None, description="Expanded version if applicable")
    definition: str = Field(description="Clear explanation in 1-2 sentences")


class ThemeV2(BaseModel):
    """Simplified theme that appeared across multiple videos."""
    name: str = Field(description="Theme label")
    one_liner: str = Field(description="Single sentence summary")
    mention_count: int = Field(description="How many videos touched this")
    video_ids: List[str] = Field(default_factory=list, description="Which videos (for linking)")


class CategoryVideo(BaseModel):
    """A video entry within a category grouping."""
    video_id: str
    title: str
    channel: str
    day: str = Field(description="Day of week: Monday, Tuesday, etc.")
    duration_minutes: int
    one_liner: str = Field(description="Single sentence key takeaway")


class VideoCategory(BaseModel):
    """A single category with its videos - for Gemini structured output compatibility."""
    category_name: str = Field(description="Category name (e.g., 'AI Agents', 'MLOps', 'Research')")
    videos: List[CategoryVideo] = Field(default_factory=list, description="Videos in this category")


class WeeklyReference(BaseModel):
    """Reference aggregated across the week with mention count."""
    name: str
    reference_type: str = Field(description="book, paper, framework, concept, person, community")
    mention_count: int = Field(default=1, description="Times mentioned this week")
    author: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    # Explicit model for Gemini native structured output compatibility (no Dict types)
    social_links: Optional[SocialLinks] = Field(
        default=None,
        description="Social links for people. Only populate if explicitly mentioned."
    )


class WeeklyContentResponse(BaseModel):
    """V2 LLM response schema for weekly digest generation.

    High-signal, minimalist format focused on:
    - One key insight (the_one_thing)
    - Memorable quote
    - Essential watch recommendation
    - Key numbers
    - Contrarian perspective
    - Framework of the week
    - Simplified themes
    - Videos grouped by LLM-determined categories
    """

    # Stats (kept)
    stats: WeeklyStats

    # Newsletter metadata
    title: str = Field(
        description="Newsletter title. Clear, specific, captures the week's essence. "
        "Example: 'Week of AI Industrialization: From Prompts to Programs'"
    )
    description: str = Field(
        description="One-sentence summary for previews/SEO. What was THIS week about?"
    )

    # V2 new sections
    the_one_thing: TheOneThing = Field(
        description="The week's single most important insight"
    )

    quote_of_the_week: QuoteOfTheWeek = Field(
        description="Most memorable verbatim quote from any video"
    )

    watch_one: WatchOne = Field(
        description="If you only watch ONE video this week, watch this"
    )

    numbers_that_matter: List[NumberThatMatters] = Field(
        description="3 striking statistics/numbers from the week"
    )

    contrarian_take: ContrarianTake = Field(
        description="The most counterintuitive insight"
    )

    concept_of_the_week: ConceptOfTheWeek = Field(
        description="One framework/concept worth knowing"
    )

    themes: List[ThemeV2] = Field(
        description="2-4 themes that appeared across multiple videos"
    )

    video_categories: List[VideoCategory] = Field(
        description="All videos grouped into 3-5 LLM-determined categories"
    )

    weekly_note: str = Field(
        description="Editorial wrap-up. Personal voice, 2-3 sentences. Sign off as '-- LTAI'"
    )

    # Kept for backend (not displayed in newsletter)
    weekly_references: List[WeeklyReference] = Field(
        default_factory=list,
        description="Top references from the week, for backend/search"
    )

    keywords: List[str] = Field(
        default_factory=list,
        description="8-12 keywords for categorization"
    )

    confidence_score: float = Field(
        ge=0.0, le=1.0,
        description="Overall confidence in weekly synthesis"
    )


# === Database Storage Models ===

class WeeklyDigestDB(BaseModel):
    """Model representing a weekly digest in the database."""

    id: Optional[UUID] = None
    week_start_date: date
    week_end_date: date
    title: str
    description: Optional[str] = None

    # Rendered content
    formatted_html: Optional[str] = None
    formatted_markdown: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = None

    # Source tracking
    source_daily_digest_ids: List[UUID] = Field(default_factory=list)
    days_with_content: int = 0

    # Stats
    total_videos: int = 0
    channels_included: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    confidence_score: Optional[float] = None

    # AI metadata
    total_tokens_input: Optional[int] = None
    total_tokens_output: Optional[int] = None
    cost_estimate: Optional[float] = None
    agent_metadata: Optional[Dict[str, Any]] = None

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


# === API Response Models ===

class WeeklyDigestGenerationResult(BaseModel):
    """Result from weekly digest generation workflow."""

    success: bool
    is_empty: bool = False
    weekly_digest_id: Optional[str] = None
    week_start: str
    week_end: str
    title: Optional[str] = None

    # Stats
    days_with_content: int = 0
    videos_included: int = 0
    references_aggregated: int = 0

    # Costs
    total_tokens: int = 0
    total_cost: float = 0.0
    processing_time_seconds: float = 0.0

    errors: List[str] = Field(default_factory=list)

    # Optional preview
    markdown_preview: Optional[str] = None
