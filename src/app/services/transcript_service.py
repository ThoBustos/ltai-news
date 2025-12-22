"""Transcript service for video transcript extraction."""

import asyncio
from datetime import datetime, timezone, date
from typing import Optional, List

from app.core.logging import logger
from app.models.pipeline import TranscriptResult, TranscriptExtractionResult
from app.models.video import Video
from app.client.transcript_io import (
    TranscriptIoClient, 
    TranscriptNotFoundError, 
    TranscriptApiError,
    TranscriptIoError
)
from app.repositories.video_repository import VideoRepository
from app.config.settings import settings


class TranscriptService:
    """Service for extracting and managing video transcripts."""
    
    def __init__(self):
        """Initialize transcript service with client and repository."""
        self.service_name = "transcript_service"
        self.video_repo = VideoRepository()
        
        # Initialize transcript.io client if configured
        api_key = getattr(settings, 'transcript_io_api_key', None)
        base_url = getattr(settings, 'transcript_io_base_url', "https://www.youtube-transcript.io/api")
        
        if api_key:
            self.client = TranscriptIoClient(api_key, base_url)
            logger.info("Initialized TranscriptService with transcript.io client")
        else:
            self.client = None
            logger.warning("TranscriptService initialized without API key - will be in simulation mode")
    
    def is_available(self) -> bool:
        """Check if transcript service is available (has API key)."""
        return self.client is not None
    
    async def extract_transcript(self, video: Video, language_code: str = "en") -> TranscriptResult:
        """Extract transcript from a video using transcript.io API.
        
        Args:
            video: Video to extract transcript from
            language_code: Language code for transcript (default: 'en')
            
        Returns:
            TranscriptResult with extraction status
        """
        logger.info(f"Extracting transcript for video {video.id}")
        
        extracted_at = datetime.now(timezone.utc)
        
        # Check if client is available
        if not self.client:
            logger.warning(f"No transcript client available for video {video.id} - simulation mode")
            return TranscriptResult(
                video_id=video.id,
                success=False,
                transcript=None,
                language_code=language_code,
                error="Transcript service not configured (missing API key)",
                extracted_at=extracted_at
            )
        
        try:
            # Extract transcript using the client
            transcript_text = await self.client.get_transcript_text(video.id, language_code)
            
            if transcript_text:
                logger.info(f"Successfully extracted transcript for video {video.id} ({len(transcript_text)} characters)")
                return TranscriptResult(
                    video_id=video.id,
                    success=True,
                    transcript=transcript_text,
                    language_code=language_code,
                    error=None,
                    extracted_at=extracted_at
                )
            else:
                error_msg = "Empty transcript returned"
                logger.warning(f"Empty transcript for video {video.id}")
                return TranscriptResult(
                    video_id=video.id,
                    success=False,
                    transcript=None,
                    language_code=language_code,
                    error=error_msg,
                    extracted_at=extracted_at
                )
                
        except TranscriptNotFoundError as e:
            # Terminal error - transcript simply doesn't exist
            error_msg = f"No transcript available: {str(e)}"
            logger.info(f"No transcript available for video {video.id}")
            return TranscriptResult(
                video_id=video.id,
                success=False,
                transcript=None,
                language_code=language_code,
                error=error_msg,
                extracted_at=extracted_at
            )
            
        except (TranscriptApiError, TranscriptIoError) as e:
            # API errors - could be temporary or terminal
            error_msg = f"API error: {str(e)}"
            logger.error(f"API error extracting transcript for video {video.id}: {error_msg}")
            return TranscriptResult(
                video_id=video.id,
                success=False,
                transcript=None,
                language_code=language_code,
                error=error_msg,
                extracted_at=extracted_at
            )
            
        except Exception as e:
            # Unexpected errors
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error extracting transcript for video {video.id}: {error_msg}", exc_info=True)
            return TranscriptResult(
                video_id=video.id,
                success=False,
                transcript=None,
                language_code=language_code,
                error=error_msg,
                extracted_at=extracted_at
            )
    
    async def save_transcript(self, video_id: str, transcript: str, language_code: str = "en") -> bool:
        """Save transcript to database.
        
        Args:
            video_id: YouTube video ID
            transcript: Transcript text
            language_code: Language code (default: 'en')
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Saving transcript for video {video_id}")
        
        try:
            success = self.video_repo.save_transcript(video_id, transcript, language_code)
            if success:
                logger.debug(f"Transcript saved for video {video_id} ({len(transcript)} characters)")
            return success
            
        except Exception as e:
            logger.error(f"Failed to save transcript for video {video_id}: {e}", exc_info=True)
            return False
    
    async def get_transcript(self, video_id: str) -> Optional[str]:
        """Get existing transcript from database.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Transcript text if exists, None otherwise
        """
        logger.debug(f"Getting transcript for video {video_id}")
        
        try:
            return self.video_repo.get_transcript(video_id)
            
        except Exception as e:
            logger.error(f"Failed to get transcript for video {video_id}: {e}", exc_info=True)
            return None
    
    def has_transcript(self, video_id: str) -> bool:
        """Check if video has an existing transcript.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            True if transcript exists, False otherwise
        """
        try:
            return self.video_repo.has_transcript(video_id)
            
        except Exception as e:
            logger.error(f"Failed to check transcript existence for video {video_id}: {e}", exc_info=True)
            return False
    
    async def extract_and_save_transcript(self, video: Video, language_code: str = "en") -> TranscriptResult:
        """Extract and save transcript in one operation.
        
        Args:
            video: Video to process
            language_code: Language code for transcript
            
        Returns:
            TranscriptResult with extraction and save status
        """
        logger.info(f"Extract and save transcript for video {video.id}")
        
        # Extract transcript
        result = await self.extract_transcript(video, language_code)
        
        if result.success and result.transcript:
            # Save transcript to database
            save_success = await self.save_transcript(
                video.id, 
                result.transcript, 
                result.language_code or language_code
            )
            
            if not save_success:
                # Update result to reflect save failure
                result.success = False
                result.error = "Transcript extraction succeeded but save failed"
        elif not result.success and result.is_terminal_failure:
            # For terminal failures, mark as failed to prevent retries
            try:
                self.video_repo.mark_transcript_failed(video.id, result.error or "Terminal failure")
                logger.info(f"Marked transcript as terminal failure for video {video.id}")
            except Exception as e:
                logger.error(f"Failed to mark transcript as failed for video {video.id}: {e}")
        
        return result
    
    async def extract_transcripts_for_date(self, target_date: date, language_code: str = "en") -> TranscriptExtractionResult:
        """Extract transcripts for all pending videos on a specific date.
        
        Args:
            target_date: Date to process videos for
            language_code: Language code for transcripts
            
        Returns:
            TranscriptExtractionResult with batch processing statistics
        """
        started_at = datetime.now(timezone.utc)
        errors = []
        
        logger.info(f"Extracting transcripts for date {target_date}")
        
        try:
            # Get videos pending transcript extraction
            pending_videos = self.video_repo.get_videos_pending_transcripts(target_date)
            
            if not pending_videos:
                logger.info(f"No videos pending transcript extraction for {target_date}")
                return TranscriptExtractionResult(
                    videos_attempted=0,
                    transcripts_extracted=0,
                    transcripts_failed=0,
                    transcripts_skipped=0,
                    errors=[],
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc)
                )
            
            logger.info(f"Found {len(pending_videos)} videos pending transcripts for {target_date}")
            
            # Process videos one by one (atomic strategy)
            transcripts_extracted = 0
            transcripts_failed = 0
            transcripts_skipped = 0
            
            for video in pending_videos:
                try:
                    logger.debug(f"Processing transcript for video {video.id}")
                    
                    # Skip if transcript already exists
                    if self.has_transcript(video.id):
                        logger.debug(f"Transcript already exists for video {video.id}, skipping")
                        transcripts_skipped += 1
                        continue
                    
                    # Extract and save transcript
                    result = await self.extract_and_save_transcript(video, language_code)
                    
                    if result.success:
                        transcripts_extracted += 1
                        logger.info(f"Successfully extracted transcript for video {video.id}")
                    else:
                        transcripts_failed += 1
                        error_msg = f"Failed to extract transcript for video {video.id}: {result.error}"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                    
                    # Rate limiting: Sleep 2 seconds between videos to stay within API limit
                    # (5 requests per 10 seconds = 1 request per 2 seconds)
                    await asyncio.sleep(2)
                        
                except Exception as e:
                    transcripts_failed += 1
                    error_msg = f"Unexpected error processing video {video.id}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)
                    
                    # Try to mark as failed
                    try:
                        self.video_repo.mark_transcript_failed(video.id, str(e))
                    except Exception:
                        pass  # Don't cascade failures
            
            completed_at = datetime.now(timezone.utc)
            
            result = TranscriptExtractionResult(
                videos_attempted=len(pending_videos),
                transcripts_extracted=transcripts_extracted,
                transcripts_failed=transcripts_failed,
                transcripts_skipped=transcripts_skipped,
                errors=errors,
                started_at=started_at,
                completed_at=completed_at
            )
            
            logger.info(f"Transcript extraction completed for {target_date}: "
                       f"{transcripts_extracted}/{len(pending_videos)} successful "
                       f"({result.success_rate:.1f}% success rate)")
            
            return result
            
        except Exception as e:
            logger.error(f"Transcript extraction failed for {target_date}: {e}", exc_info=True)
            errors.append(f"Batch extraction failed: {str(e)}")
            
            return TranscriptExtractionResult(
                videos_attempted=0,
                transcripts_extracted=0,
                transcripts_failed=0,
                transcripts_skipped=0,
                errors=errors,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc)
            )
    
    def get_service_status(self) -> dict:
        """Get current status of transcript service.
        
        Returns:
            Service status information
        """
        client_info = self.client.get_client_info() if self.client else None
        
        return {
            "service": self.service_name,
            "status": "operational" if self.is_available() else "configuration_required",
            "description": "Real transcript extraction using transcript.io API" if self.is_available() 
                          else "Transcript service not configured (missing API key)",
            "client": client_info,
            "capabilities": [
                "transcript_extraction",
                "database_storage", 
                "transcript_retrieval",
                "batch_processing",
                "terminal_failure_detection",
                "idempotent_operations"
            ] if self.is_available() else [
                "simulation_mode"
            ],
            "features": [
                "Atomic processing (one-by-one)",
                "Dead letter handling for terminal failures",
                "Checkpointing with transcript_fetched flag",
                "Automatic retry prevention",
                "Comprehensive error handling"
            ] if self.is_available() else [
                "Configuration required"
            ]
        }