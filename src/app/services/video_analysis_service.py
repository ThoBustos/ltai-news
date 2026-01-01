"""Video analysis service to orchestrate the LangGraph workflow."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any

from app.core.logging import logger
from app.models.video_analysis import VideoAnalysisComplete
from app.repositories.video_analysis_repository import VideoAnalysisRepository
from app.repositories.video_repository import VideoRepository
from app.agents.video_analyzer import analyze_video


class VideoAnalysisService:
    """Service for orchestrating video analysis using LangGraph workflow."""
    
    def __init__(self):
        """Initialize video analysis service."""
        self.service_name = "video_analysis_service"
        self.video_repo = VideoRepository()
        self.analysis_repo = VideoAnalysisRepository()
        logger.info("Initialized VideoAnalysisService")
    
    async def analyze_video(self, video_id: str) -> Optional[VideoAnalysisComplete]:
        """Analyze a single video through the complete workflow.
        
        Args:
            video_id: YouTube video ID to analyze
            
        Returns:
            VideoAnalysisComplete if successful, None if failed
        """
        logger.info(f"Starting video analysis for {video_id}")
        
        try:
            # Check if analysis already exists (idempotency)
            if await self.has_analysis(video_id):
                logger.info(f"Analysis already exists for video {video_id}, returning existing")
                return await self.get_analysis(video_id)
            
            # Validate prerequisites
            if not await self._validate_prerequisites(video_id):
                logger.error(f"Prerequisites not met for video {video_id}")
                return None
            
            # Update video status to PROCESSING
            await self._update_video_status(video_id, "processing")
            
            # Execute LangGraph workflow
            analysis = await analyze_video(video_id)
            
            if not analysis:
                await self._update_video_status(video_id, "failed", "Analysis workflow returned None")
                return None
            
            # Update video status to PROCESSED
            await self._update_video_status(video_id, "processed")
            
            logger.info(f"Video analysis completed successfully for {video_id}")
            return analysis
            
        except Exception as e:
            logger.error(f"Video analysis failed for {video_id}: {e}", exc_info=True)
            await self._update_video_status(video_id, "failed", str(e))
            return None
    
    async def has_analysis(self, video_id: str) -> bool:
        """Check if video has existing analysis.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            True if analysis exists, False otherwise
        """
        try:
            return await self.analysis_repo.has_analysis(video_id)
        except Exception as e:
            logger.error(f"Failed to check analysis existence for {video_id}: {e}")
            return False
    
    async def get_analysis(self, video_id: str) -> Optional[VideoAnalysisComplete]:
        """Get existing analysis for video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            VideoAnalysisComplete if exists, None otherwise
        """
        try:
            return await self.analysis_repo.get_analysis(video_id)
        except Exception as e:
            logger.error(f"Failed to get analysis for {video_id}: {e}")
            return None

    async def delete_analysis(self, video_id: str) -> bool:
        """Delete existing analysis for video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            return await self.analysis_repo.delete_analysis(video_id)
        except Exception as e:
            logger.error(f"Failed to delete analysis for {video_id}: {e}")
            return False
    
    async def get_videos_needing_analysis(self, limit: int = 100) -> list:
        """Get videos that need analysis (have transcripts but no analysis).
        
        Args:
            limit: Maximum number of videos to return
            
        Returns:
            List of video objects needing analysis
        """
        try:
            # Get videos with transcripts but no analysis
            videos = self.video_repo.get_unprocessed_videos(limit=limit)
            
            # Filter to only those with transcripts and no analysis
            needing_analysis = []
            for video in videos:
                if (self.video_repo.has_transcript(video.id) and 
                    not await self.has_analysis(video.id)):
                    needing_analysis.append(video)
            
            logger.info(f"Found {len(needing_analysis)} videos needing analysis")
            return needing_analysis
            
        except Exception as e:
            logger.error(f"Failed to get videos needing analysis: {e}")
            return []
    
    async def bulk_analyze_videos(self, video_ids: list, max_concurrent: int = 3) -> Dict[str, Any]:
        """Analyze multiple videos with controlled concurrency.
        
        Args:
            video_ids: List of video IDs to analyze
            max_concurrent: Maximum concurrent analyses
            
        Returns:
            Dictionary with analysis results and statistics
        """
        logger.info(f"Starting bulk analysis of {len(video_ids)} videos")
        
        import asyncio
        
        results = {
            "total_videos": len(video_ids),
            "successful": 0,
            "failed": 0,
            "errors": [],
            "started_at": datetime.now(timezone.utc)
        }
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_with_semaphore(video_id):
            async with semaphore:
                try:
                    analysis = await self.analyze_video(video_id)
                    if analysis:
                        results["successful"] += 1
                        return {"video_id": video_id, "success": True, "analysis": analysis}
                    else:
                        results["failed"] += 1
                        error_msg = f"Analysis returned None for video {video_id}"
                        results["errors"].append(error_msg)
                        return {"video_id": video_id, "success": False, "error": error_msg}
                except Exception as e:
                    results["failed"] += 1
                    error_msg = f"Analysis failed for video {video_id}: {str(e)}"
                    results["errors"].append(error_msg)
                    return {"video_id": video_id, "success": False, "error": error_msg}
        
        # Execute analyses concurrently
        tasks = [analyze_with_semaphore(video_id) for video_id in video_ids]
        analysis_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        results["completed_at"] = datetime.now(timezone.utc)
        results["analysis_results"] = analysis_results
        
        logger.info(
            f"Bulk analysis completed: {results['successful']}/{len(video_ids)} successful, "
            f"{results['failed']} failed"
        )
        
        return results
    
    async def _validate_prerequisites(self, video_id: str) -> bool:
        """Validate that video has all prerequisites for analysis.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            True if all prerequisites met, False otherwise
        """
        # Check video exists
        video = self.video_repo.get_by_id(video_id)
        if not video:
            logger.error(f"Video {video_id} not found")
            return False
        
        # Check transcript exists
        if not self.video_repo.has_transcript(video_id):
            logger.error(f"No transcript found for video {video_id}")
            return False
        
        # Check transcript is not empty
        transcript = self.video_repo.get_transcript(video_id)
        if not transcript or len(transcript.strip()) < 100:
            logger.error(f"Transcript too short for video {video_id}")
            return False
        
        return True
    
    async def _update_video_status(self, video_id: str, status: str, error_msg: Optional[str] = None):
        """Update video processing status.
        
        Args:
            video_id: YouTube video ID
            status: New status (processing, processed, failed)
            error_msg: Optional error message for failed status
        """
        try:
            from app.models.video import VideoProcessingStatus
            
            status_enum = VideoProcessingStatus(status)
            processed_at = datetime.now(timezone.utc) if status == "processed" else None
            
            self.video_repo.update_status(
                video_id=video_id,
                status=status_enum,
                processed_at=processed_at,
                processing_error=error_msg
            )
            
            logger.debug(f"Updated video {video_id} status to {status}")
            
        except Exception as e:
            logger.warning(f"Failed to update video status for {video_id}: {e}")
            # Don't fail the whole operation for status update issues
    
    async def get_analysis_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get analysis statistics for monitoring.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with analysis statistics
        """
        try:
            from datetime import timedelta
            
            date_filter = datetime.now(timezone.utc) - timedelta(days=days)
            stats = await self.analysis_repo.get_processing_stats(date_filter)
            
            # Add service-level stats
            stats.update({
                "service": self.service_name,
                "days_analyzed": days,
                "generated_at": datetime.now(timezone.utc).isoformat()
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get analysis stats: {e}")
            return {
                "service": self.service_name,
                "error": str(e),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
    
    def get_service_status(self) -> dict:
        """Get current status of video analysis service.
        
        Returns:
            Service status information
        """
        return {
            "service": self.service_name,
            "status": "operational",
            "description": "Video analysis using LangGraph + Gemini 3.0 Flash with structured outputs",
            "model": "gemini-3.0-flash",
            "workflow": "single-master-prompt",
            "capabilities": [
                "comprehensive_video_analysis",
                "structured_extraction",
                "cost_tracking",
                "opik_observability",
                "bulk_processing",
                "idempotent_operations"
            ],
            "features": [
                "Single master prompt for cost optimization",
                "Structured outputs with Pydantic validation",
                "Comprehensive Opik integration",
                "Automatic error handling and recovery",
                "Processing status tracking",
                "JSONB storage with rich metadata"
            ],
            "dependencies": [
                "LangGraph workflow engine",
                "Gemini 3.0 Flash API",
                "Opik observability platform",
                "VideoRepository (video + transcript data)",
                "VideoAnalysisRepository (analysis storage)"
            ]
        }