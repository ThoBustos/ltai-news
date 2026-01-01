"""LangGraph workflow definition for daily digest generation."""

from typing import Optional
from datetime import date

from langgraph.graph import StateGraph, START, END

from app.core.logging import logger
from app.core.opik_manager import opik_manager
from app.config.settings import settings
from app.models.daily_digest import DigestGenerationResult
from app.agents.daily_digest.state import DailyDigestState
from app.agents.daily_digest.nodes import (
    load_data_node,
    generate_digest_node,
    save_results_node,
)


def create_daily_digest_workflow():
    """Create daily digest workflow with Opik tracking.

    The workflow has three nodes:
    1. load_data_node: Load video analyses and metadata for target date
    2. generate_digest_node: Generate digest content using LLM
    3. save_results_node: Save digest and extract references

    Returns:
        Compiled and tracked LangGraph workflow
    """
    workflow = StateGraph(DailyDigestState)

    # Add nodes
    workflow.add_node("load_data", load_data_node)
    workflow.add_node("generate_digest", generate_digest_node)
    workflow.add_node("save_results", save_results_node)

    # Define sequential edges
    workflow.add_edge(START, "load_data")
    workflow.add_edge("load_data", "generate_digest")
    workflow.add_edge("generate_digest", "save_results")
    workflow.add_edge("save_results", END)

    # Compile workflow
    compiled_workflow = workflow.compile()

    # Wrap with Opik tracking
    tracked_workflow = opik_manager.track_workflow(
        compiled_workflow,
        workflow_name="daily-digest",
        tags=["digest", "newsletter", settings.analysis_model_name, "compound-knowledge"]
    )

    return tracked_workflow


def get_daily_digest_workflow():
    """Get configured daily digest workflow instance."""
    return create_daily_digest_workflow()


async def generate_daily_digest(target_date: date) -> Optional[DigestGenerationResult]:
    """Generate a daily digest for the specified date.

    This is the main entry point for digest generation.

    Args:
        target_date: Date to generate digest for

    Returns:
        DigestGenerationResult if successful, None if failed
    """
    date_str = target_date.isoformat()
    logger.info(f"Starting daily digest workflow for {date_str}")

    try:
        workflow = get_daily_digest_workflow()
        initial_state = DailyDigestState(target_date=date_str)

        final_state = await workflow.ainvoke(initial_state)

        # Check for errors
        errors = final_state.get("errors", [])
        if errors:
            logger.error(f"Digest workflow completed with errors: {errors}")

        # Check for required outputs
        digest_content = final_state.get("digest_content")
        digest_id = final_state.get("digest_id")
        metrics = final_state.get("metrics")

        if not digest_content or not digest_id:
            logger.error("Digest workflow completed but no content or ID generated")
            return DigestGenerationResult(
                success=False,
                publish_date=date_str,
                errors=errors or ["No digest content generated"],
            )

        # Build successful result
        result = DigestGenerationResult(
            success=True,
            digest_id=digest_id,
            publish_date=date_str,
            title=digest_content.title,
            videos_included=digest_content.stats.video_count,
            channels_included=len(digest_content.stats.channels),
            references_extracted=final_state.get("references_extracted", 0),
            total_tokens=(metrics.input_tokens + metrics.output_tokens) if metrics else 0,
            total_cost=metrics.total_cost if metrics else 0.0,
            processing_time_seconds=metrics.processing_time_seconds if metrics else 0.0,
            errors=errors,
            markdown_preview=final_state.get("formatted_markdown", "")[:500] if final_state.get("formatted_markdown") else None,
        )

        logger.info(
            f"Daily digest completed for {date_str}: "
            f"{result.videos_included} videos, "
            f"{result.references_extracted} references, "
            f"${result.total_cost:.4f}"
        )

        return result

    except Exception as e:
        logger.error(f"Daily digest workflow failed for {date_str}: {e}", exc_info=True)
        return DigestGenerationResult(
            success=False,
            publish_date=date_str,
            errors=[f"Workflow failed: {str(e)}"],
        )
