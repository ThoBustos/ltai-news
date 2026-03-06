"""Service for X thread generation and posting."""

from datetime import date, datetime, timezone
from typing import Optional, Dict, Any

from app.core.logging import logger
from app.core.utils.time_window import parse_date
from app.models.pipeline import XThreadResult
from app.repositories.daily_digest_repository import DailyDigestRepository
from app.agents.x_thread.workflow import generate_and_post_x_thread


class XThreadService:
    """Service for generating and posting X threads from digests.

    This service:
    - Takes a digest date
    - Generates an optimized X thread using LLM
    - Posts the thread to X/Twitter
    - Updates the digest record with tweet IDs
    """

    def __init__(self):
        """Initialize X thread service."""
        self.service_name = "x_thread_service"
        self.digest_repo = DailyDigestRepository()
        logger.info("Initialized XThreadService")

    async def post_digest_to_x(self, target_date: date) -> XThreadResult:
        """Generate and post X thread for a digest.

        Args:
            target_date: Date of the digest to post

        Returns:
            XThreadResult with posting status
        """
        logger.info(f"Posting digest to X for {target_date}")

        started_at = datetime.now(timezone.utc)
        errors = []

        try:
            # Check if digest exists
            digest = await self.digest_repo.get_digest_by_date(target_date)

            if not digest:
                error_msg = f"No digest found for {target_date}"
                logger.error(error_msg)
                return XThreadResult(
                    thread_posted=False,
                    tweet_count=0,
                    tweet_ids=None,
                    thread_url=None,
                    errors=[error_msg],
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc)
                )

            # Check if already posted
            if digest.source_tweet_ids and len(digest.source_tweet_ids) > 0:
                logger.info(f"Digest for {target_date} already posted to X")
                # Reconstruct thread URL from first tweet ID
                thread_url = f"https://x.com/i/status/{digest.source_tweet_ids[0]}"
                return XThreadResult(
                    thread_posted=True,
                    tweet_count=len(digest.source_tweet_ids),
                    tweet_ids=digest.source_tweet_ids,
                    thread_url=thread_url,
                    errors=["Already posted - returning existing thread"],
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc)
                )

            # Generate and post thread
            result = await generate_and_post_x_thread(
                target_date=target_date,
                digest_id=digest.id
            )

            if not result:
                error_msg = "X thread workflow returned no result"
                logger.error(error_msg)
                return XThreadResult(
                    thread_posted=False,
                    tweet_count=0,
                    tweet_ids=None,
                    thread_url=None,
                    errors=[error_msg],
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc)
                )

            # Extract result data
            success = result.get("success", False)
            tweet_ids = result.get("tweet_ids", [])
            thread_url = result.get("thread_url")
            workflow_errors = result.get("errors", [])

            if workflow_errors:
                errors.extend(workflow_errors)

            completed_at = datetime.now(timezone.utc)

            return XThreadResult(
                thread_posted=success,
                tweet_count=len(tweet_ids),
                tweet_ids=tweet_ids if success else None,
                thread_url=thread_url if success else None,
                errors=errors,
                started_at=started_at,
                completed_at=completed_at
            )

        except Exception as e:
            logger.error(f"Failed to post digest to X for {target_date}: {e}", exc_info=True)
            errors.append(f"X thread posting failed: {str(e)}")

            return XThreadResult(
                thread_posted=False,
                tweet_count=0,
                tweet_ids=None,
                thread_url=None,
                errors=errors,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc)
            )

    async def generate_thread_preview(self, target_date: date) -> Optional[Dict[str, Any]]:
        """Generate X thread without posting (preview mode).

        Args:
            target_date: Date of the digest

        Returns:
            Dict with generated tweets if successful, None if failed
        """
        logger.info(f"Generating X thread preview for {target_date}")

        try:
            # Check if digest exists
            digest = await self.digest_repo.get_digest_by_date(target_date)

            if not digest:
                logger.error(f"No digest found for {target_date}")
                return None

            # Generate thread in dry_run mode (don't post to X)
            result = await generate_and_post_x_thread(
                target_date=target_date,
                digest_id=str(digest.id),
                dry_run=True
            )

            if not result:
                logger.error("X thread workflow returned no result")
                return None

            # Build preview response
            thread_tweets = result.get("thread_tweets", [])
            metrics = result.get("metrics", {})
            errors = result.get("errors", [])

            return {
                "target_date": target_date.isoformat(),
                "digest_id": str(digest.id),
                "digest_title": digest.title if hasattr(digest, 'title') else None,
                "video_count": digest.video_count if hasattr(digest, 'video_count') else None,
                "thread_tweets": thread_tweets,
                "tweet_count": len(thread_tweets),
                "metrics": {
                    "input_tokens": metrics.input_tokens if hasattr(metrics, 'input_tokens') else None,
                    "output_tokens": metrics.output_tokens if hasattr(metrics, 'output_tokens') else None,
                    "total_tokens": metrics.total_tokens if hasattr(metrics, 'total_tokens') else None,
                    "cost_usd": metrics.total_cost if hasattr(metrics, 'total_cost') else None,
                    "processing_time_seconds": metrics.processing_time_seconds if hasattr(metrics, 'processing_time_seconds') else None,
                } if metrics else None,
                "errors": errors
            }

        except Exception as e:
            logger.error(f"Failed to generate thread preview for {target_date}: {e}", exc_info=True)
            return None
