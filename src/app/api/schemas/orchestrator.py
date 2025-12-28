"""API request/response schemas for orchestrator endpoints."""

from typing import List, Optional
from pydantic import BaseModel

from app.models.pipeline import PipelineResult, TranscriptExtractionResult
from app.models.video_analysis import VideoAnalysisComplete


class PipelineRunResponse(BaseModel):
    """Response for pipeline run requests."""

    message: str
    target_date: str
    status: str
    result: PipelineResult


class BackfillRequest(BaseModel):
    """Request for backfill operations."""

    start_date: str  # YYYY-MM-DD format
    end_date: str    # YYYY-MM-DD format


class BackfillResponse(BaseModel):
    """Response for backfill requests."""

    message: str
    date_range: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    results: List[PipelineResult]


class TranscriptExtractionResponse(BaseModel):
    """Response for transcript extraction requests."""

    message: str
    target_date: str
    status: str
    result: TranscriptExtractionResult


class VideoAnalysisResponse(BaseModel):
    """Response for single video analysis requests."""

    message: str
    video_id: str
    status: str
    analysis: Optional[VideoAnalysisComplete] = None
    processing_time_seconds: Optional[float] = None
    total_cost: Optional[float] = None
    total_tokens: Optional[int] = None
