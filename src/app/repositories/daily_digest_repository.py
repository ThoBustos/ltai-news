"""Repository for daily digest and reference database operations."""

from datetime import date, datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.core.logging import logger
from app.db.supabase import supabase
from app.models.daily_digest import (
    DailyDigestDB,
    DigestReference,
    DigestContentResponse,
    DigestMetrics,
)


class DailyDigestRepository:
    """Repository for daily digest database operations."""

    def __init__(self):
        self.client = supabase
        self.digests_table = "daily_digests"
        self.references_table = "digest_references"

    async def save_digest(
        self,
        publish_date: date,
        content: DigestContentResponse,
        metrics: DigestMetrics,
        formatted_markdown: str,
        formatted_html: str,
        source_video_ids: List[str],
        channels_included: List[str],
    ) -> Optional[str]:
        """Save a generated digest to the database.

        Args:
            publish_date: Date of the digest
            content: The full LLM-generated digest content
            metrics: Processing metrics
            formatted_markdown: Pre-rendered markdown
            formatted_html: Pre-rendered HTML
            source_video_ids: List of video IDs included
            channels_included: List of channel IDs included

        Returns:
            UUID of saved digest or None if failed
        """
        logger.info(f"Saving digest for {publish_date}")

        try:
            # Prepare data for database
            data = {
                "publish_date": publish_date.isoformat(),
                "title": content.title,
                "description": content.daily_tldr[:500] if content.daily_tldr else None,
                "formatted_html": formatted_html,
                "formatted_markdown": formatted_markdown,
                "content_json": content.model_dump(mode="json"),
                "source_video_ids": source_video_ids,
                "video_count": content.stats.video_count,
                "channels_included": channels_included,
                "keywords": content.keywords,
                "confidence_score": content.confidence_score,
                "total_tokens_input": metrics.input_tokens,
                "total_tokens_output": metrics.output_tokens,
                "cost_estimate": metrics.total_cost,
                "agent_metadata": {
                    "workflow_version": metrics.workflow_version,
                    "processing_time_seconds": metrics.processing_time_seconds,
                    "videos_analyzed": metrics.videos_analyzed,
                    "references_extracted": metrics.references_extracted,
                },
            }

            # Upsert by publish_date (unique constraint)
            result = self.client.table(self.digests_table).upsert(
                data,
                on_conflict="publish_date"
            ).execute()

            if result.data and len(result.data) > 0:
                digest_id = result.data[0].get("id")
                logger.info(f"Saved digest {digest_id} for {publish_date}")
                return str(digest_id)

            logger.warning(f"No data returned from digest upsert for {publish_date}")
            return None

        except Exception as e:
            logger.error(f"Failed to save digest for {publish_date}: {e}", exc_info=True)
            return None

    async def save_empty_digest(
        self,
        publish_date: date,
        reason: str = "No videos found",
    ) -> Optional[str]:
        """Save an empty digest record for days with no content.

        This allows the frontend to show "We processed this day - nothing relevant"
        rather than treating empty days as errors.

        Args:
            publish_date: Date of the digest
            reason: Explanation of why digest is empty

        Returns:
            UUID of saved digest or None if failed
        """
        logger.info(f"Saving empty digest for {publish_date}: {reason}")

        try:
            data = {
                "publish_date": publish_date.isoformat(),
                "title": "A Quiet One",
                "description": reason,
                "video_count": 0,
                "source_video_ids": [],
                "channels_included": [],
                "keywords": [],
                "content_json": {"empty": True, "reason": reason},
            }

            result = self.client.table(self.digests_table).upsert(
                data,
                on_conflict="publish_date"
            ).execute()

            if result.data and len(result.data) > 0:
                digest_id = result.data[0].get("id")
                logger.info(f"Saved empty digest {digest_id} for {publish_date}")
                return str(digest_id)

            logger.warning(f"No data returned from empty digest upsert for {publish_date}")
            return None

        except Exception as e:
            logger.error(f"Failed to save empty digest for {publish_date}: {e}", exc_info=True)
            return None

    async def get_digest_by_date(self, target_date: date) -> Optional[DailyDigestDB]:
        """Get digest for a specific date.

        Args:
            target_date: Date to get digest for

        Returns:
            DailyDigestDB if exists, None otherwise
        """
        try:
            result = (
                self.client.table(self.digests_table)
                .select("*")
                .eq("publish_date", target_date.isoformat())
                .single()
                .execute()
            )

            if result.data:
                return self._row_to_digest(result.data)
            return None

        except Exception as e:
            error_str = str(e)
            if "PGRST116" in error_str or "No rows" in error_str:
                return None
            logger.error(f"Failed to get digest for {target_date}: {e}", exc_info=True)
            return None

    async def get_digest_by_id(self, digest_id: str) -> Optional[DailyDigestDB]:
        """Get digest by UUID.

        Args:
            digest_id: UUID of the digest

        Returns:
            DailyDigestDB if exists, None otherwise
        """
        try:
            result = (
                self.client.table(self.digests_table)
                .select("*")
                .eq("id", digest_id)
                .single()
                .execute()
            )

            if result.data:
                return self._row_to_digest(result.data)
            return None

        except Exception as e:
            error_str = str(e)
            if "PGRST116" in error_str or "No rows" in error_str:
                return None
            logger.error(f"Failed to get digest {digest_id}: {e}", exc_info=True)
            return None

    async def has_digest(self, target_date: date) -> bool:
        """Check if a digest exists for the given date.

        Args:
            target_date: Date to check

        Returns:
            True if digest exists, False otherwise
        """
        try:
            result = (
                self.client.table(self.digests_table)
                .select("id")
                .eq("publish_date", target_date.isoformat())
                .limit(1)
                .execute()
            )
            return len(result.data) > 0

        except Exception as e:
            logger.error(f"Failed to check digest existence for {target_date}: {e}")
            return False

    async def mark_digest_sent(
        self,
        digest_id: str,
        recipient_count: int,
    ) -> bool:
        """Mark a digest as sent.

        Args:
            digest_id: UUID of the digest
            recipient_count: Number of recipients sent to

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.table(self.digests_table).update({
                "is_sent": True,
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "recipient_count": recipient_count,
            }).eq("id", digest_id).execute()

            logger.info(f"Marked digest {digest_id} as sent to {recipient_count} recipients")
            return True

        except Exception as e:
            logger.error(f"Failed to mark digest {digest_id} as sent: {e}", exc_info=True)
            return False

    async def get_recent_digests(self, limit: int = 7) -> List[DailyDigestDB]:
        """Get recent digests.

        Args:
            limit: Maximum number of digests to return

        Returns:
            List of recent digests ordered by publish_date desc
        """
        try:
            result = (
                self.client.table(self.digests_table)
                .select("*")
                .order("publish_date", desc=True)
                .limit(limit)
                .execute()
            )

            return [self._row_to_digest(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get recent digests: {e}", exc_info=True)
            return []

    # === Reference Operations ===

    async def upsert_references(
        self,
        references: List[Dict[str, Any]],
        digest_id: str,
        video_ids: List[str],
        target_date: date,
    ) -> int:
        """Upsert references from a digest.

        Args:
            references: List of reference dicts with type, name, author, url, description
            digest_id: UUID of the digest
            video_ids: List of video IDs where references were mentioned
            target_date: Date of first mention

        Returns:
            Number of references upserted
        """
        logger.info(f"Upserting {len(references)} references for digest {digest_id}")
        upserted = 0

        for ref in references:
            try:
                ref_type = ref.get("reference_type") or ref.get("type", "concept")
                name = ref.get("name", "").strip()
                if not name:
                    continue

                # Check if reference exists
                existing = (
                    self.client.table(self.references_table)
                    .select("id, mention_count, digest_ids, video_ids")
                    .eq("reference_type", ref_type)
                    .eq("name", name)
                    .single()
                    .execute()
                )

                if existing.data:
                    # Update existing reference
                    existing_data = existing.data
                    existing_digest_ids = existing_data.get("digest_ids", []) or []
                    existing_video_ids = existing_data.get("video_ids", []) or []

                    # Add new IDs (avoid duplicates)
                    updated_digest_ids = list(set(existing_digest_ids + [digest_id]))
                    updated_video_ids = list(set(existing_video_ids + video_ids))

                    self.client.table(self.references_table).update({
                        "mention_count": existing_data.get("mention_count", 0) + 1,
                        "digest_ids": updated_digest_ids,
                        "video_ids": updated_video_ids,
                        "description": ref.get("description") or existing_data.get("description"),
                        "url": ref.get("url") or existing_data.get("url"),
                    }).eq("id", existing_data["id"]).execute()

                else:
                    # Insert new reference
                    self.client.table(self.references_table).insert({
                        "reference_type": ref_type,
                        "name": name,
                        "author": ref.get("author"),
                        "url": ref.get("url"),
                        "description": ref.get("description"),
                        "first_seen_date": target_date.isoformat(),
                        "mention_count": 1,
                        "digest_ids": [digest_id],
                        "video_ids": video_ids,
                        "metadata": ref.get("metadata", {}),
                    }).execute()

                upserted += 1

            except Exception as e:
                error_str = str(e)
                # Ignore "no rows" errors from single() when reference doesn't exist
                if "PGRST116" not in error_str and "No rows" not in error_str:
                    logger.warning(f"Failed to upsert reference {ref.get('name')}: {e}")

        logger.info(f"Upserted {upserted} references for digest {digest_id}")
        return upserted

    async def get_reference_by_name(
        self,
        reference_type: str,
        name: str,
    ) -> Optional[DigestReference]:
        """Get a reference by type and name.

        Args:
            reference_type: Type of reference (book, concept, etc.)
            name: Name of the reference

        Returns:
            DigestReference if found, None otherwise
        """
        try:
            result = (
                self.client.table(self.references_table)
                .select("*")
                .eq("reference_type", reference_type)
                .eq("name", name)
                .single()
                .execute()
            )

            if result.data:
                return self._row_to_reference(result.data)
            return None

        except Exception as e:
            error_str = str(e)
            if "PGRST116" in error_str or "No rows" in error_str:
                return None
            logger.error(f"Failed to get reference {reference_type}:{name}: {e}")
            return None

    async def get_top_references(
        self,
        reference_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[DigestReference]:
        """Get most-mentioned references.

        Args:
            reference_type: Optional filter by type
            limit: Maximum number to return

        Returns:
            List of references ordered by mention_count desc
        """
        try:
            query = (
                self.client.table(self.references_table)
                .select("*")
                .order("mention_count", desc=True)
                .limit(limit)
            )

            if reference_type:
                query = query.eq("reference_type", reference_type)

            result = query.execute()
            return [self._row_to_reference(row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get top references: {e}", exc_info=True)
            return []

    async def get_reference_history(self, name: str) -> List[Dict[str, Any]]:
        """Get cross-day history for a reference.

        Args:
            name: Name of the reference to look up

        Returns:
            List of dicts with digest dates and video IDs where mentioned
        """
        try:
            result = (
                self.client.table(self.references_table)
                .select("*")
                .ilike("name", f"%{name}%")
                .execute()
            )

            history = []
            for row in result.data:
                history.append({
                    "reference_type": row.get("reference_type"),
                    "name": row.get("name"),
                    "first_seen": row.get("first_seen_date"),
                    "mention_count": row.get("mention_count"),
                    "digest_ids": row.get("digest_ids", []),
                    "video_ids": row.get("video_ids", []),
                })

            return history

        except Exception as e:
            logger.error(f"Failed to get reference history for {name}: {e}")
            return []

    # === Helper Methods ===

    def _row_to_digest(self, row: Dict[str, Any]) -> DailyDigestDB:
        """Convert database row to DailyDigestDB model."""
        return DailyDigestDB(
            id=UUID(row["id"]) if row.get("id") else None,
            publish_date=date.fromisoformat(row["publish_date"]) if row.get("publish_date") else None,
            title=row.get("title", ""),
            description=row.get("description"),
            formatted_html=row.get("formatted_html"),
            formatted_markdown=row.get("formatted_markdown"),
            content_json=row.get("content_json"),
            source_video_ids=row.get("source_video_ids", []),
            source_tweet_ids=row.get("source_tweet_ids", []),
            video_count=row.get("video_count"),
            channels_included=row.get("channels_included", []),
            keywords=row.get("keywords", []),
            confidence_score=float(row["confidence_score"]) if row.get("confidence_score") else None,
            total_tokens_input=row.get("total_tokens_input"),
            total_tokens_output=row.get("total_tokens_output"),
            cost_estimate=float(row["cost_estimate"]) if row.get("cost_estimate") else None,
            agent_metadata=row.get("agent_metadata"),
            eval_score=float(row["eval_score"]) if row.get("eval_score") else None,
            is_sent=row.get("is_sent", False),
            sent_at=datetime.fromisoformat(row["sent_at"]) if row.get("sent_at") else None,
            recipient_count=row.get("recipient_count", 0),
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row.get("updated_at") else None,
        )

    def _row_to_reference(self, row: Dict[str, Any]) -> DigestReference:
        """Convert database row to DigestReference model."""
        return DigestReference(
            id=UUID(row["id"]) if row.get("id") else None,
            reference_type=row.get("reference_type", "concept"),
            name=row.get("name", ""),
            author=row.get("author"),
            url=row.get("url"),
            description=row.get("description"),
            first_seen_date=date.fromisoformat(row["first_seen_date"]) if row.get("first_seen_date") else None,
            mention_count=row.get("mention_count", 1),
            digest_ids=[UUID(d) for d in (row.get("digest_ids") or [])],
            video_ids=row.get("video_ids", []),
            metadata=row.get("metadata", {}),
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row.get("updated_at") else None,
        )
