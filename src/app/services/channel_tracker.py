"""Channel tracker service for collecting videos from YouTube channels."""

from datetime import datetime
from typing import List, Optional

from app.client.google_oauth import GoogleOAuthClient
from app.config.settings import get_settings
from app.core.logging import logger
from app.models.channel import Channel, ChannelSyncResult, ChannelTrackerResult
from app.models.video import Video, VideoProcessingStatus


class ChannelTracker:
    """Service for tracking YouTube channels and collecting recent videos."""

    def __init__(
        self,
        credentials_json_path: Optional[str] = None,
        token_file: Optional[str] = None,
    ):
        """
        Initialize channel tracker.

        Args:
            credentials_json_path: Path to Google OAuth credentials JSON file.
                                  If None, uses settings.
            token_file: Path to token file. If None, uses settings.
        """
        self.settings = get_settings()

        # Initialize YouTube client
        creds_path = credentials_json_path or self.settings.google_credentials_json_path
        token_path = token_file or self.settings.google_token_file

        self.youtube_client = GoogleOAuthClient(
            credentials_json_path=creds_path,
            token_file=token_path,
        )

        # Authenticate
        logger.info("Authenticating with YouTube API...")
        self.youtube_client.authenticate()

    def get_tracked_channels(self) -> List[str]:
        """
        Get list of channel names/handles to track from configuration.

        Returns:
            List of channel names/handles
        """
        channels = self.settings.tracked_channels
        logger.info(f"Found {len(channels)} channels to track: {channels}")
        return channels

    def search_and_resolve_channel(self, channel_name: str) -> Optional[Channel]:
        """
        Search for a channel by name and resolve to full Channel object.

        Args:
            channel_name: Channel name or handle to search for

        Returns:
            Channel object if found, None otherwise
        """
        logger.debug(f"Resolving channel: {channel_name}")

        # Search for channel
        search_result = self.youtube_client.search_channel(channel_name)
        if not search_result:
            logger.warning(f"Channel not found: {channel_name}")
            return None

        channel_id = search_result["id"]
        logger.debug(f"Found channel ID: {channel_id}")

        # Get full metadata
        metadata = self.youtube_client.get_channel_metadata(channel_id)
        if not metadata:
            logger.warning(f"Could not fetch metadata for channel: {channel_id}")
            return None

        # Build Channel object
        channel = Channel(
            id=metadata["id"],
            name=metadata["title"],
            handle=metadata.get("custom_url"),
            custom_url=metadata.get("custom_url"),
            description=metadata.get("description"),
            thumbnail_url=metadata.get("thumbnail"),
            published_at=self._parse_datetime(metadata.get("published_at")),
            subscriber_count=metadata.get("subscriber_count"),
            video_count=metadata.get("video_count"),
            view_count=metadata.get("view_count"),
            uploads_playlist_id=metadata.get("uploads_playlist_id"),
            last_synced_at=datetime.utcnow(),
            raw_metadata=metadata,
        )

        logger.info(
            f"Resolved channel: {channel.name} ({channel.id}) - "
            f"{channel.subscriber_count:,} subscribers"
        )
        return channel

    def fetch_recent_videos(
        self, channel_id: str, hours: Optional[int] = None
    ) -> List[Video]:
        """
        Fetch recent videos from a channel.

        Args:
            channel_id: YouTube channel ID
            hours: Number of hours to look back (defaults to settings value)

        Returns:
            List of Video objects
        """
        lookback_hours = hours or self.settings.content_lookback_hours
        logger.debug(
            f"Fetching recent videos for channel {channel_id} "
            f"(last {lookback_hours} hours)"
        )

        # Get videos with metadata
        videos_data = self.youtube_client.get_recent_videos_with_metadata(
            channel_id, hours=lookback_hours
        )

        # Convert to Video objects
        videos = []
        for video_data in videos_data:
            video = Video(
                id=video_data["id"],
                channel_id=video_data["channel_id"],
                title=video_data["title"],
                description=video_data.get("description"),
                published_at=self._parse_datetime(video_data["published_at"]),
                view_count=video_data.get("view_count"),
                like_count=video_data.get("like_count"),
                comment_count=video_data.get("comment_count"),
                duration=video_data.get("duration"),
                thumbnail_url=video_data.get("thumbnail"),
                url=video_data["url"],
                status=VideoProcessingStatus.COLLECTED,
                collected_at=datetime.utcnow(),
                raw_metadata=video_data,
            )
            videos.append(video)

        logger.info(f"Collected {len(videos)} videos from channel {channel_id}")
        return videos

    def sync_channel(self, channel_name: str) -> ChannelSyncResult:
        """
        Sync a single channel: resolve it and fetch recent videos.

        Args:
            channel_name: Channel name or handle to sync

        Returns:
            ChannelSyncResult with channel and videos
        """
        sync_started_at = datetime.utcnow()
        logger.info(f"Syncing channel: {channel_name}")

        try:
            # Resolve channel
            channel = self.search_and_resolve_channel(channel_name)
            if not channel:
                error_msg = f"Could not resolve channel: {channel_name}"
                logger.error(error_msg)
                return ChannelSyncResult(
                    channel=Channel(
                        id="",
                        name=channel_name,
                        is_active=False,
                    ),
                    videos_collected=[],
                    videos_count=0,
                    sync_started_at=sync_started_at,
                    sync_completed_at=datetime.utcnow(),
                    error=error_msg,
                )

            # Fetch recent videos
            videos = self.fetch_recent_videos(channel.id)
            sync_completed_at = datetime.utcnow()

            result = ChannelSyncResult(
                channel=channel,
                videos_collected=videos,
                videos_count=len(videos),
                sync_started_at=sync_started_at,
                sync_completed_at=sync_completed_at,
            )

            logger.info(
                f"Successfully synced channel {channel.name}: "
                f"{len(videos)} videos collected in {result.duration_seconds:.2f}s"
            )
            return result

        except Exception as e:
            logger.error(f"Error syncing channel {channel_name}: {e}", exc_info=True)
            return ChannelSyncResult(
                channel=Channel(
                    id="",
                    name=channel_name,
                    is_active=False,
                ),
                videos_collected=[],
                videos_count=0,
                sync_started_at=sync_started_at,
                sync_completed_at=datetime.utcnow(),
                error=str(e),
            )

    def sync_all_channels(self) -> ChannelTrackerResult:
        """
        Sync all configured channels and collect recent videos.

        Returns:
            ChannelTrackerResult with all channels and videos
        """
        started_at = datetime.utcnow()
        logger.info("Starting channel sync for all tracked channels")

        # Get tracked channels
        channel_names = self.get_tracked_channels()
        if not channel_names:
            logger.warning("No channels configured to track")
            return ChannelTrackerResult(
                channels_processed=0,
                channels_found=0,
                channels_not_found=[],
                total_videos_collected=0,
                lookback_hours=self.settings.content_lookback_hours,
                sync_results=[],
                started_at=started_at,
                completed_at=datetime.utcnow(),
            )

        # Sync each channel
        sync_results: List[ChannelSyncResult] = []
        channels_found = 0
        channels_not_found: List[str] = []
        total_videos = 0

        for channel_name in channel_names:
            result = self.sync_channel(channel_name)

            if result.error or not result.channel.id:
                channels_not_found.append(channel_name)
            else:
                channels_found += 1
                total_videos += result.videos_count

            sync_results.append(result)

        completed_at = datetime.utcnow()

        tracker_result = ChannelTrackerResult(
            channels_processed=len(channel_names),
            channels_found=channels_found,
            channels_not_found=channels_not_found,
            total_videos_collected=total_videos,
            lookback_hours=self.settings.content_lookback_hours,
            sync_results=sync_results,
            started_at=started_at,
            completed_at=completed_at,
        )

        logger.info(
            f"Channel sync completed: {channels_found}/{len(channel_names)} channels found, "
            f"{total_videos} videos collected in {tracker_result.duration_seconds:.2f}s"
        )

        return tracker_result

    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        """
        Parse datetime string from YouTube API format.

        Args:
            dt_str: ISO format datetime string

        Returns:
            datetime object or None
        """
        if not dt_str:
            return None

        try:
            # YouTube API returns ISO format with Z suffix
            if dt_str.endswith("Z"):
                dt_str = dt_str[:-1] + "+00:00"
            return datetime.fromisoformat(dt_str)
        except (ValueError, AttributeError) as e:
            logger.warning(f"Could not parse datetime '{dt_str}': {e}")
            return None

