#!/usr/bin/env python3
"""Test X thread generation to diagnose truncation issues."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from app.agents.x_thread.workflow import generate_and_post_x_thread
from app.core.logging import logger


async def test_thread_generation():
    """Test thread generation for a specific date."""
    target_date = "2026-01-25"

    logger.info(f"Testing X thread generation for {target_date}")

    # Run workflow with dry_run=True (don't post to X)
    result = await generate_and_post_x_thread(
        target_date=target_date,
        dry_run=True  # Don't actually post
    )

    # Check results
    if result.get("errors"):
        logger.error(f"Errors: {result['errors']}")
        return False

    thread_tweets = result.get("thread_tweets", [])
    logger.info(f"\n{'='*60}")
    logger.info(f"Generated {len(thread_tweets)} tweets:")
    logger.info(f"{'='*60}")

    for i, tweet in enumerate(thread_tweets, 1):
        logger.info(f"\nTweet {i} ({len(tweet)} chars):")
        logger.info(f"{tweet}")
        logger.info(f"{'-'*60}")

        if len(tweet) > 280:
            logger.warning(f"⚠️  Tweet {i} exceeds 280 chars!")

    # Show metrics
    metrics = result.get("metrics")
    if metrics:
        logger.info(f"\n{'='*60}")
        logger.info(f"Metrics:")
        logger.info(f"  Input tokens: {metrics.input_tokens}")
        logger.info(f"  Output tokens: {metrics.output_tokens}")
        logger.info(f"  Total tokens: {metrics.total_tokens}")
        logger.info(f"  Cost: ${metrics.total_cost:.4f}")
        logger.info(f"  Time: {metrics.processing_time_seconds:.2f}s")
        logger.info(f"{'='*60}")

    return True


if __name__ == "__main__":
    success = asyncio.run(test_thread_generation())
    sys.exit(0 if success else 1)
