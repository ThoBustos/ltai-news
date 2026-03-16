"""Type-safe state definition for daily digest workflow."""

from typing import Dict, Any, List, Union, TypedDict, NotRequired

from app.models.daily_digest import DigestContentResponse, DigestContentResponseV3, DigestMetrics


class DailyDigestState(TypedDict):
    """Type-safe state for daily digest workflow.

    This state flows through the LangGraph workflow nodes:
    1. load_data_node: Loads video analyses and metadata for target date
    2. compress_videos_node: Compresses each analysis to ~400 tokens (no LLM)
    3. write_digest_node: Generates digest content using LLM (from compact summaries)
    4. save_results_node: Saves digest to database and extracts references
    """

    # Input (required)
    target_date: str  # YYYY-MM-DD format

    # Data loaded in first node
    video_analyses: NotRequired[List[Dict[str, Any]]]  # Full analysis data per video
    video_metadata: NotRequired[List[Dict[str, Any]]]  # Video + channel metadata
    channel_stats: NotRequired[Dict[str, Dict[str, Any]]]  # Channel aggregates

    # Compact summaries produced by compress_videos_node (~400 tokens each)
    # Used by write_digest_node instead of raw analyses to stay within token limits
    video_summaries: NotRequired[List[str]]

    # LLM output (from write_digest_node)
    digest_content: NotRequired[Union[DigestContentResponse, DigestContentResponseV3]]

    # Rendered output
    formatted_markdown: NotRequired[str]
    formatted_html: NotRequired[str]

    # Processing tracking
    metrics: NotRequired[DigestMetrics]
    errors: NotRequired[List[str]]

    # Result (from save_results_node)
    digest_id: NotRequired[str]
    references_extracted: NotRequired[int]
    is_empty: NotRequired[bool]  # True when no videos found (still saves to DB)
