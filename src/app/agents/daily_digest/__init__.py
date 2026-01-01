"""Daily digest agent module.

This module generates daily AI newsletters from video analysis data.
Uses LangGraph workflow with Gemini Flash 3 and Opik tracking.

Usage:
    from app.agents.daily_digest import generate_daily_digest

    result = await generate_daily_digest(target_date)
    if result.success:
        print(f"Generated digest: {result.digest_id}")
"""

from app.agents.daily_digest.workflow import (
    generate_daily_digest,
    get_daily_digest_workflow,
    create_daily_digest_workflow,
)
from app.agents.daily_digest.state import DailyDigestState
from app.agents.daily_digest.formatters import (
    format_digest_markdown,
    format_digest_html,
)

__all__ = [
    # Main entry point
    "generate_daily_digest",
    # Workflow
    "get_daily_digest_workflow",
    "create_daily_digest_workflow",
    # State
    "DailyDigestState",
    # Formatters
    "format_digest_markdown",
    "format_digest_html",
]
