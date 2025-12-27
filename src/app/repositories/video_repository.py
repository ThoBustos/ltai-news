"""Repository for video database operations."""

from typing import List, Optional
from datetime import datetime, timedelta, date

from app.core.logging import logger
from app.db.supabase import supabase
from app.models.video import Video, VideoProcessingStatus
from app.core.utils.time_window import TimeWindow, get_window


class VideoRepository:
    """Repository for video database operations."""

    def __init__(self):
        self.client = supabase
        self.table = "videos"

    def video_exists(self, video_id: str) -> bool:
        """
        Check if video exists in database.

        Args:
            video_id: YouTube video ID

        Returns:
            True if video exists, False otherwise

        Raises:
            Exception: If database operation fails
        """
        try:
            result = (
                self.client.table(self.table)
                .select("id")
                .eq("id", video_id)
                .limit(1)
                .execute()
            )

            return len(result.data) > 0

        except Exception as e:
            logger.error(f"Failed to check if video exists {video_id}: {e}")
            raise

    def get_video_by_id(self, video_id: str) -> Optional[Video]:
        """
        Get video by YouTube video ID.

        Args:
            video_id: YouTube video ID

        Returns:
            Video model or None if not found

        Raises:
            Exception: If database operation fails
        """
        try:
            result = (
                self.client.table(self.table)
                .select("*")
                .eq("id", video_id)
                .single()
                .execute()
            )

            if result.data:
                return Video(**result.data)
            return None

        except Exception as e:
            error_str = str(e)
            if "PGRST116" in error_str or "No rows" in error_str or "not found" in error_str.lower():
                return None
            logger.error(f"Failed to get video {video_id}: {e}")
            raise

    def insert_video(self, video: Video) -> Video:
        """
        Insert a new video (only if it doesn't exist).

        Args:
            video: Video model to insert

        Returns:
            Inserted video (same object)

        Raises:
            ValueError: If video already exists
            Exception: If database operation fails
        """
        # Check if video already exists
        if self.video_exists(video.id):
            logger.debug(f"Video {video.id} already exists, skipping insert")
            raise ValueError(f"Video {video.id} already exists")

        try:
            # Convert video to dict
            video_data = video.model_dump(exclude_none=True, exclude={"raw_metadata"})

            # Handle raw_metadata separately (JSONB)
            if video.raw_metadata:
                video_data["raw_metadata"] = video.raw_metadata

            # Convert datetime fields to ISO strings
            if video.published_at:
                video_data["published_at"] = video.published_at.isoformat()
            if video.collected_at:
                video_data["collected_at"] = video.collected_at.isoformat()
            if video.processed_at:
                video_data["processed_at"] = video.processed_at.isoformat()

            # Insert video
            result = (
                self.client.table(self.table)
                .insert(video_data)
                .execute()
            )

            if result.data:
                logger.info(f"Inserted video: {video.id} - {video.title[:50]}...")
            else:
                logger.warning(f"No data returned from video insert: {video.id}")

            return video

        except Exception as e:
            logger.error(f"Failed to insert video {video.id}: {e}")
            raise

    def upsert_video(self, video: Video) -> Video:
        """
        Insert or update a video.

        Updates only if video exists and hasn't been processed yet.
        Otherwise inserts new video.

        Args:
            video: Video model to upsert

        Returns:
            Upserted video (same object)

        Raises:
            Exception: If database operation fails
        """
        try:
            existing = self.get_video_by_id(video.id)

            if existing:
                # Only update if not processed
                if existing.status in [VideoProcessingStatus.COLLECTED, VideoProcessingStatus.PROCESSING]:
                    # Update metadata but preserve processing status
                    video_data = video.model_dump(
                        exclude_none=True,
                        exclude={"raw_metadata", "status", "processed_at", "processing_error"}
                    )

                    if video.raw_metadata:
                        video_data["raw_metadata"] = video.raw_metadata

                    # Convert datetime fields
                    if video.published_at:
                        video_data["published_at"] = video.published_at.isoformat()
                    if video.collected_at:
                        video_data["collected_at"] = video.collected_at.isoformat()

                    self.client.table(self.table).update(video_data).eq("id", video.id).execute()
                    logger.debug(f"Updated unprocessed video: {video.id}")
                else:
                    logger.debug(f"Video {video.id} already processed ({existing.status}), skipping update")
            else:
                # Insert new video
                self.insert_video(video)

            return video

        except ValueError:
            # Video already exists, return existing
            return self.get_video_by_id(video.id) or video
        except Exception as e:
            logger.error(f"Failed to upsert video {video.id}: {e}")
            raise

    def get_unprocessed_videos(
        self,
        channel_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Video]:
        """
        Get videos that haven't been processed yet.

        Args:
            channel_id: Optional channel ID to filter by
            limit: Optional limit on number of results

        Returns:
            List of unprocessed Video models

        Raises:
            Exception: If database operation fails
        """
        try:
            query = (
                self.client.table(self.table)
                .select("*")
                .in_("status", [VideoProcessingStatus.COLLECTED.value])
                .order("collected_at", desc=False)  # Process oldest first
            )

            if channel_id:
                query = query.eq("channel_id", channel_id)

            if limit:
                query = query.limit(limit)

            result = query.execute()

            return [Video(**row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get unprocessed videos: {e}")
            raise

    def update_video_status(
        self,
        video_id: str,
        status: VideoProcessingStatus,
        error: Optional[str] = None
    ) -> None:
        """
        Update video processing status.

        Args:
            video_id: YouTube video ID
            status: New processing status
            error: Optional error message if status is FAILED

        Raises:
            Exception: If database operation fails
        """
        try:
            update_data = {
                "status": status.value,
            }

            if status == VideoProcessingStatus.PROCESSED:
                update_data["processed_at"] = datetime.utcnow().isoformat()
            elif status == VideoProcessingStatus.FAILED and error is not None:
                update_data["processing_error"] = error

            self.client.table(self.table).update(update_data).eq("id", video_id).execute()

            logger.debug(f"Updated video {video_id} status to {status.value}")

        except Exception as e:
            logger.error(f"Failed to update video status {video_id}: {e}")
            raise

    def get_recent_videos_by_channel(
        self,
        channel_id: str,
        hours: int = 24,
        limit: Optional[int] = None
    ) -> List[Video]:
        """
        Get recent videos for a channel within specified hours.

        Args:
            channel_id: YouTube channel ID
            hours: Number of hours to look back
            limit: Optional limit on number of results

        Returns:
            List of Video models

        Raises:
            Exception: If database operation fails
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            query = (
                self.client.table(self.table)
                .select("*")
                .eq("channel_id", channel_id)
                .gte("published_at", cutoff_time.isoformat())
                .order("published_at", desc=True)
            )

            if limit:
                query = query.limit(limit)

            result = query.execute()

            return [Video(**row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get recent videos for channel {channel_id}: {e}")
            raise

    def get_videos_for_date(self, target_date: date) -> List[Video]:
        """
        Get videos published on a specific date (UTC).

        Args:
            target_date: Date to get videos for

        Returns:
            List of Video models published on the target date

        Raises:
            Exception: If database operation fails
        """
        try:
            window = get_window(target_date)
            return self.get_videos_in_window(window)

        except Exception as e:
            logger.error(f"Failed to get videos for date {target_date}: {e}")
            raise

    def get_videos_in_window(self, window: TimeWindow) -> List[Video]:
        """
        Get videos published within a specific time window.

        Args:
            window: TimeWindow to filter videos by

        Returns:
            List of Video models published within the window

        Raises:
            Exception: If database operation fails
        """
        try:
            result = (
                self.client.table(self.table)
                .select("*")
                .gte("published_at", window.start_utc.isoformat())
                .lte("published_at", window.end_utc.isoformat())
                .order("published_at", desc=True)
                .execute()
            )

            videos = [Video(**row) for row in result.data]
            logger.debug(f"Found {len(videos)} videos in window {window.date_str}")
            return videos

        except Exception as e:
            logger.error(f"Failed to get videos in window {window.date_str}: {e}")
            raise

    def get_pending_processing(self, target_date: date) -> List[Video]:
        """
        Get videos published on a specific date that need processing.

        Args:
            target_date: Date to get pending videos for

        Returns:
            List of Video models with status 'collected' for the target date

        Raises:
            Exception: If database operation fails
        """
        try:
            window = get_window(target_date)
            
            result = (
                self.client.table(self.table)
                .select("*")
                .gte("published_at", window.start_utc.isoformat())
                .lte("published_at", window.end_utc.isoformat())
                .eq("status", VideoProcessingStatus.COLLECTED.value)
                .order("published_at", desc=False)  # Process oldest first
                .execute()
            )

            videos = [Video(**row) for row in result.data]
            logger.debug(f"Found {len(videos)} pending videos for {target_date}")
            return videos

        except Exception as e:
            logger.error(f"Failed to get pending videos for {target_date}: {e}")
            raise

    def update_status(
        self,
        video_id: str,
        status: VideoProcessingStatus,
        processed_at: Optional[datetime] = None,
        processing_error: Optional[str] = None
    ) -> None:
        """
        Update video processing status with enhanced options.

        Args:
            video_id: YouTube video ID
            status: New processing status
            processed_at: Optional timestamp for when processing completed
            processing_error: Optional error message if status is FAILED

        Raises:
            Exception: If database operation fails
        """
        try:
            update_data = {
                "status": status.value,
            }

            if processed_at:
                update_data["processed_at"] = processed_at.isoformat()
            elif status == VideoProcessingStatus.PROCESSED:
                update_data["processed_at"] = datetime.utcnow().isoformat()

            if processing_error:
                update_data["processing_error"] = processing_error
            elif status == VideoProcessingStatus.FAILED and not processing_error:
                update_data["processing_error"] = "Processing failed (no details)"

            self.client.table(self.table).update(update_data).eq("id", video_id).execute()

            logger.debug(f"Updated video {video_id} status to {status.value}")

        except Exception as e:
            logger.error(f"Failed to update video status {video_id}: {e}")
            raise

    def get_videos_pending_transcripts(self, target_date: date) -> List[Video]:
        """Get videos that need transcript extraction for a specific date.
        
        Args:
            target_date: Date to get videos for
            
        Returns:
            List of videos with status 'collected' and transcript_fetched = False
            
        Raises:
            Exception: If database operation fails
        """
        try:
            window = get_window(target_date)
            
            result = (
                self.client.table(self.table)
                .select("*")
                .gte("published_at", window.start_utc.isoformat())
                .lte("published_at", window.end_utc.isoformat())
                .eq("status", VideoProcessingStatus.COLLECTED.value)
                .eq("transcript_fetched", False)
                .order("published_at", desc=False)  # Process oldest first
                .execute()
            )

            videos = [Video(**row) for row in result.data]
            logger.debug(f"Found {len(videos)} videos pending transcript extraction for {target_date}")
            return videos

        except Exception as e:
            logger.error(f"Failed to get videos pending transcripts for {target_date}: {e}")
            raise

    def save_transcript(self, video_id: str, transcript: str, language_code: str = "en") -> bool:
        """Save transcript to database and update video flags.
        
        Args:
            video_id: YouTube video ID
            transcript: Transcript text
            language_code: Language code for the transcript
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            Exception: If database operation fails
        """
        try:
            # Use upsert to handle existing transcripts
            transcript_data = {
                "video_id": video_id,
                "transcript": transcript,
                "char_count": len(transcript),
                "language_code": language_code,
                "extracted_at": datetime.utcnow().isoformat(),
            }
            
            # Insert or update transcript
            self.client.table("video_transcripts").upsert(
                transcript_data,
                on_conflict="video_id"
            ).execute()
            
            # Update video flags
            self.client.table(self.table).update({
                "transcript_fetched": True
            }).eq("id", video_id).execute()
            
            logger.debug(f"Saved transcript for video {video_id} ({len(transcript)} characters)")
            return True

        except Exception as e:
            logger.error(f"Failed to save transcript for video {video_id}: {e}")
            raise

    def mark_transcript_failed(self, video_id: str, error: str) -> bool:
        """Mark transcript extraction as failed for a video.
        
        Args:
            video_id: YouTube video ID
            error: Error message describing the failure
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            Exception: If database operation fails
        """
        try:
            # Update video to mark transcript as fetched (even though failed)
            # This prevents endless retries for videos without transcripts
            self.client.table(self.table).update({
                "transcript_fetched": True,
                "transcript_error": error
            }).eq("id", video_id).execute()
            
            logger.debug(f"Marked transcript failed for video {video_id}: {error}")
            return True

        except Exception as e:
            logger.error(f"Failed to mark transcript failed for video {video_id}: {e}")
            raise

    def get_transcript(self, video_id: str) -> Optional[str]:
        """Get existing transcript for a video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Transcript text if exists, None otherwise
            
        Raises:
            Exception: If database operation fails
        """
        try:
            result = (
                self.client.table("video_transcripts")
                .select("transcript")
                .eq("video_id", video_id)
                .single()
                .execute()
            )
            
            if result.data:
                return result.data.get("transcript")
            return None

        except Exception as e:
            error_str = str(e)
            if "PGRST116" in error_str or "No rows" in error_str or "not found" in error_str.lower():
                return None
            logger.error(f"Failed to get transcript for video {video_id}: {e}")
            raise

    def has_transcript(self, video_id: str) -> bool:
        """Check if video has an existing transcript.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            True if transcript exists, False otherwise
        """
        try:
            result = (
                self.client.table("video_transcripts")
                .select("video_id")
                .eq("video_id", video_id)
                .limit(1)
                .execute()
            )
            
            return len(result.data) > 0

        except Exception as e:
            logger.error(f"Failed to check transcript existence for video {video_id}: {e}")
            return False
