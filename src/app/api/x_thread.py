"""API endpoints for X thread posting."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.core.logging import logger
from app.core.utils.time_window import parse_date
from app.services.x_thread_service import XThreadService


router = APIRouter(prefix="/api/x-thread", tags=["x-thread"])


class XThreadPostResponse(BaseModel):
    """Response model for X thread posting."""
    success: bool
    target_date: str
    digest_id: Optional[str] = None
    tweet_count: int
    tweet_ids: Optional[List[str]] = None
    thread_url: Optional[str] = None
    errors: List[str] = []
    message: str


@router.post("/post-to-x/{date_str}", response_model=XThreadPostResponse)
async def post_digest_to_x(date_str: str) -> XThreadPostResponse:
    """Manually post digest to X for a specific date.

    Use cases:
    - Repost after editing digest
    - Post for a date where auto-post was disabled
    - Test X posting without running full pipeline

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        XThreadPostResponse with posting results
    """
    logger.info(f"API request to post digest to X for {date_str}")

    try:
        # Parse date
        target_date = parse_date(date_str)

        # Initialize service
        x_thread_service = XThreadService()

        # Post to X
        result = await x_thread_service.post_digest_to_x(target_date)

        # Check if already posted
        already_posted = False
        if result.errors and "Already posted" in result.errors[0]:
            already_posted = True

        # Build response
        if result.thread_posted:
            message = (
                f"Thread already exists for {date_str}"
                if already_posted
                else f"Thread posted successfully for {date_str}"
            )
            return XThreadPostResponse(
                success=True,
                target_date=date_str,
                tweet_count=result.tweet_count,
                tweet_ids=result.tweet_ids,
                thread_url=result.thread_url,
                errors=result.errors if not already_posted else [],
                message=message
            )
        else:
            return XThreadPostResponse(
                success=False,
                target_date=date_str,
                tweet_count=0,
                tweet_ids=None,
                thread_url=None,
                errors=result.errors,
                message=f"Failed to post thread for {date_str}"
            )

    except ValueError as e:
        logger.error(f"Invalid date format: {date_str}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")

    except Exception as e:
        logger.error(f"Failed to post digest to X for {date_str}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/preview/{date_str}")
async def preview_thread(date_str: str):
    """Generate thread preview without posting.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        Preview of generated thread
    """
    logger.info(f"API request to preview thread for {date_str}")

    try:
        # Parse date
        target_date = parse_date(date_str)

        # Initialize service
        x_thread_service = XThreadService()

        # Generate preview
        preview = await x_thread_service.generate_thread_preview(target_date)

        if preview:
            return {
                "success": True,
                "preview": preview
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No digest found for {date_str}"
            )

    except ValueError as e:
        logger.error(f"Invalid date format: {date_str}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to generate preview for {date_str}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
