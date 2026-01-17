"""LangGraph workflow definition for weekly digest generation."""

from typing import Optional, Tuple
from datetime import date, timedelta

from langgraph.graph import StateGraph, START, END

from app.core.logging import logger
from app.core.opik_manager import opik_manager
from app.config.settings import settings
from app.models.weekly_digest import WeeklyDigestGenerationResult
from app.agents.weekly_digest.state import WeeklyDigestState
from app.agents.weekly_digest.nodes import (
    load_week_data_node,
    generate_weekly_node,
    save_results_node,
)


def get_week_bounds(any_date: date) -> Tuple[date, date]:
    """Get Monday and Sunday for the week containing any_date.

    Args:
        any_date: Any date in the target week

    Returns:
        Tuple of (Monday, Sunday) for that week
    """
    monday = any_date - timedelta(days=any_date.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def get_last_complete_week_bounds() -> Tuple[date, date]:
    """Get bounds for the most recently completed week.

    Returns:
        Tuple of (Monday, Sunday) for the last complete week
    """
    today = date.today()
    # Calculate days since last Sunday
    days_since_sunday = (today.weekday() + 1) % 7
    # If today is Sunday (days_since_sunday == 0), go back a full week
    last_sunday = today - timedelta(days=days_since_sunday if days_since_sunday > 0 else 7)
    last_monday = last_sunday - timedelta(days=6)
    return last_monday, last_sunday


def create_weekly_digest_workflow():
    """Create weekly digest workflow with Opik tracking.

    The workflow has three nodes:
    1. load_week_data_node: Load daily digests and references for the week
    2. generate_weekly_node: Generate weekly content using LLM
    3. save_results_node: Save weekly digest to database

    Returns:
        Compiled and tracked LangGraph workflow
    """
    workflow = StateGraph(WeeklyDigestState)

    # Add nodes
    workflow.add_node("load_week_data", load_week_data_node)
    workflow.add_node("generate_weekly", generate_weekly_node)
    workflow.add_node("save_results", save_results_node)

    # Define sequential edges
    workflow.add_edge(START, "load_week_data")
    workflow.add_edge("load_week_data", "generate_weekly")
    workflow.add_edge("generate_weekly", "save_results")
    workflow.add_edge("save_results", END)

    # Compile workflow
    compiled_workflow = workflow.compile()

    # Wrap with Opik tracking
    tracked_workflow = opik_manager.track_workflow(
        compiled_workflow,
        workflow_name="weekly-digest",
        tags=["digest", "newsletter", "weekly", settings.analysis_model_name]
    )

    return tracked_workflow


def get_weekly_digest_workflow():
    """Get configured weekly digest workflow instance."""
    return create_weekly_digest_workflow()


async def generate_weekly_digest(week_start: date) -> Optional[WeeklyDigestGenerationResult]:
    """Generate a weekly digest for the specified week.

    This is the main entry point for weekly digest generation.

    Args:
        week_start: Monday of the target week (must be a Monday)

    Returns:
        WeeklyDigestGenerationResult if successful, None if failed

    Raises:
        ValueError: If week_start is not a Monday
    """
    # Validate it's a Monday
    if week_start.weekday() != 0:
        raise ValueError(f"week_start must be a Monday, got {week_start.strftime('%A')}")

    week_end = week_start + timedelta(days=6)
    logger.info(f"Starting weekly digest workflow for {week_start} to {week_end}")

    try:
        workflow = get_weekly_digest_workflow()
        initial_state = WeeklyDigestState(
            week_start_date=week_start.isoformat(),
            week_end_date=week_end.isoformat()
        )

        final_state = await workflow.ainvoke(initial_state)

        # Check for errors
        errors = final_state.get("errors", [])
        if errors:
            logger.error(f"Weekly digest workflow completed with errors: {errors}")

        # Check for required outputs
        weekly_content = final_state.get("weekly_content")
        digest_id = final_state.get("weekly_digest_id")
        metrics = final_state.get("metrics", {})
        is_empty = final_state.get("is_empty", False)

        # Handle empty digest case
        if is_empty and digest_id:
            logger.info(f"Empty weekly digest saved for {week_start}: no content available")
            return WeeklyDigestGenerationResult(
                success=True,
                is_empty=True,
                weekly_digest_id=digest_id,
                week_start=week_start.isoformat(),
                week_end=week_end.isoformat(),
                errors=errors,
            )

        if not weekly_content or not digest_id:
            logger.error("Weekly digest workflow completed but no content or ID generated")
            return WeeklyDigestGenerationResult(
                success=False,
                week_start=week_start.isoformat(),
                week_end=week_end.isoformat(),
                errors=errors or ["No weekly content generated"],
            )

        # Build successful result
        result = WeeklyDigestGenerationResult(
            success=True,
            weekly_digest_id=digest_id,
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
            title=weekly_content.title,
            days_with_content=final_state.get("days_with_content", 0),
            videos_included=weekly_content.stats.total_videos,
            references_aggregated=len(weekly_content.weekly_references),
            total_tokens=metrics.get("input_tokens", 0) + metrics.get("output_tokens", 0),
            total_cost=metrics.get("total_cost", 0.0),
            processing_time_seconds=metrics.get("processing_time_seconds", 0.0),
            errors=errors,
            markdown_preview=final_state.get("formatted_markdown", "")[:500] if final_state.get("formatted_markdown") else None,
        )

        logger.info(
            f"Weekly digest completed for {week_start} to {week_end}: "
            f"{result.days_with_content} days, "
            f"{result.videos_included} videos, "
            f"${result.total_cost:.4f}"
        )

        return result

    except Exception as e:
        logger.error("Weekly digest workflow failed for {}: {}", week_start, e, exc_info=True)
        return WeeklyDigestGenerationResult(
            success=False,
            week_start=week_start.isoformat(),
            week_end=(week_start + timedelta(days=6)).isoformat(),
            errors=[f"Workflow failed: {e!s}"],
        )
