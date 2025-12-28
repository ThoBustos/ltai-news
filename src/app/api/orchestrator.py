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