"""Type-safe state definition for X thread workflow."""

from typing import Dict, Any, List, TypedDict, NotRequired, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.daily_digest import DigestContentResponse


class XThreadMetrics(BaseModel):
    """Processing metrics for X thread generation."""
    workflow_version: str = "1.0"
    started_at: datetime = Field(default_factory=lambda: datetime.now())
    completed_at: Optional[datetime] = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    total_cost: Optional[float] = None
    processing_time_seconds: float = 0.0
    tweet_count: int = 0


class XThreadState(TypedDict):
    """Type-safe state for X thread workflow.

    This state flows through the LangGraph workflow nodes:
    1. load_digest_node: Loads digest data and channel metadata
    2. generate_thread_node: Generates X thread using LLM
    3. post_to_x_node: Posts thread to X via API
    """

    # Input (required)
    target_date: str  # YYYY-MM-DD format
    digest_id: str  # Digest database ID

    # Data loaded in first node
    digest_content: NotRequired[DigestContentResponse]  # Full digest data
    channels: NotRequired[List[Dict[str, Any]]]  # Channel data with X handles

    # LLM-generated thread
    thread_tweets: NotRequired[List[str]]  # Each tweet <280 chars

    # X API results
    tweet_ids: NotRequired[List[str]]  # Posted tweet IDs
    thread_url: NotRequired[str]  # Link to first tweet

    # Processing tracking
    metrics: NotRequired[XThreadMetrics]  # tokens, cost, time (typed Pydantic model)
    errors: NotRequired[List[str]]
