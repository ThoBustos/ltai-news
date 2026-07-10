"""Daily digest models for newsletter generation and database storage."""

from datetime import datetime, date
from typing import List, Dict, Any, Optional, Literal, TypedDict, NotRequired
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# === LLM Response Schema Models ===

class SocialLinks(BaseModel):
    """Social media links for references - explicit model for Gemini compatibility."""
    twitter: Optional[str] = Field(
        default=None,
        description="Twitter/X handle or URL"
    )
    linkedin: Optional[str] = Field(
        default=None,
        description="LinkedIn profile URL"
    )
    github: Optional[str] = Field(
        default=None,
        description="GitHub profile URL"
    )
    youtube: Optional[str] = Field(
        default=None,
        description="YouTube channel URL"
    )
    website: Optional[str] = Field(
        default=None,
        description="Personal or organization website URL"
    )

    def to_dict(self) -> Dict[str, str]:
        """Convert to dict for backward compatibility."""
        return {k: v for k, v in self.model_dump().items() if v is not None}


class ChannelStat(BaseModel):
    """Statistics for a single channel in the digest."""
    channel_id: str
    channel_name: str
    video_count: int
    thumbnail_url: Optional[str] = None
    channel_url: str = Field(
        default="",
        description="YouTube channel URL - populated programmatically from channel_id"
    )


class DigestStats(BaseModel):
    """Overall statistics for the digest - V2."""
    video_count: int
    total_duration_minutes: int
    estimated_read_minutes: int = Field(description="Estimated read time based on word count at 200 WPM")
    channels: List[ChannelStat]


# GoldenNugget removed in V2 - VideoSection now has depth fields directly


class Speaker(BaseModel):
    """Speaker with optional social links - only from video context."""
    name: str = Field(description="Speaker name")
    twitter_url: Optional[str] = Field(
        default=None,
        description="Twitter/X URL ONLY if found in video context"
    )
    youtube_url: Optional[str] = Field(
        default=None,
        description="YouTube channel URL ONLY if found in video context"
    )
    linkedin_url: Optional[str] = Field(
        default=None,
        description="LinkedIn URL ONLY if found in video context"
    )


class VideoSection(BaseModel):
    """Section for a single video in the digest - V2."""
    video_id: str
    title: str
    channel_name: str
    # thumbnail_url removed in V2 - text-focused digest
    duration_minutes: int = Field(description="Video duration in minutes")
    speakers: List[Speaker] = Field(
        default_factory=list,
        description="Main speakers with social links from video context only"
    )
    tags: List[str] = Field(default_factory=list, description="3-5 topic tags for categorization")

    # V2.2: Logical flow - intellectual journey (NO ARROWS - frontend adds them)
    logical_flow: List[str] = Field(
        default_factory=list,
        description="4-6 concepts in sequence showing intellectual journey. "
        "NOT buzzwords. NO ARROWS in data (frontend renders arrows between items). "
        "Example: ['Problem: context collapse', '700k token evidence', "
        "'Agentic RAG proposal', 'Sub-agent constraints']"
    )

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


# === V2 Cross-Video Analysis Models ===

class TensionPerspective(BaseModel):
    """One side of a key tension between videos."""
    position: str = Field(description="The viewpoint or stance")
    video_id: str = Field(description="Video ID for linking")
    video_title: str = Field(description="Video title for display")
    speaker: Optional[str] = Field(default=None, description="Speaker name if known")


class ConvergencePoint(BaseModel):
    """Concept mentioned by multiple videos - shows field consensus."""
    concept: str = Field(description="The shared concept or theme")
    video_ids: List[str] = Field(description="List of video IDs that mention this")
    video_titles: List[str] = Field(description="Video titles for display")
    synthesis: str = Field(
        description="How these videos together illuminate the concept. "
        "2-3 sentences connecting their perspectives."
    )


class KeyTension(BaseModel):
    """Where videos disagree or offer different perspectives."""
    topic: str = Field(description="The contested topic or question")
    perspectives: List[TensionPerspective] = Field(
        description="Different viewpoints from different videos"
    )
    resolution: Optional[str] = Field(
        default=None,
        description="How to reconcile the tension, if possible. "
        "Can be None if tension is unresolved."
    )


class ContrarianCorner(BaseModel):
    """One counterintuitive insight from the day's content."""
    insight: str = Field(description="The counterintuitive idea")
    source_video_id: str = Field(description="Video ID for linking")
    source_video_title: str = Field(
        default="",
        description="Video title for display and attribution"
    )
    why_counterintuitive: str = Field(description="Why this challenges common wisdom")
    so_what: str = Field(
        default="",
        description="What should the reader do differently based on this insight? "
        "Concrete, actionable implication. "
        "Example: 'When evaluating AI tools, look for benchmarks that include impossible cases.'"
    )


class ActionItem(BaseModel):
    """Concrete action item derived from the day's insights."""
    action: str = Field(description="What to do (imperative)")
    context: str = Field(description="Why/how it connects to today's insights")
    difficulty: Literal["quick", "medium", "deep-dive"] = Field(
        description="Effort level required"
    )
    # V2: Source attribution and concrete first step
    source_video_id: str = Field(
        default="",
        description="Video ID for linking to relevant section"
    )
    source_video_title: str = Field(
        default="",
        description="Video title for attribution"
    )
    first_step: str = Field(
        default="",
        description="Concrete first step to take (not abstract). "
        "Example: 'Run your RAG at 50%, 70%, 90% utilization. Measure retrieval accuracy.'"
    )


class ReferenceItem(BaseModel):
    """A reference (book, framework, concept, etc.) mentioned in the content."""
    name: str
    author: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    source_video_id: Optional[str] = None
    # Explicit model for Gemini native structured output compatibility (no Dict types)
    social_links: Optional[SocialLinks] = Field(
        default=None,
        description="Social links for people/orgs. Only populate if explicitly mentioned."
    )


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

    # === V2: Layered Overview (NEW) ===
    big_picture_bullets: List[str] = Field(
        default_factory=list,
        description="1-2 bullets per video for 30-second skim. "
        "Each is ONE complete insight with specific numbers/names. "
        "Can merge concepts from multiple videos. "
        "Format: '**Key term** — insight with [entity link](url) when available in context'"
    )

    deeper_picture: str = Field(
        default="",
        description="2-6 paragraphs connecting concepts across videos (scales with video count: "
        "1-3 videos → 2-3 paragraphs, 4-7 videos → 3-4 paragraphs, 8+ videos → 4-6 paragraphs). "
        "Use **bold** for key terms. "
        "Pattern: 'Video A introduces X. Video B shows why X fails.' "
        "EMBED video links inline: *[Video Title](video_url)* - every video title should be clickable. "
        "DO NOT list sources separately at the beginning."
    )

    # === V2: Cross-Video Analysis (NEW) ===
    convergence_points: List[ConvergencePoint] = Field(
        default_factory=list,
        description="Concepts mentioned by 2+ videos showing field consensus. "
        "Empty list is valid if no genuine convergence exists. Do NOT force connections."
    )

    key_tensions: List[KeyTension] = Field(
        default_factory=list,
        description="Where videos disagree or offer different perspectives. "
        "Empty list is valid if no genuine disagreement exists. Do NOT invent tensions."
    )

    # Legacy field - keep for backwards compat
    daily_tldr: str = Field(
        default="",
        description="Legacy field - keep for backwards compat. "
        "Can be empty if big_picture_bullets is populated."
    )
    video_sections: List[VideoSection] = Field(description="Per-video content sections with V2 depth")
    contrarian_corner: ContrarianCorner = Field(description="One counterintuitive insight")
    action_items: List[ActionItem] = Field(description="3-5 concrete things to do")
    references_index: ReferencesIndex = Field(description="Categorized references")
    conclusion: str = Field(description="Closing thought that ties everything together")
    keywords: List[str] = Field(description="8-12 keywords for categorization")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Overall confidence (0.0-1.0)")


# === V3 Schema — Minimalist format ===

class VideoSectionV3(BaseModel):
    """Per-video section for V3 digest — minimalist."""
    video_id: str
    title: str
    speaker: str = Field(description="Primary speaker name. E.g. 'Andrej Karpathy'")
    channel_name: str
    duration_minutes: int
    video_url: str
    framing: str = Field(
        description="1-2 sentences. What this video is actually about. Who is speaking. Why it matters today. No em dashes."
    )
    bullets: List[str] = Field(
        description="4-8 key points. Each is one complete thought with specific names, numbers, or claims. No em dashes."
    )


class ReferencesV3(BaseModel):
    """Flat reference lists for V3 digest."""
    people: List[str] = Field(
        default_factory=list,
        description="Names mentioned. Include URL if explicitly in video context. E.g. 'Andrej Karpathy (x.com/karpathy)'"
    )
    tools: List[str] = Field(
        default_factory=list,
        description="Tools, products, frameworks mentioned. E.g. 'LangGraph (langchain.com)'"
    )
    papers: List[str] = Field(
        default_factory=list,
        description="Papers or books mentioned. E.g. 'Attention Is All You Need'"
    )


class DigestContentResponseV3(BaseModel):
    """Complete LLM response schema for V3 digest — minimalist format."""
    schema_version: Literal["v3"] = "v3"

    title: str = Field(
        description="Punchy one-line title. Captures the most important thing today. No em dashes. Not abstract. Not hype. Example: 'The model is not the bottleneck anymore.'"
    )

    meta: str = Field(
        description="Date and video count. Format exactly: 'Month D · N videos'. Example: 'March 4 · 6 videos'"
    )

    intro: str = Field(
        description=(
            "Staccato short sentences, each on its own line (use actual newlines). "
            "Not paragraphs. Distill what mattered today. "
            "Name specific people, products, numbers. "
            "No em dashes. No filler. No 'In this issue...' opener. "
            "Example:\n"
            "Three channels said it today.\n"
            "None of them coordinated.\n"
            "That's the signal.\n\n"
            "Gemini Flash pricing dropped again.\n"
            "Cursor hit $500M ARR.\n"
            "Karpathy was right about pipelines."
        )
    )

    pull_quote: Optional[str] = Field(
        default=None,
        description="One genuinely great verbatim quote from the day. Only populate when it truly stands out. Leave null otherwise. Do not force."
    )

    video_sections: List[VideoSectionV3]

    references: ReferencesV3

    keywords: List[str] = Field(description="6-10 keywords for search")
    confidence_score: float = Field(ge=0.0, le=1.0)


class DigestSynthesisResponse(BaseModel):
    """LLM response schema for synthesizing title/intro/pull_quote from multiple chunk digests."""
    title: str = Field(description="Punchy one-line title capturing the most important theme across all videos. No em dashes.")
    intro: str = Field(description="Staccato short sentences, each on its own line. Synthesize key signals from all batches. No em dashes.")
    pull_quote: Optional[str] = Field(default=None, description="The single best verbatim quote from all batches. Null if none stands out.")


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
    is_empty: bool = False
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
