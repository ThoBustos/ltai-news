"""Channel tracker service for collecting videos from YouTube channels."""

from datetime import datetime, date
from typing import List, Optional

from app.client.google_oauth import GoogleOAuthClient
from app.config.settings import settings
from app.core.logging import logger
from app.core.utils.time_window import TimeWindow, get_window
from app.models.channel import Channel, ChannelSyncResult, ChannelTrackerResult
from app.models.video import Video, VideoProcessingStatus
from app.repositories import ChannelRepository, VideoRepository


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
        dt_str_clean = str(dt_str)
        if dt_str_clean.endswith("Z"):
            dt_str_clean = dt_str_clean[:-1] + "+00:00"
        return datetime.fromisoformat(dt_str_clean)
    except (ValueError, AttributeError) as e:
        logger.warning(f"Could not parse datetime '{dt_str}': {e}")
        return None


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
        self.settings = settings

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

        # Initialize repositories
        self.channel_repo = ChannelRepository()
        self.video_repo = VideoRepository()

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
            published_at=_parse_datetime(metadata.get("published_at")),
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
        self, channel_id: str, hours: Optional[int] = None, bypass_duration: bool = False
    ) -> List[Video]:
        """
        Fetch recent videos from a channel.

        Args:
            channel_id: YouTube channel ID
            hours: Number of hours to look back (defaults to settings value)
            bypass_duration: If True, skips the minimum duration filter

        Returns:
            List of Video objects
        """
        lookback_hours = hours or self.settings.content_lookback_hours
        logger.debug(
            f"Fetching recent videos for channel {channel_id} "
            f"(last {lookback_hours} hours, bypass_duration={bypass_duration})"
        )

        # Get videos with metadata
        videos_data = self.youtube_client.get_recent_videos_with_metadata(
            channel_id, hours=lookback_hours
        )

        # Convert to Video objects
        videos = []
        min_duration_secs = self.settings.min_video_duration_minutes * 60
        
        for video_data in videos_data:
            # Skip if video is too short (unless bypassing)
            duration_secs = video_data.get("duration_seconds", 0)
            if not bypass_duration and duration_secs < min_duration_secs:
                logger.info(
                    f"Skipping video {video_data['id']} - duration {duration_secs}s "
                    f"is less than minimum {min_duration_secs}s (channel not bypassed)"
                )
                continue
                
            video = Video(
                id=video_data["id"],
                channel_id=video_data["channel_id"],
                title=video_data["title"],
                description=video_data.get("description"),
                published_at=_parse_datetime(video_data["published_at"]),
                view_count=video_data.get("view_count"),
                like_count=video_data.get("like_count"),
                comment_count=video_data.get("comment_count"),
                duration=video_data.get("duration"),
                duration_seconds=video_data.get("duration_seconds"),
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
            # 1. Try to find channel in database first to save quota (search = 100 units)
            channel = self.channel_repo.get_by_name(channel_name)
            if not channel:
                channel = self.channel_repo.get_by_handle(channel_name)
            
            if channel:
                logger.debug(f"Found channel {channel.name} in database, skipping search")
            else:
                # 2. Resolve channel via YouTube API search if not found in DB
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

            # Save/Update channel to database
            try:
                self.channel_repo.upsert_channel(channel)
            except Exception as e:
                logger.warning(f"Failed to save channel to database: {e}")

            # Check for bypasses
            bypass_duration = any(
                b.lower() in [channel_name.lower(), channel.name.lower(), channel.handle.lower() if channel.handle else ""] 
                for b in self.settings.bypass_duration_channels
            )
            bypass_lookback = any(
                b.lower() in [channel_name.lower(), channel.name.lower(), channel.handle.lower() if channel.handle else ""] 
                for b in self.settings.bypass_lookback_channels
            )
            
            hours = self.settings.extended_lookback_hours if bypass_lookback else None
            if bypass_duration:
                logger.info(f"Channel {channel.name} is bypassing duration limits")
            if bypass_lookback:
                logger.info(f"Channel {channel.name} is bypassing lookback limits (using {hours} hours)")

            # Fetch recent videos
            videos = self.fetch_recent_videos(channel.id, hours=hours, bypass_duration=bypass_duration)

            # Save videos to database (only new ones)
            saved_videos = []
            for video in videos:
                try:
                    self.video_repo.upsert_video(video)
                    saved_videos.append(video)
                except Exception as e:
                    logger.warning(f"Failed to save video {video.id} to database: {e}")
                    # Still include in result even if DB save failed
                    saved_videos.append(video)

            # Update channel last_synced_at
            try:
                self.channel_repo.update_last_synced(channel.id)
            except Exception as e:
                logger.warning(f"Failed to update last_synced_at for channel {channel.id}: {e}")

            sync_completed_at = datetime.utcnow()

            result = ChannelSyncResult(
                channel=channel,
                videos_collected=saved_videos,
                videos_count=len(saved_videos),
                sync_started_at=sync_started_at,
                sync_completed_at=sync_completed_at,
            )

            logger.info(
                f"Successfully synced channel {channel.name}: "
                f"{len(saved_videos)} videos collected in {result.duration_seconds:.2f}s"
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

    def sync_channels_for_date(self, target_date: date) -> ChannelTrackerResult:
        """
        Sync all channels for a specific date window.
        
        This method fetches videos only within the 24-hour UTC window
        for the specified date.

        Args:
            target_date: Date to sync channels for

        Returns:
            ChannelTrackerResult with channels and videos for the date
        """
        started_at = datetime.utcnow()
        window = get_window(target_date)
        logger.info(f"Syncing all channels for date {target_date} (window: {window.start_utc} to {window.end_utc})")

        # Get tracked channels
        channel_names = self.get_tracked_channels()
        if not channel_names:
            logger.warning("No channels configured to track")
            return ChannelTrackerResult(
                channels_processed=0,
                channels_found=0,
                channels_not_found=[],
                total_videos_collected=0,
                lookback_hours=24,  # Fixed 24h window
                sync_results=[],
                started_at=started_at,
                completed_at=datetime.utcnow(),
            )

        # Sync each channel for the specific date
        sync_results: List[ChannelSyncResult] = []
        channels_found = 0
        channels_not_found: List[str] = []
        total_videos = 0

        for channel_name in channel_names:
            result = self.sync_channel_for_date(channel_name, target_date)

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
            lookback_hours=24,  # Fixed 24h window
            sync_results=sync_results,
            started_at=started_at,
            completed_at=completed_at,
        )

        logger.info(
            f"Channel sync for {target_date} completed: {channels_found}/{len(channel_names)} channels found, "
            f"{total_videos} videos collected in {tracker_result.duration_seconds:.2f}s"
        )

        return tracker_result

    def sync_channel_for_date(self, channel_name: str, target_date: date) -> ChannelSyncResult:
        """
        Sync a single channel for a specific date window.

        Args:
            channel_name: Channel name or handle to sync
            target_date: Date to sync channel for

        Returns:
            ChannelSyncResult with channel and videos for the date
        """
        sync_started_at = datetime.utcnow()
        window = get_window(target_date)
        logger.info(f"Syncing channel {channel_name} for date {target_date}")

        try:
            # 1. Try to find channel in database first to save quota (search = 100 units)
            channel = self.channel_repo.get_by_name(channel_name)
            if not channel:
                channel = self.channel_repo.get_by_handle(channel_name)
            
            if channel:
                logger.debug(f"Found channel {channel.name} in database, skipping search")
            else:
                # 2. Resolve channel via YouTube API search if not found in DB
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

            # Save/Update channel to database
            try:
                self.channel_repo.upsert_channel(channel)
            except Exception as e:
                logger.warning(f"Failed to save channel to database: {e}")

            # Check for bypasses (only duration bypass applies here as window is fixed)
            bypass_duration = any(
                b.lower() in [channel_name.lower(), channel.name.lower(), channel.handle.lower() if channel.handle else ""] 
                for b in self.settings.bypass_duration_channels
            )
            if bypass_duration:
                logger.info(f"Channel {channel.name} is bypassing duration limits for date {target_date}")

            # Fetch videos in window
            videos = self.fetch_videos_in_window(channel.id, window, bypass_duration=bypass_duration)

            # Save videos to database (only new ones)
            saved_videos = []
            for video in videos:
                try:
                    self.video_repo.upsert_video(video)
                    saved_videos.append(video)
                except Exception as e:
                    logger.warning(f"Failed to save video {video.id} to database: {e}")
                    # Still include in result even if DB save failed
                    saved_videos.append(video)

            # Update channel last_synced_at
            try:
                self.channel_repo.update_last_synced(channel.id)
            except Exception as e:
                logger.warning(f"Failed to update last_synced_at for channel {channel.id}: {e}")

            sync_completed_at = datetime.utcnow()

            result = ChannelSyncResult(
                channel=channel,
                videos_collected=saved_videos,
                videos_count=len(saved_videos),
                sync_started_at=sync_started_at,
                sync_completed_at=sync_completed_at,
            )

            logger.info(
                f"Successfully synced channel {channel.name} for {target_date}: "
                f"{len(saved_videos)} videos collected in {result.duration_seconds:.2f}s"
            )
            return result

        except Exception as e:
            logger.error(f"Error syncing channel {channel_name} for {target_date}: {e}", exc_info=True)
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

    def fetch_videos_in_window(self, channel_id: str, window: TimeWindow, bypass_duration: bool = False) -> List[Video]:
        """
        Fetch videos from a channel within a specific time window.

        Args:
            channel_id: YouTube channel ID
            window: TimeWindow to filter videos by
            bypass_duration: If True, skips the minimum duration filter

        Returns:
            List of Video objects published within the window
        """
        logger.debug(
            f"Fetching videos for channel {channel_id} in window "
            f"{window.start_utc} to {window.end_utc} (bypass_duration={bypass_duration})"
        )

        # Get videos with metadata using the window start as our lookback anchor
        videos_data = self.youtube_client.get_recent_videos_with_metadata(
            channel_id, since_datetime=window.start_utc
        )

        # Filter videos to only include those in our exact window
        videos = []
        min_duration_secs = self.settings.min_video_duration_minutes * 60
        
        for video_data in videos_data:
            published_at = _parse_datetime(video_data["published_at"])
            if published_at and window.contains(published_at):
                # Skip if video is too short (unless bypassing)
                duration_secs = video_data.get("duration_seconds", 0)
                if not bypass_duration and duration_secs < min_duration_secs:
                    logger.info(
                        f"Skipping video {video_data['id']} - duration {duration_secs}s "
                        f"is less than minimum {min_duration_secs}s (channel not bypassed)"
                    )
                    continue
                    
                video = Video(
                    id=video_data["id"],
                    channel_id=video_data["channel_id"],
                    title=video_data["title"],
                    description=video_data.get("description"),
                    published_at=published_at,
                    view_count=video_data.get("view_count"),
                    like_count=video_data.get("like_count"),
                    comment_count=video_data.get("comment_count"),
                    duration=video_data.get("duration"),
                    duration_seconds=video_data.get("duration_seconds"),
                    thumbnail_url=video_data.get("thumbnail"),
                    url=video_data["url"],
                    status=VideoProcessingStatus.COLLECTED,
                    collected_at=datetime.utcnow(),
                    raw_metadata=video_data,
                )
                videos.append(video)

        logger.info(f"Collected {len(videos)} videos from channel {channel_id} in window {window.date_str}")
        return videos

    # (Removed _parse_datetime from here)


