"""API request/response schemas for orchestrator endpoints."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.models.pipeline import PipelineResult, TranscriptExtractionResult
from app.models.video_analysis import VideoAnalysisComplete
from app.models.daily_digest import DigestGenerationResult, DigestSendResult


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


class DigestGenerationResponse(BaseModel):
    """Response for digest generation requests."""

    message: str
    target_date: str
    status: str
    result: Optional[DigestGenerationResult] = None


class DigestSendRequest(BaseModel):
    """Request for sending a digest."""

    test_email: Optional[str] = None  # If provided, send test to this email only


class DigestSendResponse(BaseModel):
    """Response for digest send requests."""

    message: str
    digest_id: str
    status: str
    result: Optional[DigestSendResult] = None


class DigestContentResponse(BaseModel):
    """Response for getting digest content."""

    message: str
    target_date: str
    digest_id: Optional[str] = None
    title: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = None
    markdown: Optional[str] = None
    html: Optional[str] = None
    video_count: Optional[int] = None
    channels: Optional[List[str]] = None
    is_sent: bool = False
    sent_at: Optional[str] = None
