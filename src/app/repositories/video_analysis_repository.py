"""Repository for video analysis data with JSONB handling."""

import json
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from app.core.logging import logger
from app.db.supabase import supabase
from app.models.video_analysis import VideoAnalysisComplete
from app.models.video import VideoProcessingStatus


def _json_serializer(obj):
    """Custom JSON serializer for datetime objects."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


class VideoAnalysisRepository:
    """Repository for video analysis operations with proper JSONB handling."""

    def __init__(self):
        self.client = supabase
        self.table_name = "video_processed_data"

    async def save_analysis(self, analysis: VideoAnalysisComplete) -> bool:
        """Save complete video analysis to database with upsert pattern.

        Args:
            analysis: Complete analysis data to save

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Saving analysis for video {analysis.video_id}")

        try:
            # Prepare data - convert Pydantic to database format
            # NOTE: Pass Python objects directly for JSONB columns (Supabase handles serialization)
            data = {
                "video_id": analysis.video_id,
                "summary": analysis.tldr,
                "analysis": analysis.detailed_insights,
                "key_points": [f"{topic['topic']} ({topic['category']})" for topic in analysis.core_topics],
                "tags": self._extract_tags(analysis),
                "tldr": analysis.tldr,
                "core_topics": analysis.core_topics,
                "lessons_learned": analysis.lessons_learned,
                "detailed_insights": analysis.detailed_insights,
                "sources_referenced": analysis.sources_referenced,
                "concepts_mentioned": analysis.concepts_mentioned,
                "people_mentioned": analysis.people_mentioned,
                "communities_mentioned": analysis.communities_mentioned,
                "metadata_extracted": analysis.metadata_extracted,
                "input_tokens": analysis.input_tokens,
                "output_tokens": analysis.output_tokens,
                "total_tokens": analysis.total_tokens,
                "total_cost": analysis.total_cost,
                "total_processing_time_seconds": analysis.total_processing_time_seconds,
                "processing_metadata": analysis.processing_metadata,
                "model_name": analysis.model_name,
                "tokens_used": analysis.total_tokens,
                "processed_at": analysis.processed_at.isoformat() if analysis.processed_at else datetime.now(timezone.utc).isoformat()
            }

            # Upsert analysis data
            self.client.table(self.table_name).upsert(
                data,
                on_conflict="video_id"
            ).execute()

            # Update video status flags
            await self._update_video_flags(analysis.video_id)

            logger.info(f"Analysis saved successfully for video {analysis.video_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save analysis for video {analysis.video_id}: {e}", exc_info=True)
            return False

    async def get_analysis(self, video_id: str) -> Optional[VideoAnalysisComplete]:
        """Get existing analysis from database.

        Args:
            video_id: YouTube video ID

        Returns:
            VideoAnalysisComplete if exists, None otherwise
        """
        logger.debug(f"Getting analysis for video {video_id}")

        try:
            result = (
                self.client.table(self.table_name)
                .select("*")
                .eq("video_id", video_id)
                .single()
                .execute()
            )

            if not result.data:
                return None

            row = result.data

            # Convert database row to Pydantic model
            return VideoAnalysisComplete(
                video_id=row['video_id'],
                tldr=row.get('tldr', ''),
                key_audience="",  # Not stored separately
                core_topics=json.loads(row['core_topics']) if row.get('core_topics') else [],
                lessons_learned=json.loads(row['lessons_learned']) if row.get('lessons_learned') else {},
                detailed_insights=row.get('detailed_insights', ''),
                sources_referenced=json.loads(row['sources_referenced']) if row.get('sources_referenced') else [],
                concepts_mentioned=json.loads(row['concepts_mentioned']) if row.get('concepts_mentioned') else [],
                people_mentioned=json.loads(row['people_mentioned']) if row.get('people_mentioned') else [],
                communities_mentioned=json.loads(row['communities_mentioned']) if row.get('communities_mentioned') else [],
                metadata_extracted=json.loads(row['metadata_extracted']) if row.get('metadata_extracted') else {},
                input_tokens=row.get('input_tokens') or 0,
                output_tokens=row.get('output_tokens') or 0,
                total_tokens=row.get('total_tokens') or 0,
                total_cost=float(row['total_cost']) if row.get('total_cost') else 0.0,
                total_processing_time_seconds=float(row['total_processing_time_seconds']) if row.get('total_processing_time_seconds') else 0.0,
                confidence_scores={},  # Would need to extract from metadata
                processing_metadata=json.loads(row['processing_metadata']) if row.get('processing_metadata') else None,
                model_name=row.get('model_name') or "unknown",
                processed_at=datetime.fromisoformat(row['processed_at']) if row.get('processed_at') else datetime.now(timezone.utc)
            )

        except Exception as e:
            error_str = str(e)
            if "PGRST116" in error_str or "No rows" in error_str or "not found" in error_str.lower():
                return None
            logger.error(f"Failed to get analysis for video {video_id}: {e}", exc_info=True)
            return None

    async def has_analysis(self, video_id: str) -> bool:
        """Check if video has existing analysis.

        Args:
            video_id: YouTube video ID

        Returns:
            True if analysis exists, False otherwise
        """
        try:
            result = (
                self.client.table(self.table_name)
                .select("video_id")
                .eq("video_id", video_id)
                .limit(1)
                .execute()
            )
            return len(result.data) > 0

        except Exception as e:
            logger.error(f"Failed to check analysis existence for video {video_id}: {e}", exc_info=True)
            return False

    async def update_analysis_metrics(self, video_id: str, metrics: Dict[str, Any]) -> bool:
        """Update processing metrics for existing analysis.

        Args:
            video_id: YouTube video ID
            metrics: Metrics data to update

        Returns:
            True if successful, False otherwise
        """
        logger.debug(f"Updating metrics for video {video_id}")

        try:
            self.client.table(self.table_name).update({
                "processing_metadata": metrics,  # Pass Python dict directly for JSONB
                "total_cost": metrics.get('total_cost', 0.0),
                "total_processing_time_seconds": metrics.get('processing_time_seconds', 0.0),
                "processed_at": datetime.now(timezone.utc).isoformat()
            }).eq("video_id", video_id).execute()

            return True

        except Exception as e:
            logger.error(f"Failed to update metrics for video {video_id}: {e}", exc_info=True)
            return False

    async def _update_video_flags(self, video_id: str):
        """Update video table flags after successful analysis."""
        try:
            self.client.table("videos").update({
                "summary_generated": True,
                "tags_extracted": True,
                "status": VideoProcessingStatus.PROCESSED.value,
                "processed_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", video_id).execute()

            logger.debug(f"Updated video flags for {video_id}")

        except Exception as e:
            logger.warning(f"Failed to update video flags for {video_id}: {e}")
            # Don't fail the whole operation for this

    def _extract_tags(self, analysis: VideoAnalysisComplete) -> list:
        """Extract tags from analysis for the legacy tags field."""
        tags = []

        # Add topic categories as tags
        for topic in analysis.core_topics:
            if isinstance(topic, dict):
                tags.append(topic.get('category', 'general'))
                tags.append(topic.get('topic', '').lower().replace(' ', '-'))

        # Add concept tags
        for concept in analysis.concepts_mentioned:
            if isinstance(concept, dict):
                concept_name = concept.get('concept', '').lower().replace(' ', '-')
                if concept_name:
                    tags.append(concept_name)

        # Remove duplicates and limit to reasonable number
        return list(set(tags))[:15]

    async def get_processing_stats(self, date_filter: Optional[datetime] = None) -> Dict[str, Any]:
        """Get processing statistics for monitoring.

        Args:
            date_filter: Optional date to filter by

        Returns:
            Dictionary with processing statistics
        """
        try:
            query = self.client.table(self.table_name).select("total_cost, total_processing_time_seconds, total_tokens")

            if date_filter:
                query = query.gte("processed_at", date_filter.isoformat())

            result = query.execute()

            if not result.data:
                return {
                    "total_analyses": 0,
                    "avg_cost_per_video": 0.0,
                    "avg_processing_time_seconds": 0.0,
                    "avg_tokens_per_video": 0.0,
                    "total_cost": 0.0
                }

            # Calculate stats from results
            total = len(result.data)
            total_cost = sum(float(r.get('total_cost', 0) or 0) for r in result.data)
            total_time = sum(float(r.get('total_processing_time_seconds', 0) or 0) for r in result.data)
            total_tokens = sum(int(r.get('total_tokens', 0) or 0) for r in result.data)

            return {
                "total_analyses": total,
                "avg_cost_per_video": total_cost / total if total > 0 else 0.0,
                "avg_processing_time_seconds": total_time / total if total > 0 else 0.0,
                "avg_tokens_per_video": total_tokens / total if total > 0 else 0.0,
                "total_cost": total_cost
            }

        except Exception as e:
            logger.error(f"Failed to get processing stats: {e}", exc_info=True)
            return {
                "total_analyses": 0,
                "avg_cost_per_video": 0.0,
                "avg_processing_time_seconds": 0.0,
                "avg_tokens_per_video": 0.0,
                "total_cost": 0.0
            }
