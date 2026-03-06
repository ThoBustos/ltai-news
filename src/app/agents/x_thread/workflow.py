"""LangGraph workflow definition for X thread generation and posting."""

from typing import Optional, Dict, Any
from datetime import date

from langgraph.graph import StateGraph, START, END

from app.core.logging import logger
from app.core.opik_manager import opik_manager
from app.config.settings import settings
from app.agents.x_thread.state import XThreadState
from app.agents.x_thread.nodes import (
    load_digest_node,
    generate_thread_node,
    post_to_x_node,
)


def create_x_thread_workflow(dry_run: bool = False):
    """Create X thread workflow with Opik tracking.

    The workflow has three nodes:
    1. load_digest_node: Load digest data and channel metadata
    2. generate_thread_node: Generate X thread using LLM
    3. post_to_x_node: Post thread to X via API (skipped if dry_run=True)

    Args:
        dry_run: If True, skip posting to X (for testing)

    Returns:
        Compiled and tracked LangGraph workflow
    """
    workflow = StateGraph(XThreadState)

    # Add nodes
    workflow.add_node("load_digest", load_digest_node)
    workflow.add_node("generate_thread", generate_thread_node)
    workflow.add_node("post_to_x", post_to_x_node)

    # Define edges
    workflow.add_edge(START, "load_digest")
    workflow.add_edge("load_digest", "generate_thread")

    if dry_run:
        # Skip posting in dry_run mode
        workflow.add_edge("generate_thread", END)
    else:
        # Normal flow: post to X
        workflow.add_edge("generate_thread", "post_to_x")
        workflow.add_edge("post_to_x", END)

    # Compile workflow
    compiled_workflow = workflow.compile()

    # Wrap with Opik tracking
    tracked_workflow = opik_manager.track_workflow(
        compiled_workflow,
        workflow_name="x-thread",
        tags=["x-thread", "twitter", "social-media", settings.analysis_model_name]
    )

    return tracked_workflow


def get_x_thread_workflow(dry_run: bool = False):
    """Get configured X thread workflow instance.

    Args:
        dry_run: If True, skip posting to X (for testing)
    """
    return create_x_thread_workflow(dry_run=dry_run)


async def generate_and_post_x_thread(
    target_date: date,
    digest_id: str = None,
    dry_run: bool = False
) -> Optional[Dict[str, Any]]:
    """Generate and post X thread for the specified digest.

    This is the main entry point for X thread posting.

    Args:
        target_date: Date of the digest (can be date object or str)
        digest_id: UUID of the digest (optional for dry_run)
        dry_run: If True, skip posting to X (for testing)

    Returns:
        Dict with result data if successful, None if failed
    """
    # Handle both date object and string
    if isinstance(target_date, date):
        date_str = target_date.isoformat()
    else:
        date_str = target_date

    logger.info(f"Starting X thread workflow for {date_str}" + (" (DRY RUN)" if dry_run else ""))

    try:
        workflow = get_x_thread_workflow(dry_run=dry_run)
        initial_state = XThreadState(
            target_date=date_str,
            digest_id=digest_id or ""
        )

        final_state = await workflow.ainvoke(initial_state)

        # Check for errors
        errors = final_state.get("errors", [])
        if errors:
            logger.error(f"X thread workflow completed with errors: {errors}")

        # Check for required outputs
        thread_tweets = final_state.get("thread_tweets", [])
        tweet_ids = final_state.get("tweet_ids", [])
        thread_url = final_state.get("thread_url")
        metrics = final_state.get("metrics", {})

        if not thread_tweets:
            logger.error("X thread workflow completed but no tweets generated")
            return {
                "success": False,
                "target_date": date_str,
                "errors": errors or ["No tweets generated"],
            }

        # Build result
        result = {
            "success": len(tweet_ids) > 0 or dry_run,  # Success if posted OR dry_run mode
            "target_date": date_str,
            "digest_id": digest_id or "",
            "tweet_count": len(thread_tweets),  # Use thread_tweets for dry_run
            "thread_tweets": thread_tweets,  # Include generated tweets
            "tweet_ids": tweet_ids,
            "thread_url": thread_url,
            "metrics": metrics,
            "errors": errors,
        }

        if dry_run:
            logger.info(
                f"X thread generated (DRY RUN) for {date_str}: "
                f"{len(thread_tweets)} tweets"
            )
        elif result["success"]:
            logger.info(
                f"X thread posted for {date_str}: "
                f"{len(tweet_ids)} tweets, "
                f"URL: {thread_url}"
            )
        else:
            logger.warning(f"X thread generation completed but posting failed for {date_str}")

        return result

    except Exception as e:
        logger.error(f"X thread workflow failed for {date_str}: {e}", exc_info=True)
        return {
            "success": False,
            "target_date": date_str,
            "errors": [f"Workflow failed: {str(e)}"],
        }
