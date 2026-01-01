"""Type-safe state definition for daily digest workflow."""

from typing import Dict, Any, List, TypedDict, NotRequired

from app.models.daily_digest import DigestContentResponse, DigestMetrics


class DailyDigestState(TypedDict):
    """Type-safe state for daily digest workflow.

    This state flows through the LangGraph workflow nodes:
    1. load_data_node: Loads video analyses and metadata for target date
    2. generate_digest_node: Generates digest content using LLM
    3. save_results_node: Saves digest to database and extracts references
    """

    # Input (required)
    target_date: str  # YYYY-MM-DD format

    # Data loaded in first node
    video_analyses: NotRequired[List[Dict[str, Any]]]  # Full analysis data per video
    video_metadata: NotRequired[List[Dict[str, Any]]]  # Video + channel metadata
    channel_stats: NotRequired[Dict[str, Dict[str, Any]]]  # Channel aggregates

    # LLM output (from generate_digest_node)
    digest_content: NotRequired[DigestContentResponse]

    # Rendered output
    formatted_markdown: NotRequired[str]
    formatted_html: NotRequired[str]

    # Processing tracking
    metrics: NotRequired[DigestMetrics]
    errors: NotRequired[List[str]]

    # Result (from save_results_node)
    digest_id: NotRequired[str]
    references_extracted: NotRequired[int]
