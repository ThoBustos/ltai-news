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

class CommunityMention(BaseModel):
    """Community, event, or organization mentioned."""
    name: str = Field(description="Community or organization name")
    type: Literal["discord", "community", "event", "organization"] = Field(description="Type of mention")
    url: Optional[str] = Field(None, description="URL if available")

class VideoAnalysisResponse(BaseModel):
    """Master structured response for comprehensive video analysis."""
    
    # Core analysis components
    tldr: str = Field(description="1-2 paragraph summary of the video")
    key_audience: str = Field(description="Who would benefit most from this content")
    
    # Structured extractions
    core_topics: List[CoreTopic] = Field(description="3-7 main topics identified")
    lessons_learned: Dict[str, List[str]] = Field(description="Lessons organized by category (technical/business/general)")
    sources_referenced: List[SourceReference] = Field(description="External sources mentioned")
    concepts_mentioned: List[ConceptMention] = Field(description="Key concepts and frameworks")
    people_mentioned: List[PersonMention] = Field(description="People referenced in the video")
    communities_mentioned: List[CommunityMention] = Field(description="Communities, events, organizations")
    
    # Analysis and insights
    detailed_insights: str = Field(description="Extended analysis and implications")
    
    # Confidence tracking
    confidence_scores: Dict[str, float] = Field(description="Confidence per extraction category (0.0-1.0)")

# === Database Storage Model ===

class VideoAnalysisComplete(BaseModel):
    """Complete video analysis result for database storage."""
    
    video_id: str
    
    # Analysis results (from LLM structured outputs)
    tldr: str
    key_audience: str
    core_topics: List[Dict[str, Any]]  # Serialized CoreTopic objects
    lessons_learned: Dict[str, List[str]]
    detailed_insights: str
    sources_referenced: List[Dict[str, Any]]  # Serialized SourceReference objects
    concepts_mentioned: List[Dict[str, Any]]  # Serialized ConceptMention objects
    people_mentioned: List[Dict[str, Any]]  # Serialized PersonMention objects
    communities_mentioned: List[Dict[str, Any]]  # Serialized CommunityMention objects
    metadata_extracted: Dict[str, Any]  # Full video/channel metadata
    
    # Processing tracking
    input_tokens: int  # Track input tokens separately
    output_tokens: int  # Track output tokens separately
    total_tokens: int
    total_cost: Optional[float] = None  # Opik tracks cost automatically
    total_processing_time_seconds: float
    confidence_scores: Dict[str, float]
    
    # Processing metadata (for future case studies)
    processing_metadata: Optional[Dict[str, Any]] = Field(None, description="Detailed processing info for case studies")
    
    # Model and timing info
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
