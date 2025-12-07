"""Unit tests for ChannelTracker service."""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from app.models.channel import Channel, ChannelSyncResult, ChannelTrackerResult
from app.models.video import Video, VideoProcessingStatus
from app.services.channel_tracker import ChannelTracker
from tests.fixtures.youtube_responses import (
    MOCK_CHANNEL_METADATA_RESPONSE,
    MOCK_CHANNEL_SEARCH_RESPONSE,
    MOCK_RECENT_VIDEOS_RESPONSE,
)


class TestChannelTracker:
    """Unit tests for ChannelTracker service."""

    @pytest.fixture
    def mock_youtube_client(self):
        """Create a mock YouTube client."""
        client = Mock()
        client.youtube_service = Mock()
        return client

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.tracked_channels = ["Latent Space", "@TestChannel"]
        settings.content_lookback_hours = 24
        settings.google_credentials_json_path = "/path/to/creds.json"
        settings.google_token_file = "/path/to/token.json"
        return settings

    @pytest.fixture
    def tracker(self, mock_youtube_client, mock_settings):
        """Create a ChannelTracker instance with mocked dependencies."""
        with patch("app.services.channel_tracker.get_settings", return_value=mock_settings):
            with patch(
                "app.services.channel_tracker.GoogleOAuthClient",
                return_value=mock_youtube_client,
            ):
                tracker = ChannelTracker()
                tracker.youtube_client = mock_youtube_client
                return tracker

    def test_get_tracked_channels(self, tracker, mock_settings):
        """Test getting tracked channels from config."""
        channels = tracker.get_tracked_channels()
        assert channels == ["Latent Space", "@TestChannel"]

    def test_search_and_resolve_channel_success(self, tracker, mock_youtube_client):
        """Test successfully resolving a channel."""
        # Mock search_channel
        mock_youtube_client.search_channel.return_value = {
            "id": "UC_TEST_CHANNEL_ID",
            "title": "Latent Space",
        }

        # Mock get_channel_metadata
        mock_youtube_client.get_channel_metadata.return_value = {
            "id": "UC_TEST_CHANNEL_ID",
            "title": "Latent Space",
            "custom_url": "@LatentSpacePod",
            "description": "Test description",
            "thumbnail": "https://example.com/thumb.jpg",
            "published_at": "2020-01-01T00:00:00Z",
            "subscriber_count": 10000,
            "video_count": 100,
            "view_count": 1000000,
            "uploads_playlist_id": "UU_TEST",
        }

        channel = tracker.search_and_resolve_channel("Latent Space")

        assert channel is not None
        assert channel.id == "UC_TEST_CHANNEL_ID"
        assert channel.name == "Latent Space"
        assert channel.handle == "@LatentSpacePod"
        assert channel.subscriber_count == 10000

    def test_search_and_resolve_channel_not_found(self, tracker, mock_youtube_client):
        """Test resolving a channel that doesn't exist."""
        mock_youtube_client.search_channel.return_value = None

        channel = tracker.search_and_resolve_channel("NonExistent Channel")

        assert channel is None

    def test_search_and_resolve_channel_metadata_fail(self, tracker, mock_youtube_client):
        """Test resolving a channel when metadata fetch fails."""
        mock_youtube_client.search_channel.return_value = {
            "id": "UC_TEST_CHANNEL_ID",
            "title": "Latent Space",
        }
        mock_youtube_client.get_channel_metadata.return_value = None

        channel = tracker.search_and_resolve_channel("Latent Space")

        assert channel is None

    def test_fetch_recent_videos(self, tracker, mock_youtube_client):
        """Test fetching recent videos from a channel."""
        mock_youtube_client.get_recent_videos_with_metadata.return_value = (
            MOCK_RECENT_VIDEOS_RESPONSE
        )

        videos = tracker.fetch_recent_videos("UC_TEST", hours=24)

        assert len(videos) == 2
        assert videos[0].id == "VIDEO_ID_1"
        assert videos[0].status == VideoProcessingStatus.COLLECTED
        assert videos[1].id == "VIDEO_ID_2"

    def test_fetch_recent_videos_empty(self, tracker, mock_youtube_client):
        """Test fetching videos when none are found."""
        mock_youtube_client.get_recent_videos_with_metadata.return_value = []

        videos = tracker.fetch_recent_videos("UC_TEST", hours=24)

        assert len(videos) == 0

    def test_sync_channel_success(self, tracker, mock_youtube_client):
        """Test successfully syncing a channel."""
        # Mock search and resolve
        mock_youtube_client.search_channel.return_value = {
            "id": "UC_TEST",
            "title": "Test Channel",
        }
        mock_youtube_client.get_channel_metadata.return_value = {
            "id": "UC_TEST",
            "title": "Test Channel",
            "custom_url": "@testchannel",
            "subscriber_count": 10000,
            "video_count": 100,
            "view_count": 1000000,
            "uploads_playlist_id": "UU_TEST",
        }

        # Mock video fetching
        mock_youtube_client.get_recent_videos_with_metadata.return_value = [
            {
                "id": "video1",
                "channel_id": "UC_TEST",
                "title": "Video 1",
                "published_at": "2024-01-15T10:00:00Z",
                "url": "https://youtube.com/watch?v=video1",
            }
        ]

        result = tracker.sync_channel("Test Channel")

        assert result.error is None
        assert result.channel.id == "UC_TEST"
        assert len(result.videos_collected) == 1
        assert result.videos_count == 1
        assert isinstance(result.duration_seconds, float)

    def test_sync_channel_not_found(self, tracker, mock_youtube_client):
        """Test syncing a channel that doesn't exist."""
        mock_youtube_client.search_channel.return_value = None

        result = tracker.sync_channel("NonExistent Channel")

        assert result.error is not None
        assert result.channel.id == ""
        assert len(result.videos_collected) == 0

    def test_sync_channel_exception(self, tracker, mock_youtube_client):
        """Test syncing a channel when an exception occurs."""
        mock_youtube_client.search_channel.side_effect = Exception("API Error")

        result = tracker.sync_channel("Test Channel")

        assert result.error is not None
        assert "API Error" in result.error

    def test_sync_all_channels_success(self, tracker, mock_youtube_client):
        """Test syncing all channels successfully."""
        # Mock search and resolve
        mock_youtube_client.search_channel.return_value = {
            "id": "UC_TEST",
            "title": "Test Channel",
        }
        mock_youtube_client.get_channel_metadata.return_value = {
            "id": "UC_TEST",
            "title": "Test Channel",
            "subscriber_count": 10000,
            "video_count": 100,
            "view_count": 1000000,
            "uploads_playlist_id": "UU_TEST",
        }

        # Mock video fetching
        mock_youtube_client.get_recent_videos_with_metadata.return_value = [
            {
                "id": "video1",
                "channel_id": "UC_TEST",
                "title": "Video 1",
                "published_at": "2024-01-15T10:00:00Z",
                "url": "https://youtube.com/watch?v=video1",
            }
        ]

        result = tracker.sync_all_channels()

        assert result.channels_processed == 2  # From mock_settings
        assert result.channels_found == 2
        assert result.total_videos_collected == 2  # 1 video per channel

    def test_sync_all_channels_partial_failure(self, tracker, mock_youtube_client):
        """Test syncing all channels with some failures."""
        # First channel succeeds, second fails
        def mock_search_side_effect(channel_name):
            if channel_name == "Latent Space":
                return {"id": "UC_TEST1", "title": "Latent Space"}
            return None

        mock_youtube_client.search_channel.side_effect = mock_search_side_effect
        mock_youtube_client.get_channel_metadata.return_value = {
            "id": "UC_TEST1",
            "title": "Latent Space",
            "subscriber_count": 10000,
            "video_count": 100,
            "view_count": 1000000,
            "uploads_playlist_id": "UU_TEST1",
        }
        mock_youtube_client.get_recent_videos_with_metadata.return_value = []

        result = tracker.sync_all_channels()

        assert result.channels_processed == 2
        assert result.channels_found == 1
        assert len(result.channels_not_found) == 1

    def test_sync_all_channels_empty_config(self, tracker, mock_settings):
        """Test syncing when no channels are configured."""
        mock_settings.tracked_channels = []

        result = tracker.sync_all_channels()

        assert result.channels_processed == 0
        assert result.total_videos_collected == 0

    def test_parse_datetime_valid(self, tracker):
        """Test parsing valid datetime strings."""
        dt_str = "2024-01-15T10:00:00Z"
        dt = tracker._parse_datetime(dt_str)

        assert dt is not None
        assert isinstance(dt, datetime)

    def test_parse_datetime_without_z(self, tracker):
        """Test parsing datetime without Z suffix."""
        dt_str = "2024-01-15T10:00:00+00:00"
        dt = tracker._parse_datetime(dt_str)

        assert dt is not None
        assert isinstance(dt, datetime)

    def test_parse_datetime_none(self, tracker):
        """Test parsing None datetime."""
        dt = tracker._parse_datetime(None)
        assert dt is None

    def test_parse_datetime_invalid(self, tracker):
        """Test parsing invalid datetime string."""
        dt = tracker._parse_datetime("invalid-date")
        assert dt is None

