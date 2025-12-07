"""API endpoints for channel tracking."""

from fastapi import APIRouter, HTTPException

from app.config.settings import get_settings
from app.core.logging import logger
from app.models.channel import ChannelTrackerResult
from app.services.channel_tracker import ChannelTracker

router = APIRouter(prefix="/api/channels", tags=["channels"])


@router.get("/list")
async def list_tracked_channels():
    """
    Get list of configured channels to track.

    Returns:
        List of channel names/handles from configuration
    """
    settings = get_settings()
    return {
        "channels": settings.tracked_channels,
        "lookback_hours": settings.content_lookback_hours,
    }


@router.post("/sync")
async def sync_channels() -> ChannelTrackerResult:
    """
    Trigger manual sync of all configured channels.

    This will:
    1. Resolve all channel names/handles to YouTube channel IDs
    2. Fetch recent videos from each channel (last N hours)
    3. Return structured data ready for database storage

    Returns:
        ChannelTrackerResult with all channels and videos collected
    """
    logger.info("Manual channel sync triggered via API")
    try:
        tracker = ChannelTracker()
        result = tracker.sync_all_channels()
        return result
    except Exception as e:
        logger.error(f"Error during channel sync: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Channel sync failed: {str(e)}")


@router.post("/resolve/{channel_name}")
async def resolve_channel(channel_name: str):
    """
    Resolve a channel name/handle to YouTube channel metadata.

    Useful for testing channel configuration before adding to TRACKED_CHANNELS.

    Args:
        channel_name: Channel name or handle to resolve

    Returns:
        Channel metadata if found
    """
    logger.info(f"Resolving channel via API: {channel_name}")
    try:
        tracker = ChannelTracker()
        channel = tracker.search_and_resolve_channel(channel_name)
        if not channel:
            raise HTTPException(
                status_code=404, detail=f"Channel not found: {channel_name}"
            )
        return channel
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving channel: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Channel resolution failed: {str(e)}"
        )

