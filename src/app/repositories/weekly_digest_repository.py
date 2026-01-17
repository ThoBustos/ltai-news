"""Repository for weekly digest database operations."""

from datetime import date, datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.core.logging import logger
from app.db.supabase import supabase
from app.models.weekly_digest import (
    WeeklyDigestDB,
    WeeklyContentResponse,
)


class WeeklyDigestRepository:
    """Repository for weekly digest database operations."""

    def __init__(self):
        self.client = supabase
        self.table = "weekly_digests"

    async def save_weekly_digest(
        self,
        week_start: date,
        week_end: date,
        content: WeeklyContentResponse,
        formatted_markdown: str,
        formatted_html: str,
        daily_digest_ids: List[str],
        metrics: Dict[str, Any],
    ) -> Optional[str]:
        """Save a generated weekly digest to the database.

        Args:
            week_start: Monday of the week
            week_end: Sunday of the week
            content: The full LLM-generated weekly content
            formatted_markdown: Pre-rendered markdown
            formatted_html: Pre-rendered HTML
            daily_digest_ids: List of daily digest UUIDs included
            metrics: Processing metrics dict

        Returns:
            UUID of saved digest or None if failed
        """
        logger.info(f"Saving weekly digest for {week_start} to {week_end}")

        try:
            data = {
                "week_start_date": week_start.isoformat(),
                "week_end_date": week_end.isoformat(),
                "title": content.title,
                "description": content.description,
                "formatted_html": formatted_html,
                "formatted_markdown": formatted_markdown,
                "content_json": content.model_dump(mode="json"),
                "source_daily_digest_ids": daily_digest_ids,
                "days_with_content": content.stats.days_covered,
                "total_videos": content.stats.total_videos,
                "channels_included": content.stats.channels,
                "keywords": content.keywords,
                "confidence_score": content.confidence_score,
                "total_tokens_input": metrics.get("input_tokens", 0),
                "total_tokens_output": metrics.get("output_tokens", 0),
                "cost_estimate": metrics.get("total_cost", 0.0),
                "agent_metadata": {
                    "workflow_version": metrics.get("workflow_version", "1.0"),
                    "processing_time_seconds": metrics.get("processing_time_seconds", 0.0),
                },
            }

            # Upsert by week_start_date (unique constraint)
            result = self.client.table(self.table).upsert(
                data,
                on_conflict="week_start_date"
            ).execute()

            if result.data and len(result.data) > 0:
                digest_id = result.data[0].get("id")
                logger.info(f"Saved weekly digest {digest_id} for {week_start}")
                return str(digest_id)

            logger.warning(f"No data returned from weekly digest upsert for {week_start}")
            return None

        except Exception as e:
            logger.error(f"Failed to save weekly digest for {week_start}: {e}", exc_info=True)
            return None

    async def save_empty_weekly_digest(
        self,
        week_start: date,
        week_end: date,
        reason: str = "No daily digests found",
    ) -> Optional[str]:
        """Save an empty weekly digest record for weeks with no content.

        Args:
            week_start: Monday of the week
            week_end: Sunday of the week
            reason: Explanation of why digest is empty

        Returns:
            UUID of saved digest or None if failed
        """
        logger.info(f"Saving empty weekly digest for {week_start}: {reason}")

        try:
            data = {
                "week_start_date": week_start.isoformat(),
                "week_end_date": week_end.isoformat(),
                "title": "A Quiet Week",
                "description": reason,
                "days_with_content": 0,
                "total_videos": 0,
                "source_daily_digest_ids": [],
                "channels_included": [],
                "keywords": [],
                "content_json": {"empty": True, "reason": reason},
            }

            result = self.client.table(self.table).upsert(
                data,
                on_conflict="week_start_date"
            ).execute()

            if result.data and len(result.data) > 0:
                digest_id = result.data[0].get("id")
                logger.info(f"Saved empty weekly digest {digest_id} for {week_start}")
                return str(digest_id)

            logger.warning(f"No data returned from empty weekly digest upsert for {week_start}")
            return None

        except Exception as e:
            logger.error(f"Failed to save empty weekly digest for {week_start}: {e}", exc_info=True)
            return None

    async def get_weekly_digest_by_date(self, week_start: date) -> Optional[WeeklyDigestDB]:
        """Get weekly digest by week start date.

        Args:
            week_start: Monday of the target week

        Returns:
            WeeklyDigestDB if exists, None otherwise
        """
        try:
            result = (
                self.client.table(self.table)
                .select("*")
                .eq("week_start_date", week_start.isoformat())
                .single()
                .execute()
            )

            if result.data:
                return self._row_to_weekly_digest(result.data)
            return None

        except Exception as e:
            error_str = str(e)
            if "PGRST116" in error_str or "No rows" in error_str:
                return None
            logger.error(f"Failed to get weekly digest for {week_start}: {e}", exc_info=True)
            return None

    async def get_weekly_digest_by_id(self, digest_id: str) -> Optional[WeeklyDigestDB]:
        """Get weekly digest by UUID.

        Args:
            digest_id: UUID of the weekly digest

        Returns:
            WeeklyDigestDB if exists, None otherwise
        """
        try:
            result = (
                self.client.table(self.table)
                .select("*")
                .eq("id", digest_id)
                .single()
                .execute()
            )

            if result.data:
                return self._row_to_weekly_digest(result.data)
            return None

        except Exception as e:
            error_str = str(e)
            if "PGRST116" in error_str or "No rows" in error_str:
                return None
            logger.error(f"Failed to get weekly digest {digest_id}: {e}", exc_info=True)
            return None

    async def get_latest_weekly_digest(self) -> Optional[WeeklyDigestDB]:
        """Get the most recent weekly digest.

        Returns:
            Most recent WeeklyDigestDB or None if no digests exist
        """
        try:
            result = (
                self.client.table(self.table)
                .select("*")
                .order("week_start_date", desc=True)
                .limit(1)
                .execute()
            )

            if result.data and len(result.data) > 0:
                return self._row_to_weekly_digest(result.data[0])
            return None

        except Exception as e:
            logger.error(f"Failed to get latest weekly digest: {e}", exc_info=True)
            return None

    async def get_recent_weekly_digests(self, limit: int = 4) -> List[WeeklyDigestDB]:
        """Get recent weekly digests.

        Args:
            limit: Maximum number of digests to return

        Returns:
            List of recent weekly digests ordered by week_start_date desc
        """
        try:
            result = (
                self.client.table(self.table)
                .select("*")
                .order("week_start_date", desc=True)
                .limit(limit)
                .execute()
            )

            return [self._row_to_weekly_digest(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get recent weekly digests: {e}", exc_info=True)
            return []

    async def has_weekly_digest(self, week_start: date) -> bool:
        """Check if a weekly digest exists for the given week.

        Args:
            week_start: Monday of the week to check

        Returns:
            True if digest exists, False otherwise
        """
        try:
            result = (
                self.client.table(self.table)
                .select("id")
                .eq("week_start_date", week_start.isoformat())
                .limit(1)
                .execute()
            )
            return len(result.data) > 0

        except Exception as e:
            logger.error(f"Failed to check weekly digest existence for {week_start}: {e}")
            return False

    async def mark_weekly_digest_sent(
        self,
        digest_id: str,
        recipient_count: int,
    ) -> bool:
        """Mark a weekly digest as sent.

        Args:
            digest_id: UUID of the weekly digest
            recipient_count: Number of recipients sent to

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.table(self.table).update({
                "is_sent": True,
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "recipient_count": recipient_count,
            }).eq("id", digest_id).execute()

            logger.info(f"Marked weekly digest {digest_id} as sent to {recipient_count} recipients")
            return True

        except Exception as e:
            logger.error(f"Failed to mark weekly digest {digest_id} as sent: {e}", exc_info=True)
            return False

    def _row_to_weekly_digest(self, row: Dict[str, Any]) -> WeeklyDigestDB:
        """Convert database row to WeeklyDigestDB model."""
        return WeeklyDigestDB(
            id=UUID(row["id"]) if row.get("id") else None,
            week_start_date=date.fromisoformat(row["week_start_date"]) if row.get("week_start_date") else None,
            week_end_date=date.fromisoformat(row["week_end_date"]) if row.get("week_end_date") else None,
            title=row.get("title", ""),
            description=row.get("description"),
            formatted_html=row.get("formatted_html"),
            formatted_markdown=row.get("formatted_markdown"),
            content_json=row.get("content_json"),
            source_daily_digest_ids=[UUID(d) for d in (row.get("source_daily_digest_ids") or [])],
            days_with_content=row.get("days_with_content", 0),
            total_videos=row.get("total_videos", 0),
            channels_included=row.get("channels_included", []),
            keywords=row.get("keywords", []),
            confidence_score=float(row["confidence_score"]) if row.get("confidence_score") else None,
            total_tokens_input=row.get("total_tokens_input"),
            total_tokens_output=row.get("total_tokens_output"),
            cost_estimate=float(row["cost_estimate"]) if row.get("cost_estimate") else None,
            agent_metadata=row.get("agent_metadata"),
            is_sent=row.get("is_sent", False),
            sent_at=datetime.fromisoformat(row["sent_at"]) if row.get("sent_at") else None,
            recipient_count=row.get("recipient_count", 0),
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row.get("updated_at") else None,
        )
