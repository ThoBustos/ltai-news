"""State definition for weekly digest workflow."""

from typing import TypedDict, NotRequired, List, Dict, Any

from app.models.weekly_digest import WeeklyContentResponse


class WeeklyDigestState(TypedDict):
    """Type-safe state for weekly digest workflow.

    This state flows through the LangGraph workflow nodes:
    1. load_week_data_node: Loads daily digests and references for the week
    2. generate_weekly_node: Generates weekly content using LLM
    3. save_results_node: Saves weekly digest to database
    """

    # Input (required)
    week_start_date: str  # YYYY-MM-DD (Monday)
    week_end_date: str    # YYYY-MM-DD (Sunday)

    # Data loaded in first node
    daily_digests: NotRequired[List[Dict[str, Any]]]
    trending_references: NotRequired[List[Dict[str, Any]]]
    aggregated_social_links: NotRequired[Dict[str, Dict[str, str]]]

    # Generated content
    weekly_content: NotRequired[WeeklyContentResponse]
    formatted_markdown: NotRequired[str]
    formatted_html: NotRequired[str]

    # Tracking
    days_with_content: NotRequired[int]
    is_empty: NotRequired[bool]
    metrics: NotRequired[Dict[str, Any]]
    errors: NotRequired[List[str]]

    # Result
    weekly_digest_id: NotRequired[str]
