"""API endpoints for orchestrator control."""

from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.core.logging import logger
from app.core.utils.time_window import parse_date
from app.models.pipeline import PipelineStatus
from app.services.orchestrator import ContentOrchestrator
from app.services.video_analysis_service import VideoAnalysisService
from app.api.schemas.orchestrator import (
    PipelineRunResponse,
    BackfillRequest,
    BackfillResponse,
    TranscriptExtractionResponse,
    VideoAnalysisResponse,
    DigestGenerationResponse,
    DigestSendRequest,
    DigestSendResponse,
    DigestContentResponse,
    ReprocessFailedResponse,
)

router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator"])


@router.post("/run-daily/{date_str}", response_model=PipelineRunResponse)
async def run_daily_pipeline(date_str: str) -> PipelineRunResponse:
    """
    Run the complete daily pipeline for a specific date.
    
    This endpoint triggers:
    1. Content extraction for the specified date
    2. Video processing (placeholder for now)
    3. Digest generation (placeholder for now)
    
    Args:
        date_str: Date in YYYY-MM-DD format
        
    Returns:
        PipelineRunResponse with execution results
    """
    logger.info(f"API request to run daily pipeline for {date_str}")
    
    try:
        # Parse date
        target_date = parse_date(date_str)
        
        # Initialize orchestrator
        orchestrator = ContentOrchestrator()
        
        # Run pipeline
        result = await orchestrator.run_daily_pipeline(target_date)
        
        return PipelineRunResponse(
            message=f"Pipeline completed for {date_str}",
            target_date=date_str,
            status="completed" if result.success else "failed",
            result=result
        )
        
    except ValueError as e:
        logger.error(f"Invalid date format: {date_str}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error(f"Pipeline execution failed for {date_str}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")


@router.post("/run-daily/{date_str}/async")
async def run_daily_pipeline_async(date_str: str, background_tasks: BackgroundTasks):
    """
    Run the daily pipeline asynchronously in the background.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        background_tasks: FastAPI background tasks
        
    Returns:
        Immediate response while pipeline runs in background
    """
    logger.info(f"API request to run daily pipeline async for {date_str}")
    
    try:
        # Parse date to validate format
        target_date = parse_date(date_str)
        
        # Add pipeline task to background
        async def run_pipeline():
            orchestrator = ContentOrchestrator()
            result = await orchestrator.run_daily_pipeline(target_date)
            if result.success:
                logger.info(f"Background pipeline completed successfully for {date_str}")
            else:
                logger.error(f"Background pipeline failed for {date_str}: {result.total_errors}")
        
        background_tasks.add_task(run_pipeline)
        
        return {
            "message": f"Pipeline started in background for {date_str}",
            "target_date": date_str,
            "status": "started",
            "note": "Check /api/orchestrator/status/{date} for progress"
        }
        
    except ValueError as e:
        logger.error(f"Invalid date format: {date_str}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to start background pipeline for {date_str}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start pipeline: {str(e)}")


@router.get("/status/{date_str}", response_model=PipelineStatus)
async def get_pipeline_status(date_str: str) -> PipelineStatus:
    """
    Get the current status of pipeline for a specific date.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        
    Returns:
        PipelineStatus with current state
    """
    logger.debug(f"API request for pipeline status for {date_str}")
    
    try:
        # Parse date
        target_date = parse_date(date_str)
        
        # Initialize orchestrator
        orchestrator = ContentOrchestrator()
        
        # Get status
        status = orchestrator.get_pipeline_status(target_date)
        
        return status
        
    except ValueError as e:
        logger.error(f"Invalid date format: {date_str}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to get pipeline status for {date_str}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@router.post("/backfill", response_model=BackfillResponse)
async def run_backfill(backfill_request: BackfillRequest) -> BackfillResponse:
    """
    Run pipeline for a range of dates (backfill operation).
    
    Args:
        backfill_request: Request with start_date and end_date
        
    Returns:
        BackfillResponse with results for all dates
    """
    logger.info(f"API request for backfill: {backfill_request.start_date} to {backfill_request.end_date}")
    
    try:
        # Parse dates
        start_date = parse_date(backfill_request.start_date)
        end_date = parse_date(backfill_request.end_date)
        
        if start_date > end_date:
            raise ValueError("start_date must be before or equal to end_date")
        
        # Initialize orchestrator
        orchestrator = ContentOrchestrator()
        
        # Run backfill
        results = await orchestrator.run_backfill(start_date, end_date)
        
        # Count successes and failures
        successful_runs = len([r for r in results if r.success])
        failed_runs = len(results) - successful_runs
        
        return BackfillResponse(
            message=f"Backfill completed for {backfill_request.start_date} to {backfill_request.end_date}",
            date_range=f"{backfill_request.start_date} to {backfill_request.end_date}",
            total_runs=len(results),
            successful_runs=successful_runs,
            failed_runs=failed_runs,
            results=results
        )
        
    except ValueError as e:
        logger.error(f"Invalid backfill request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Backfill execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Backfill execution failed: {str(e)}")


@router.post("/backfill/async")
async def run_backfill_async(backfill_request: BackfillRequest, background_tasks: BackgroundTasks):
    """
    Run backfill operation asynchronously in the background.
    
    Args:
        backfill_request: Request with start_date and end_date
        background_tasks: FastAPI background tasks
        
    Returns:
        Immediate response while backfill runs in background
    """
    logger.info(f"API request for async backfill: {backfill_request.start_date} to {backfill_request.end_date}")
    
    try:
        # Parse dates to validate format
        start_date = parse_date(backfill_request.start_date)
        end_date = parse_date(backfill_request.end_date)
        
        if start_date > end_date:
            raise ValueError("start_date must be before or equal to end_date")
        
        # Add backfill task to background
        async def run_backfill_task():
            orchestrator = ContentOrchestrator()
            results = await orchestrator.run_backfill(start_date, end_date)
            successful_runs = len([r for r in results if r.success])
            logger.info(
                f"Background backfill completed: {successful_runs}/{len(results)} successful "
                f"for {backfill_request.start_date} to {backfill_request.end_date}"
            )
        
        background_tasks.add_task(run_backfill_task)
        
        return {
            "message": f"Backfill started in background for {backfill_request.start_date} to {backfill_request.end_date}",
            "date_range": f"{backfill_request.start_date} to {backfill_request.end_date}",
            "status": "started",
            "note": "Backfill is running in background. Check logs for completion status."
        }
        
    except ValueError as e:
        logger.error(f"Invalid backfill request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start background backfill: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start backfill: {str(e)}")


@router.post("/extract-transcripts/{date_str}", response_model=TranscriptExtractionResponse)
async def extract_transcripts(date_str: str) -> TranscriptExtractionResponse:
    """
    Extract transcripts for all videos on a specific date.
    
    This endpoint triggers standalone transcript extraction:
    1. Finds videos published on the target date
    2. Extracts transcripts for videos that don't have them yet
    3. Saves transcripts to the database
    4. Updates video flags to prevent re-processing
    
    Args:
        date_str: Date in YYYY-MM-DD format
        
    Returns:
        TranscriptExtractionResponse with extraction results
    """
    logger.info(f"API request to extract transcripts for {date_str}")
    
    try:
        # Parse date
        target_date = parse_date(date_str)
        
        # Initialize orchestrator
        orchestrator = ContentOrchestrator()
        
        # Extract transcripts
        result = await orchestrator.extract_transcripts(target_date)
        
        return TranscriptExtractionResponse(
            message=f"Transcript extraction completed for {date_str}",
            target_date=date_str,
            status="completed" if result.transcripts_extracted > 0 or result.videos_attempted == 0 else "partial",
            result=result
        )
        
    except ValueError as e:
        logger.error(f"Invalid date format: {date_str}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error(f"Transcript extraction failed for {date_str}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcript extraction failed: {str(e)}")


@router.post("/extract-transcripts/{date_str}/async")
async def extract_transcripts_async(date_str: str, background_tasks: BackgroundTasks):
    """
    Extract transcripts asynchronously in the background.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        background_tasks: FastAPI background tasks
        
    Returns:
        Immediate response while transcript extraction runs in background
    """
    logger.info(f"API request to extract transcripts async for {date_str}")
    
    try:
        # Parse date to validate format
        target_date = parse_date(date_str)
        
        # Add transcript extraction task to background
        async def run_transcript_extraction():
            orchestrator = ContentOrchestrator()
            result = await orchestrator.extract_transcripts(target_date)
            logger.info(f"Background transcript extraction completed for {date_str}: "
                       f"{result.transcripts_extracted}/{result.videos_attempted} successful "
                       f"({result.success_rate:.1f}% success rate)")
        
        background_tasks.add_task(run_transcript_extraction)
        
        return {
            "message": f"Transcript extraction started in background for {date_str}",
            "target_date": date_str,
            "status": "started",
            "note": "Check logs for completion status"
        }
        
    except ValueError as e:
        logger.error(f"Invalid date format: {date_str}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to start background transcript extraction for {date_str}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start transcript extraction: {str(e)}")


@router.post("/process-video/{video_id}", response_model=VideoAnalysisResponse)
async def process_single_video(video_id: str) -> VideoAnalysisResponse:
    """
    Process a single video through the analysis pipeline.
    
    This endpoint:
    1. Validates the video exists and has a transcript
    2. Runs the complete video analysis workflow
    3. Saves results to the database
    4. Returns detailed analysis results
    
    Args:
        video_id: YouTube video ID to process
        
    Returns:
        VideoAnalysisResponse with analysis results and metrics
    """
    logger.info(f"API request to process video {video_id}")
    
    try:
        # Initialize video analysis service
        analysis_service = VideoAnalysisService()
        
        # Check if video already has analysis
        if await analysis_service.has_analysis(video_id):
            existing_analysis = await analysis_service.get_analysis(video_id)
            return VideoAnalysisResponse(
                message=f"Video {video_id} already analyzed",
                video_id=video_id,
                status="already_processed",
                analysis=existing_analysis,
                processing_time_seconds=existing_analysis.total_processing_time_seconds if existing_analysis else 0,
                total_cost=existing_analysis.total_cost if existing_analysis else 0,
                total_tokens=existing_analysis.total_tokens if existing_analysis else 0
            )
        
        # Analyze video
        import time
        start_time = time.time()
        
        analysis = await analysis_service.analyze_video(video_id)
        
        processing_time = time.time() - start_time
        
        if analysis:
            return VideoAnalysisResponse(
                message=f"Video {video_id} analyzed successfully",
                video_id=video_id,
                status="completed",
                analysis=analysis,
                processing_time_seconds=processing_time,
                total_cost=analysis.total_cost,
                total_tokens=analysis.total_tokens
            )
        else:
            return VideoAnalysisResponse(
                message=f"Video {video_id} analysis failed",
                video_id=video_id,
                status="failed"
            )
            
    except Exception as e:
        logger.error(f"Video analysis failed for {video_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Video analysis failed: {str(e)}")


@router.post("/process-video/{video_id}/async")
async def process_single_video_async(video_id: str, background_tasks: BackgroundTasks):
    """
    Process a single video asynchronously in the background.
    
    Args:
        video_id: YouTube video ID to process
        background_tasks: FastAPI background tasks
        
    Returns:
        Immediate response while video analysis runs in background
    """
    logger.info(f"API request to process video {video_id} async")
    
    try:
        # Add video analysis task to background
        async def run_video_analysis():
            analysis_service = VideoAnalysisService()
            analysis = await analysis_service.analyze_video(video_id)
            if analysis:
                logger.info(f"Background video analysis completed successfully for {video_id}")
            else:
                logger.error(f"Background video analysis failed for {video_id}")
        
        background_tasks.add_task(run_video_analysis)
        
        return {
            "message": f"Video analysis started in background for {video_id}",
            "video_id": video_id,
            "status": "started",
            "note": "Check logs for completion status"
        }
        
    except Exception as e:
        logger.error(f"Failed to start background video analysis for {video_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start video analysis: {str(e)}")


@router.post("/reprocess-failed/{date_str}", response_model=ReprocessFailedResponse)
async def reprocess_failed_videos(date_str: str) -> ReprocessFailedResponse:
    """
    Reprocess videos that failed analysis for a specific date.
    
    This endpoint:
    1. Finds all failed videos for the target date
    2. Deletes their existing analysis data (if any)
    3. Resets their status back to 'collected'
    4. Runs the analysis pipeline on them
    
    Args:
        date_str: Date in YYYY-MM-DD format
        
    Returns:
        ReprocessFailedResponse with reprocessing results
    """
    logger.info(f"API request to reprocess failed videos for {date_str}")
    
    try:
        # Parse date
        target_date = parse_date(date_str)
        
        # Initialize orchestrator
        orchestrator = ContentOrchestrator()
        
        # Get count of failed videos before reprocessing
        from app.repositories.video_repository import VideoRepository
        video_repo = VideoRepository()
        failed_videos = video_repo.get_failed_videos(target_date)
        videos_found = len(failed_videos)
        
        # Reprocess failed videos
        result = await orchestrator.reprocess_failed_videos(target_date)
        
        return ReprocessFailedResponse(
            message=f"Reprocessed failed videos for {date_str}",
            target_date=date_str,
            status="completed" if result.analyses_completed > 0 else "no_videos" if videos_found == 0 else "failed",
            videos_found=videos_found,
            videos_reprocessed=result.videos_processed,
            analyses_completed=result.analyses_completed,
            errors=result.errors
        )
        
    except ValueError as e:
        logger.error(f"Invalid date format: {date_str}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to reprocess videos for {date_str}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Reprocessing failed: {str(e)}")


@router.post("/reprocess-failed/{date_str}/async")
async def reprocess_failed_videos_async(date_str: str, background_tasks: BackgroundTasks):
    """
    Reprocess failed videos asynchronously in the background.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        background_tasks: FastAPI background tasks
        
    Returns:
        Immediate response while reprocessing runs in background
    """
    logger.info(f"API request to reprocess failed videos async for {date_str}")
    
    try:
        # Parse date to validate format
        target_date = parse_date(date_str)
        
        # Get count of failed videos
        from app.repositories.video_repository import VideoRepository
        video_repo = VideoRepository()
        failed_videos = video_repo.get_failed_videos(target_date)
        videos_found = len(failed_videos)
        
        # Add reprocessing task to background
        async def run_reprocessing():
            orchestrator = ContentOrchestrator()
            result = await orchestrator.reprocess_failed_videos(target_date)
            logger.info(
                f"Background reprocessing completed for {date_str}: "
                f"{result.analyses_completed}/{result.videos_processed} successful"
            )
        
        background_tasks.add_task(run_reprocessing)
        
        return {
            "message": f"Reprocessing started in background for {date_str}",
            "target_date": date_str,
            "videos_found": videos_found,
            "status": "started",
            "note": "Check logs for completion status"
        }
        
    except ValueError as e:
        logger.error(f"Invalid date format: {date_str}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to start background reprocessing for {date_str}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start reprocessing: {str(e)}")


@router.get("/analysis/stats")
async def get_analysis_stats(days: int = 30):
    """
    Get video analysis statistics for monitoring.
    
    Args:
        days: Number of days to look back (default: 30)
        
    Returns:
        Analysis statistics including costs, processing times, and success rates
    """
    try:
        analysis_service = VideoAnalysisService()
        stats = await analysis_service.get_analysis_stats(days)
        
        return {
            "status": "success",
            "data": stats,
            "days_analyzed": days
        }
        
    except Exception as e:
        logger.error(f"Failed to get analysis stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get analysis stats: {str(e)}")


@router.get("/health")
async def health_check():
    """
    Health check endpoint for orchestrator service.

    Returns:
        Simple health status
    """
    return {
        "status": "healthy",
        "service": "orchestrator",
        "message": "Orchestrator service is operational"
    }


# ========== Daily Digest Endpoints ==========

@router.post("/generate-digest/{date_str}", response_model=DigestGenerationResponse)
async def generate_digest(date_str: str) -> DigestGenerationResponse:
    """
    Generate a daily digest for a specific date.

    This endpoint triggers the daily digest workflow:
    1. Loads all video analyses for the target date
    2. Generates cohesive newsletter content via LLM
    3. Saves digest with markdown/HTML to database
    4. Extracts and upserts references for cross-day tracking

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        DigestGenerationResponse with generation results
    """
    logger.info(f"API request to generate digest for {date_str}")

    try:
        # Parse date
        target_date = parse_date(date_str)

        # Import here to avoid circular imports
        from app.agents.daily_digest import generate_daily_digest

        # Generate digest
        result = await generate_daily_digest(target_date)

        if result and result.success:
            message = (
                f"Digest saved for {date_str} - no content to report"
                if result.is_empty
                else f"Digest generated successfully for {date_str}"
            )
            return DigestGenerationResponse(
                message=message,
                target_date=date_str,
                status="completed",
                result=result
            )
        else:
            return DigestGenerationResponse(
                message=f"Digest generation failed for {date_str}",
                target_date=date_str,
                status="failed",
                result=result
            )

    except ValueError as e:
        logger.error(f"Invalid date format: {date_str}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error(f"Digest generation failed for {date_str}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Digest generation failed: {str(e)}")


@router.post("/generate-digest/{date_str}/async")
async def generate_digest_async(date_str: str, background_tasks: BackgroundTasks):
    """
    Generate a daily digest asynchronously in the background.

    Args:
        date_str: Date in YYYY-MM-DD format
        background_tasks: FastAPI background tasks

    Returns:
        Immediate response while digest generation runs in background
    """
    logger.info(f"API request to generate digest async for {date_str}")

    try:
        # Parse date to validate format
        target_date = parse_date(date_str)

        # Add digest generation task to background
        async def run_digest_generation():
            from app.agents.daily_digest import generate_daily_digest
            result = await generate_daily_digest(target_date)
            if result and result.success:
                logger.info(f"Background digest generation completed for {date_str}: {result.digest_id}")
            else:
                logger.error(f"Background digest generation failed for {date_str}")

        background_tasks.add_task(run_digest_generation)

        return {
            "message": f"Digest generation started in background for {date_str}",
            "target_date": date_str,
            "status": "started",
            "note": "Check /api/orchestrator/digest/{date} to see the result"
        }

    except ValueError as e:
        logger.error(f"Invalid date format: {date_str}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to start background digest generation for {date_str}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start digest generation: {str(e)}")


@router.get("/digest/{date_str}", response_model=DigestContentResponse)
async def get_digest(date_str: str) -> DigestContentResponse:
    """
    Get the digest content for a specific date.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        DigestContentResponse with digest content
    """
    logger.debug(f"API request for digest content for {date_str}")

    try:
        # Parse date
        target_date = parse_date(date_str)

        # Get digest from repository
        from app.repositories.daily_digest_repository import DailyDigestRepository
        digest_repo = DailyDigestRepository()

        digest = await digest_repo.get_digest_by_date(target_date)

        if not digest:
            return DigestContentResponse(
                message=f"No digest found for {date_str}",
                target_date=date_str,
            )

        return DigestContentResponse(
            message=f"Digest found for {date_str}",
            target_date=date_str,
            digest_id=str(digest.id) if digest.id else None,
            title=digest.title,
            content_json=digest.content_json,
            markdown=digest.formatted_markdown,
            html=digest.formatted_html,
            video_count=digest.video_count,
            channels=digest.channels_included,
            is_sent=digest.is_sent,
            sent_at=digest.sent_at.isoformat() if digest.sent_at else None
        )

    except ValueError as e:
        logger.error(f"Invalid date format: {date_str}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to get digest for {date_str}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get digest: {str(e)}")


@router.post("/send-digest/{date_str}", response_model=DigestSendResponse)
async def send_digest(date_str: str, request: DigestSendRequest = None) -> DigestSendResponse:
    """
    Send a digest email for a specific date.

    If test_email is provided, sends only to that email.
    Otherwise, sends to all active subscribers.

    Args:
        date_str: Date in YYYY-MM-DD format
        request: Optional send request with test_email

    Returns:
        DigestSendResponse with send results
    """
    logger.info(f"API request to send digest for {date_str}")

    try:
        # Parse date
        target_date = parse_date(date_str)

        # Get digest from repository
        from app.repositories.daily_digest_repository import DailyDigestRepository
        from app.services.email_service import EmailService

        digest_repo = DailyDigestRepository()
        email_service = EmailService()

        digest = await digest_repo.get_digest_by_date(target_date)

        if not digest:
            raise HTTPException(status_code=404, detail=f"No digest found for {date_str}")

        digest_id = str(digest.id) if digest.id else None
        if not digest_id:
            raise HTTPException(status_code=400, detail="Digest has no ID")

        # Send email
        if request and request.test_email:
            result = await email_service.send_test_digest(digest_id, request.test_email)
        else:
            result = await email_service.send_digest_to_subscribers(digest_id)

        if result.success:
            return DigestSendResponse(
                message=f"Digest sent successfully for {date_str}",
                digest_id=digest_id,
                status="sent",
                result=result
            )
        else:
            return DigestSendResponse(
                message=f"Digest send failed for {date_str}",
                digest_id=digest_id,
                status="failed",
                result=result
            )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Invalid date format: {date_str}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to send digest for {date_str}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send digest: {str(e)}")


@router.get("/references/top")
async def get_top_references(reference_type: str = None, limit: int = 20):
    """
    Get top referenced items across all digests.

    Args:
        reference_type: Optional filter by type (book, concept, framework, person, community)
        limit: Maximum number of references to return (default: 20)

    Returns:
        List of top references sorted by mention count
    """
    try:
        from app.repositories.daily_digest_repository import DailyDigestRepository
        digest_repo = DailyDigestRepository()

        references = await digest_repo.get_top_references(
            reference_type=reference_type,
            limit=limit
        )

        return {
            "status": "success",
            "reference_type": reference_type,
            "count": len(references),
            "references": [
                {
                    "name": ref.name,
                    "type": ref.reference_type,
                    "author": ref.author,
                    "url": ref.url,
                    "description": ref.description,
                    "mention_count": ref.mention_count,
                    "first_seen": ref.first_seen_date.isoformat() if ref.first_seen_date else None,
                }
                for ref in references
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get top references: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get references: {str(e)}")


@router.get("/references/search/{name}")
async def search_reference(name: str):
    """
    Search for a reference and get its cross-day history.

    Args:
        name: Name of the reference to search for

    Returns:
        Reference history showing all mentions across digests
    """
    try:
        from app.repositories.daily_digest_repository import DailyDigestRepository
        digest_repo = DailyDigestRepository()

        history = await digest_repo.get_reference_history(name)

        return {
            "status": "success",
            "search_term": name,
            "results": history
        }

    except Exception as e:
        logger.error(f"Failed to search reference {name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to search reference: {str(e)}")