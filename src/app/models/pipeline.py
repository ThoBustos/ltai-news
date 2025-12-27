"""Pipeline execution tracking models."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, computed_field

from app.core.utils.time_window import TimeWindow


class ExtractionResult(BaseModel):
    """Result of content extraction phase."""
    
    videos_found: int
    videos_saved: int
    channels_processed: int
    channels_found: int
    channels_not_found: List[str]
    errors: List[str]
    window: TimeWindow
    started_at: datetime
    completed_at: datetime
    
    @computed_field
    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        return (self.completed_at - self.started_at).total_seconds()
    
    @computed_field
    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.videos_found == 0:
            return 100.0
        return (self.videos_saved / self.videos_found) * 100.0


class ProcessingResult(BaseModel):
    """Result of video processing phase."""
    
    videos_processed: int
    transcripts_extracted: int
    analyses_completed: int
    errors: List[str]
    started_at: datetime
    completed_at: datetime
    
    @computed_field
    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        return (self.completed_at - self.started_at).total_seconds()


class DigestResult(BaseModel):
    """Result of digest generation phase."""
    
    digest_generated: bool
    videos_included: int
    digest_id: Optional[str]
    errors: List[str]
    started_at: datetime
    completed_at: datetime
    
    @computed_field
    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        return (self.completed_at - self.started_at).total_seconds()


class PipelineResult(BaseModel):
    """Complete pipeline execution result."""
    
    target_date: str  # YYYY-MM-DD format
    window: TimeWindow
    extraction: Optional[ExtractionResult]
    processing: Optional[ProcessingResult]
    digest: Optional[DigestResult]
    pipeline_started_at: datetime
    pipeline_completed_at: datetime
    total_errors: List[str]
    
    @computed_field
    @property
    def duration_seconds(self) -> float:
        """Get total pipeline duration in seconds."""
        return (self.pipeline_completed_at - self.pipeline_started_at).total_seconds()
    
    @computed_field
    @property
    def success(self) -> bool:
        """Check if pipeline completed successfully."""
        return len(self.total_errors) == 0
    
    @computed_field
    @property
    def summary(self) -> dict:
        """Get pipeline summary statistics."""
        return {
            "target_date": self.target_date,
            "duration_seconds": self.duration_seconds,
            "success": self.success,
            "total_errors": len(self.total_errors),
            "videos_found": self.extraction.videos_found if self.extraction else 0,
            "videos_saved": self.extraction.videos_saved if self.extraction else 0,
            "videos_processed": self.processing.videos_processed if self.processing else 0,
            "digest_generated": self.digest.digest_generated if self.digest else False,
        }


class PipelineStatus(BaseModel):
    """Current status of a pipeline run."""
    
    target_date: str
    status: str  # 'pending', 'extracting', 'processing', 'generating_digest', 'completed', 'failed'
    current_phase: Optional[str]
    started_at: Optional[datetime]
    estimated_completion: Optional[datetime]
    progress_percentage: float = 0.0
    last_updated: datetime
    errors: List[str]
    
    @computed_field
    @property
    def is_running(self) -> bool:
        """Check if pipeline is currently running."""
        return self.status in ['extracting', 'processing', 'generating_digest']
    
    @computed_field
    @property
    def is_completed(self) -> bool:
        """Check if pipeline is completed (success or failure)."""
        return self.status in ['completed', 'failed']


class TranscriptRequest(BaseModel):
    """Request for transcript extraction."""
    
    video_id: str
    language_code: str = "en"
    force_refresh: bool = False


class TranscriptResult(BaseModel):
    """Result of transcript extraction."""
    
    video_id: str
    success: bool
    transcript: Optional[str] = None
    char_count: Optional[int] = None
    language_code: Optional[str] = "en"
    error: Optional[str] = None
    extracted_at: datetime
    
    @computed_field
    @property
    def character_count(self) -> int:
        """Get transcript character count."""
        if self.char_count is not None:
            return self.char_count
        return len(self.transcript) if self.transcript else 0
    
    @computed_field
    @property
    def is_terminal_failure(self) -> bool:
        """Check if this is a terminal failure (don't retry)."""
        if not self.success and self.error:
            terminal_errors = [
                "no transcript available",
                "transcript not found",
                "transcript disabled",
                "unauthorized",
                "forbidden"
            ]
            error_lower = self.error.lower()
            return any(term in error_lower for term in terminal_errors)
        return False


class TranscriptExtractionResult(BaseModel):
    """Result of batch transcript extraction."""
    
    videos_attempted: int
    transcripts_extracted: int
    transcripts_failed: int
    transcripts_skipped: int
    errors: List[str]
    started_at: datetime
    completed_at: datetime
    
    @computed_field
    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        return (self.completed_at - self.started_at).total_seconds()
    
    @computed_field
    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.videos_attempted == 0:
            return 100.0
        return (self.transcripts_extracted / self.videos_attempted) * 100.0


class AnalysisResult(BaseModel):
    """Result of video analysis."""
    
    video_id: str
    success: bool
    summary: Optional[str]
    analysis: Optional[str]
    key_points: List[str]
    tags: List[str]
    error: Optional[str]
    model_name: Optional[str]
    tokens_used: Optional[int]
    analyzed_at: datetime