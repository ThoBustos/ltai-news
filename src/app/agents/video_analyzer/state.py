"""Type-safe state definition for video analysis workflow."""

from typing import Dict, Any, List, TypedDict, NotRequired

from app.models.video_analysis import VideoAnalysisResponse, ProcessingMetrics


class VideoAnalysisState(TypedDict):
    """Type-safe state for video analysis workflow."""

    # Input data (loaded in first node)
    video_id: str
    video: NotRequired[Dict[str, Any]]
    transcript: NotRequired[Dict[str, Any]]
    channel: NotRequired[Dict[str, Any]]

    # Analysis results (filled by nodes)
    analysis_response: NotRequired[VideoAnalysisResponse]

    # Processing tracking
    metrics: NotRequired[ProcessingMetrics]
    errors: NotRequired[List[str]]
