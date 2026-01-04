"""Video analysis models for comprehensive extraction and database storage."""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional, Any, Literal
from datetime import datetime

# === LLM Response Model (for structured output) ===

class CoreTopic(BaseModel):
    """Individual topic with metadata."""
    topic: str = Field(description="Clear, specific topic name")
    category: Literal["technical", "business", "philosophy", "general"] = Field(description="Topic category")
    importance: Literal["high", "medium", "low"] = Field(description="Relative importance")

class SourceReference(BaseModel):
    """Individual source reference."""
    type: Literal["paper", "book", "podcast", "link", "discord", "community", "event"] = Field(description="Source type")
    title: str = Field(description="Source title or name")
    url: Optional[str] = Field(None, description="URL if available")
    author: Optional[str] = Field(None, description="Author or creator")

class ConceptMention(BaseModel):
    """Key concept or framework mentioned."""
    concept: str = Field(description="Concept or framework name")
    description: str = Field(description="Brief description of the concept")
    relevance: str = Field(description="Why this concept is relevant to the video")

class PersonMention(BaseModel):
    """Person mentioned in the video."""
    name: str = Field(description="Person's name")
    role: Optional[str] = Field(None, description="Their role or title")
    affiliation: Optional[str] = Field(None, description="Organization or company")
    context: Optional[str] = Field(None, description="Why they're mentioned in this video")
    # V2: Social links - ONLY include if explicitly mentioned in video/description
    social_links: Dict[str, str] = Field(
        default_factory=dict,
        description="Social links ONLY if explicitly mentioned: "
        "{'twitter': '@handle', 'linkedin': 'url', 'website': 'url'}. "
        "Do NOT guess handles or URLs."
    )

class CommunityMention(BaseModel):
    """Community, event, or organization mentioned."""
    name: str = Field(description="Community or organization name")
    type: Literal["discord", "community", "event", "organization", "podcast", "newsletter", "course"] = Field(
        description="Type of mention"
    )
    description: Optional[str] = Field(None, description="Brief description")
    url: Optional[str] = Field(
        None,
        description="URL ONLY if explicitly mentioned in video/description. Do NOT guess URLs."
    )


# === V2 EXTRACTION MODELS ===

class DirectQuote(BaseModel):
    """A direct quote capturing a key insight or aha moment."""
    quote: str = Field(description="Exact quote from the transcript - verbatim")
    speaker: Optional[str] = Field(None, description="Speaker if identifiable from context")
    context: str = Field(description="What topic/point this quote addresses")
    impact: Literal["insight", "prediction", "contrarian", "actionable", "synthesis"] = Field(
        description="Why this quote matters - the type of value it delivers"
    )


class AnalogyMetaphor(BaseModel):
    """An analogy or metaphor used to explain a concept."""
    analogy: str = Field(description="The analogy or metaphor as stated")
    explains: str = Field(description="What concept or idea it illuminates")
    effectiveness: Literal["high", "medium"] = Field(
        description="How well it conveys the idea - high if memorable and clear"
    )


class FrameworkMentioned(BaseModel):
    """A framework, mental model, or structured thinking approach shared."""
    name: str = Field(description="Framework or mental model name")
    description: str = Field(description="How it works or is applied - actionable explanation")
    application: str = Field(description="Specific use case or context from the video")
    source: Optional[str] = Field(None, description="Origin if mentioned (book, person, company)")


class StatisticDataPoint(BaseModel):
    """A concrete number, statistic, or quantified claim."""
    value: str = Field(description="The exact number, percentage, or statistic")
    context: str = Field(description="What it measures or represents")
    significance: str = Field(description="Why this number matters - the implication")


class VideoSection(BaseModel):
    """Deep analysis of a video section/segment."""
    title: str = Field(description="Section title or theme - descriptive")
    timestamp_range: Optional[str] = Field(None, description="Approximate time range if determinable")
    summary: str = Field(description="Dense 2-3 sentence summary with specifics - no generic statements")
    key_points: List[str] = Field(description="3-5 bullet points capturing core value")
    frameworks_used: List[str] = Field(default_factory=list, description="Frameworks referenced in this section")
    notable_quotes: List[str] = Field(default_factory=list, description="Best 1-2 quotes from this section")


class VideoAnalysisResponse(BaseModel):
    """Master structured response for comprehensive video analysis - V2.0."""

    # === CORE SUMMARY ===
    tldr: str = Field(description="2-3 paragraph dense summary with key numbers, frameworks, and insights")
    key_audience: str = Field(description="Who benefits most from this content and why specifically")
    teaser_hooks: List[str] = Field(description="Exactly 3 compelling sentences to tease the content")
    keywords: List[str] = Field(description="8-15 keywords for discoverability and categorization")

    # === STRUCTURED EXTRACTIONS ===
    core_topics: List[CoreTopic] = Field(description="3-7 main topics identified")
    lessons_learned: Dict[str, List[str]] = Field(
        description="Lessons by category (technical/business/general)"
    )
    sources_referenced: List[SourceReference] = Field(description="External sources mentioned")
    concepts_mentioned: List[ConceptMention] = Field(description="Key concepts and frameworks")
    people_mentioned: List[PersonMention] = Field(description="People referenced")
    communities_mentioned: List[CommunityMention] = Field(description="Communities, events, organizations")

    # === V2: DEPTH EXTRACTIONS ===
    direct_quotes: List[DirectQuote] = Field(
        description="5-10 most impactful quotes - verbatim aha moments"
    )
    analogies_metaphors: List[AnalogyMetaphor] = Field(
        description="Analogies and metaphors used to explain concepts"
    )
    frameworks_shared: List[FrameworkMentioned] = Field(
        description="Mental models and frameworks explained"
    )
    statistics_data: List[StatisticDataPoint] = Field(
        description="Numbers, stats, and quantified claims"
    )

    # === SECTION-BY-SECTION ANALYSIS ===
    section_analysis: List[VideoSection] = Field(
        description="Deep analysis of each major section/segment"
    )

    # === SYNTHESIS ===
    detailed_insights: str = Field(description="Extended analysis connecting all elements")

    # === CONFIDENCE ===
    confidence_scores: Dict[str, float] = Field(
        description="Confidence per extraction category (0.0-1.0)"
    )

# === Database Storage Model ===

class VideoAnalysisComplete(BaseModel):
    """Complete video analysis result for database storage - V2.0."""

    video_id: str

    # === CORE ===
    tldr: str
    key_audience: str
    teaser_hooks: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)

    # === STRUCTURED ===
    core_topics: List[Dict[str, Any]]  # Serialized CoreTopic objects
    lessons_learned: Dict[str, List[str]]
    detailed_insights: str
    sources_referenced: List[Dict[str, Any]]  # Serialized SourceReference objects
    concepts_mentioned: List[Dict[str, Any]]  # Serialized ConceptMention objects
    people_mentioned: List[Dict[str, Any]]  # Serialized PersonMention objects
    communities_mentioned: List[Dict[str, Any]]  # Serialized CommunityMention objects

    # === V2: DEPTH EXTRACTIONS ===
    direct_quotes: List[Dict[str, Any]] = Field(default_factory=list)
    analogies_metaphors: List[Dict[str, Any]] = Field(default_factory=list)
    frameworks_shared: List[Dict[str, Any]] = Field(default_factory=list)
    statistics_data: List[Dict[str, Any]] = Field(default_factory=list)
    section_analysis: List[Dict[str, Any]] = Field(default_factory=list)

    # === METADATA ===
    metadata_extracted: Dict[str, Any]  # Full video/channel metadata

    # === PROCESSING ===
    input_tokens: int
    output_tokens: int
    total_tokens: int
    total_cost: Optional[float] = None
    total_processing_time_seconds: float
    confidence_scores: Dict[str, float]
    processing_metadata: Optional[Dict[str, Any]] = Field(None, description="Detailed processing info")

    # === MODEL INFO ===
    model_name: str = "gemini-3-flash-preview"
    processed_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

# === Processing Metrics (for case studies) ===

class ProcessingMetrics(BaseModel):
    """Processing metrics for workflow execution tracking."""
    
    workflow_version: str = "1.0"
    extraction_method: str = "single-master-prompt"  # vs "multi-node" for future comparisons
    opik_trace_id: Optional[str] = None
    opik_experiment_id: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Token and cost breakdown
    input_tokens: int
    output_tokens: int
    total_cost: Optional[float] = None  # Opik tracks cost automatically
    processing_time_seconds: float
    
    # Quality metrics
    confidence_scores: Dict[str, float]
    extraction_completeness: Dict[str, bool]  # Track which sections were successfully extracted
