"""Content orchestrator service - central pipeline coordinator."""

from datetime import date, datetime, timezone
from typing import List, Optional

from app.core.logging import logger
from app.core.utils.time_window import TimeWindow, get_window, parse_date
from app.models.pipeline import (
    ExtractionResult,
    PipelineResult,
    PipelineStatus,
    ProcessingResult,
    DigestResult,
    XThreadResult,
    TranscriptExtractionResult,
)
from app.models.video import Video, VideoProcessingStatus
from app.repositories import VideoRepository, ChannelRepository
from app.services.channel_tracker import ChannelTracker
from app.services.transcript_service import TranscriptService
from app.services.video_analysis_service import VideoAnalysisService
from app.services.x_thread_service import XThreadService
from app.config.settings import settings


class ContentOrchestrator:
    """Central pipeline coordinator for content processing."""
    
    def __init__(self):
        """Initialize orchestrator with required services."""
        self.video_repo = VideoRepository()
        self.channel_repo = ChannelRepository()
        self.channel_tracker = ChannelTracker()
        self.transcript_service = TranscriptService()
        self.video_analysis_service = VideoAnalysisService()
        self.x_thread_service = XThreadService()
    
    async def run_daily_pipeline(self, target_date: date) -> PipelineResult:
        """Run the complete daily content pipeline for a specific date.
        
        Args:
            target_date: Date to process content for
            
        Returns:
            PipelineResult with complete execution details
        """
        pipeline_started_at = datetime.now(timezone.utc)
        date_str = target_date.isoformat()
        window = get_window(target_date)
        total_errors = []
        
        logger.info(f"Starting daily pipeline for {date_str}")
        
        try:
            # Phase 1: Extract content
            logger.info(f"Phase 1: Extracting content for {date_str}")
            extraction_result = await self._extract_content(target_date, window)
            
            # Phase 2: Extract transcripts
            logger.info(f"Phase 2: Extracting transcripts for {date_str}")
            transcript_result = await self._extract_transcripts(target_date)
            
            # Phase 3: Process videos (analysis and other processing)
            logger.info(f"Phase 3: Processing videos for {date_str}")
            processing_result = await self._process_videos(target_date, transcript_result)
            
            # Phase 4: Generate digest
            logger.info(f"Phase 4: Generating digest for {date_str}")
            digest_result = await self._generate_digest(target_date)

            # Phase 5: Post to X (if enabled)
            x_thread_result = None
            if settings.auto_post_to_x and digest_result.digest_generated:
                logger.info(f"Phase 5: Posting to X for {date_str}")
                x_thread_result = await self._post_to_x(target_date)
            elif settings.auto_post_to_x and not digest_result.digest_generated:
                logger.warning(f"Skipping Phase 5 (X posting): No digest generated for {date_str}")

            # Collect all errors
            total_errors.extend(extraction_result.errors)
            total_errors.extend(transcript_result.errors)
            total_errors.extend(processing_result.errors)
            total_errors.extend(digest_result.errors)
            if x_thread_result:
                total_errors.extend(x_thread_result.errors)

            pipeline_completed_at = datetime.now(timezone.utc)

            result = PipelineResult(
                target_date=date_str,
                window=window,
                extraction=extraction_result,
                processing=processing_result,
                digest=digest_result,
                x_thread=x_thread_result,
                pipeline_started_at=pipeline_started_at,
                pipeline_completed_at=pipeline_completed_at,
                total_errors=total_errors,
            )
            
            if result.success:
                logger.info(f"Pipeline completed successfully for {date_str} in {result.duration_seconds:.2f}s")
            else:
                logger.warning(f"Pipeline completed with {len(total_errors)} errors for {date_str}")
            
            return result
            
        except Exception as e:
            logger.error(f"Pipeline failed for {date_str}: {e}", exc_info=True)
            
            pipeline_completed_at = datetime.now(timezone.utc)
            total_errors.append(f"Pipeline failure: {str(e)}")
            
            return PipelineResult(
                target_date=date_str,
                window=window,
                extraction=None,
                processing=None,
                digest=None,
                pipeline_started_at=pipeline_started_at,
                pipeline_completed_at=pipeline_completed_at,
                total_errors=total_errors,
            )
    
    async def _extract_content(self, target_date: date, window: TimeWindow) -> ExtractionResult:
        """Extract content for the given date and time window.
        
        Args:
            target_date: Date to extract content for
            window: Time window to extract content for
            
        Returns:
            ExtractionResult with extraction statistics
        """
        started_at = datetime.now(timezone.utc)
        errors = []
        
        try:
            # Use date-specific syncing to respect backfills and historical windows
            tracker_result = self.channel_tracker.sync_channels_for_date(target_date)
            
            # Count videos in our time window
            videos_in_window = 0
            videos_saved = 0
            
            for sync_result in tracker_result.sync_results:
                if sync_result.error:
                    errors.append(f"Channel {sync_result.channel.name}: {sync_result.error}")
                    continue
                
                # Count videos that fall within our window
                for video in sync_result.videos_collected:
                    if window.contains(video.published_at):
                        logger.info(f"Found video in window: {video.id} - {video.title} ({video.published_at})")
                        videos_in_window += 1
                        videos_saved += 1
                    else:
                        logger.debug(f"Video {video.id} outside window: {video.published_at}")
            
            completed_at = datetime.now(timezone.utc)
            
            return ExtractionResult(
                videos_found=videos_in_window,
                videos_saved=videos_saved,
                channels_processed=tracker_result.channels_processed,
                channels_found=tracker_result.channels_found,
                channels_not_found=tracker_result.channels_not_found,
                errors=errors,
                window=window,
                started_at=started_at,
                completed_at=completed_at,
            )
            
        except Exception as e:
            logger.error(f"Content extraction failed: {e}", exc_info=True)
            errors.append(f"Extraction failed: {str(e)}")
            
            return ExtractionResult(
                videos_found=0,
                videos_saved=0,
                channels_processed=0,
                channels_found=0,
                channels_not_found=[],
                errors=errors,
                window=window,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )
    
    async def _extract_transcripts(self, target_date: date) -> TranscriptExtractionResult:
        """Extract transcripts for videos on the target date.
        
        Args:
            target_date: Date to extract transcripts for
            
        Returns:
            TranscriptExtractionResult with extraction statistics
        """
        logger.info(f"Extracting transcripts for {target_date}")
        
        try:
            return await self.transcript_service.extract_transcripts_for_date(target_date)
            
        except Exception as e:
            logger.error(f"Transcript extraction failed for {target_date}: {e}", exc_info=True)
            
            # Return failed result
            started_at = datetime.now(timezone.utc)
            return TranscriptExtractionResult(
                videos_attempted=0,
                transcripts_extracted=0,
                transcripts_failed=0,
                transcripts_skipped=0,
                errors=[f"Transcript extraction failed: {str(e)}"],
                started_at=started_at,
                completed_at=datetime.now(timezone.utc)
            )
    
    async def _process_videos(self, target_date: date, transcript_result: Optional[TranscriptExtractionResult] = None) -> ProcessingResult:
        """Process videos for the target date using video analysis service.
        
        Args:
            target_date: Date to process videos for
            transcript_result: Result from transcript extraction phase
            
        Returns:
            ProcessingResult with processing statistics
        """
        started_at = datetime.now(timezone.utc)
        errors = []
        
        logger.info(f"Processing videos for {target_date}")
        
        try:
            # Get videos that need processing (status = COLLECTED, transcript_fetched = True)
            processing_queue = self.get_processing_queue(target_date)
            
            # Filter to only videos with transcripts
            videos_with_transcripts = [
                v for v in processing_queue 
                if self.video_repo.has_transcript(v.id) and not await self.video_analysis_service.has_analysis(v.id)
            ]
            
            logger.info(f"Found {len(videos_with_transcripts)} videos with transcripts needing analysis")
            
            videos_processed = 0
            transcripts_extracted = transcript_result.transcripts_extracted if transcript_result else 0
            analyses_completed = 0
            
            for video in videos_with_transcripts:
                try:
                    logger.info(f"Processing video {video.id}: {video.title[:50]}...")
                    
                    # Analyze video using the analysis service
                    analysis = await self.video_analysis_service.analyze_video(video.id)
                    
                    if analysis:
                        analyses_completed += 1
                        videos_processed += 1
                        logger.info(f"Successfully analyzed video {video.id}")
                    else:
                        error_msg = f"Analysis returned None for video {video.id}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        
                except Exception as e:
                    error_msg = f"Failed to process video {video.id}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)
            
            completed_at = datetime.now(timezone.utc)
            
            logger.info(f"Video processing completed: {analyses_completed}/{len(videos_with_transcripts)} analyses successful")
            
            return ProcessingResult(
                videos_processed=videos_processed,
                transcripts_extracted=transcripts_extracted,
                analyses_completed=analyses_completed,
                errors=errors,
                started_at=started_at,
                completed_at=completed_at,
            )
            
        except Exception as e:
            logger.error(f"Video processing failed: {e}", exc_info=True)
            errors.append(f"Processing failed: {str(e)}")
            
            return ProcessingResult(
                videos_processed=0,
                transcripts_extracted=0,
                analyses_completed=0,
                errors=errors,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )
    
    async def _generate_digest(self, target_date: date) -> DigestResult:
        """Generate digest for the target date using the daily digest agent.

        Args:
            target_date: Date to generate digest for

        Returns:
            DigestResult with generation statistics
        """
        started_at = datetime.now(timezone.utc)
        errors = []

        logger.info(f"Generating digest for {target_date}")

        try:
            # Import here to avoid circular imports
            from app.agents.daily_digest import generate_daily_digest

            # Run the daily digest workflow
            result = await generate_daily_digest(target_date)

            completed_at = datetime.now(timezone.utc)

            if result and result.success:
                return DigestResult(
                    digest_generated=True,
                    videos_included=result.videos_included,
                    digest_id=result.digest_id,
                    errors=result.errors,
                    started_at=started_at,
                    completed_at=completed_at,
                )
            else:
                errors.extend(result.errors if result else ["Digest generation returned no result"])
                return DigestResult(
                    digest_generated=False,
                    videos_included=0,
                    digest_id=None,
                    errors=errors,
                    started_at=started_at,
                    completed_at=completed_at,
                )

        except Exception as e:
            logger.error(f"Digest generation failed: {e}", exc_info=True)
            errors.append(f"Digest generation failed: {str(e)}")

            return DigestResult(
                digest_generated=False,
                videos_included=0,
                digest_id=None,
                errors=errors,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )

    async def _post_to_x(self, target_date: date) -> XThreadResult:
        """Post digest to X/Twitter for the target date.

        Args:
            target_date: Date of the digest to post

        Returns:
            XThreadResult with posting statistics
        """
        started_at = datetime.now(timezone.utc)
        errors = []

        logger.info(f"Posting digest to X for {target_date}")

        try:
            # Use X thread service to generate and post thread
            result = await self.x_thread_service.post_digest_to_x(target_date)
            return result

        except Exception as e:
            logger.error(f"X posting failed: {e}", exc_info=True)
            errors.append(f"X posting failed: {str(e)}")

            return XThreadResult(
                thread_posted=False,
                tweet_count=0,
                tweet_ids=None,
                thread_url=None,
                errors=errors,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )

    def get_processing_queue(self, target_date: date) -> List[Video]:
        """Get videos that need processing for the target date.
        
        Args:
            target_date: Date to get processing queue for
            
        Returns:
            List of videos with status 'collected' for the target date
        """
        try:
            window = get_window(target_date)
            all_videos = self.video_repo.get_videos_in_window(window)
            
            # Filter for videos that need processing
            processing_queue = [
                video for video in all_videos 
                if video.status == VideoProcessingStatus.COLLECTED
            ]
            
            logger.info(f"Processing queue for {target_date}: {len(processing_queue)} videos")
            return processing_queue
        
        except Exception as e:
            logger.error(f"Failed to get processing queue for {target_date}: {e}")
            return []

    async def reprocess_failed_videos(self, target_date: date) -> ProcessingResult:
        """Reprocess videos that failed analysis for a specific date.
        
        This method:
        1. Gets all failed videos for the target date
        2. Deletes their existing analysis data (if any)
        3. Resets their status back to 'collected'
        4. Runs the analysis pipeline on them
        
        Args:
            target_date: Date to reprocess failed videos for
            
        Returns:
            ProcessingResult with reprocessing statistics
        """
        started_at = datetime.now(timezone.utc)
        errors = []
        
        logger.info(f"Starting reprocess of failed videos for {target_date}")
        
        try:
            # Get failed videos first (before resetting)
            failed_videos = self.video_repo.get_failed_videos(target_date)
            
            if not failed_videos:
                logger.info(f"No failed videos to reprocess for {target_date}")
                return ProcessingResult(
                    videos_processed=0,
                    transcripts_extracted=0,
                    analyses_completed=0,
                    errors=[],
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                )
            
            logger.info(f"Found {len(failed_videos)} failed videos to reprocess for {target_date}")
            
            # Delete existing failed analysis data for these videos
            for video in failed_videos:
                try:
                    await self.video_analysis_service.delete_analysis(video.id)
                except Exception as e:
                    logger.warning(f"Could not delete existing analysis for {video.id}: {e}")
            
            # Reset failed videos status to 'collected'
            reset_count = self.video_repo.reset_failed_videos(target_date)
            logger.info(f"Reset {reset_count} videos to collected status")
            
            # Now run the processing pipeline on them
            videos_processed = 0
            analyses_completed = 0
            
            for video in failed_videos:
                try:
                    # Check if video has transcript
                    if not self.video_repo.has_transcript(video.id):
                        logger.warning(f"Video {video.id} has no transcript, skipping")
                        errors.append(f"Video {video.id} has no transcript")
                        continue
                    
                    logger.info(f"Reprocessing video {video.id}: {video.title[:50]}...")
                    
                    # Analyze video
                    analysis = await self.video_analysis_service.analyze_video(video.id)
                    
                    if analysis:
                        analyses_completed += 1
                        videos_processed += 1
                        logger.info(f"Successfully reprocessed video {video.id}")
                    else:
                        error_msg = f"Analysis returned None for video {video.id}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        
                except Exception as e:
                    error_msg = f"Failed to reprocess video {video.id}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)
            
            completed_at = datetime.now(timezone.utc)
            
            logger.info(f"Reprocessing completed: {analyses_completed}/{len(failed_videos)} successful")
            
            return ProcessingResult(
                videos_processed=videos_processed,
                transcripts_extracted=0,
                analyses_completed=analyses_completed,
                errors=errors,
                started_at=started_at,
                completed_at=completed_at,
            )
            
        except Exception as e:
            logger.error(f"Reprocessing failed videos failed: {e}", exc_info=True)
            errors.append(f"Reprocessing failed: {str(e)}")
            
            return ProcessingResult(
                videos_processed=0,
                transcripts_extracted=0,
                analyses_completed=0,
                errors=errors,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )
    
    def get_pipeline_status(self, target_date: date) -> PipelineStatus:
        """Get current status of pipeline for target date.
        
        Args:
            target_date: Date to check pipeline status for
            
        Returns:
            PipelineStatus with current state
        """
        try:
            date_str = target_date.isoformat()
            window = get_window(target_date)
            
            # Get videos for this date
            videos = self.video_repo.get_videos_in_window(window)
            
            if not videos:
                return PipelineStatus(
                    target_date=date_str,
                    status='pending',
                    current_phase=None,
                    started_at=None,
                    estimated_completion=None,
                    progress_percentage=0.0,
                    last_updated=datetime.now(timezone.utc),
                    errors=[]
                )
            
            # Analyze video statuses to determine pipeline phase
            collected_count = len([v for v in videos if v.status == VideoProcessingStatus.COLLECTED])
            processing_count = len([v for v in videos if v.status == VideoProcessingStatus.PROCESSING])
            processed_count = len([v for v in videos if v.status == VideoProcessingStatus.PROCESSED])
            failed_count = len([v for v in videos if v.status == VideoProcessingStatus.FAILED])
            
            total_videos = len(videos)
            errors = [f"{failed_count} videos failed processing"] if failed_count > 0 else []
            
            # Determine current status and phase
            if collected_count == total_videos:
                status = 'pending'
                current_phase = 'extraction_complete'
                progress = 25.0
            elif processing_count > 0:
                status = 'processing'
                current_phase = 'video_processing'
                progress = 50.0 + ((processed_count / total_videos) * 25.0)
            elif processed_count == (total_videos - failed_count):
                status = 'completed'
                current_phase = 'digest_generation'
                progress = 100.0
            else:
                status = 'extracting'
                current_phase = 'content_extraction'
                progress = (processed_count / total_videos) * 25.0
            
            return PipelineStatus(
                target_date=date_str,
                status=status,
                current_phase=current_phase,
                started_at=min(v.collected_at for v in videos if v.collected_at),
                estimated_completion=None,  # Could be calculated based on processing rate
                progress_percentage=progress,
                last_updated=datetime.now(timezone.utc),
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Failed to get pipeline status for {target_date}: {e}", exc_info=True)
            return PipelineStatus(
                target_date=target_date.isoformat(),
                status='failed',
                current_phase='error',
                started_at=None,
                estimated_completion=None,
                progress_percentage=0.0,
                last_updated=datetime.now(timezone.utc),
                errors=[f"Status check failed: {str(e)}"]
            )
    
    async def run_backfill(self, start_date: date, end_date: date) -> List[PipelineResult]:
        """Run pipeline for a range of dates (backfill operation).
        
        Args:
            start_date: First date to process
            end_date: Last date to process (inclusive)
            
        Returns:
            List of PipelineResult for each date
        """
        logger.info(f"Starting backfill from {start_date} to {end_date}")
        
        results = []
        current_date = start_date
        
        while current_date <= end_date:
            logger.info(f"Backfill processing date: {current_date}")
            
            try:
                result = await self.run_daily_pipeline(current_date)
                results.append(result)
            except Exception as e:
                logger.error(f"Backfill failed for {current_date}: {e}", exc_info=True)
                
                # Create a failed result
                failed_result = PipelineResult(
                    target_date=current_date.isoformat(),
                    window=get_window(current_date),
                    extraction=None,
                    processing=None,
                    digest=None,
                    pipeline_started_at=datetime.now(timezone.utc),
                    pipeline_completed_at=datetime.now(timezone.utc),
                    total_errors=[f"Backfill failed: {str(e)}"]
                )
                results.append(failed_result)
            
            # Move to next date
            current_date = date.fromordinal(current_date.toordinal() + 1)
        
        successful_runs = len([r for r in results if r.success])
        logger.info(f"Backfill completed: {successful_runs}/{len(results)} successful runs")
        
        return results
    
    async def extract_transcripts(self, target_date: date) -> TranscriptExtractionResult:
        """Extract transcripts for a specific date (standalone operation).
        
        Args:
            target_date: Date to extract transcripts for
            
        Returns:
            TranscriptExtractionResult with extraction statistics
        """
        logger.info(f"Starting standalone transcript extraction for {target_date}")
        
        try:
            return await self._extract_transcripts(target_date)
            
        except Exception as e:
            logger.error(f"Standalone transcript extraction failed for {target_date}: {e}", exc_info=True)
            
            # Return failed result
            started_at = datetime.now(timezone.utc)
            return TranscriptExtractionResult(
                videos_attempted=0,
                transcripts_extracted=0,
                transcripts_failed=0,
                transcripts_skipped=0,
                errors=[f"Standalone transcript extraction failed: {str(e)}"],
                started_at=started_at,
                completed_at=datetime.now(timezone.utc)
            )