"""Integration tests for ChannelTracker using real YouTube API."""

import os
import logging
from pathlib import Path

import pytest
from dotenv import load_dotenv

from app.services.channel_tracker import ChannelTracker

load_dotenv()

logger = logging.getLogger(__name__)

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def authenticated_tracker():
    """Create an authenticated ChannelTracker for integration tests."""
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_JSON_PATH")
    if not credentials_path:
        pytest.skip("GOOGLE_CREDENTIALS_JSON_PATH not set")

    # Use .tokens directory for test token
    tokens_dir = Path(".tokens")
    tokens_dir.mkdir(exist_ok=True)
    token_file = tokens_dir / "test_token.json"

    tracker = ChannelTracker(
        credentials_json_path=credentials_path,
        token_file=str(token_file),
    )

    return tracker


class TestChannelTrackerIntegration:
    """Integration tests with real YouTube API."""

    TEST_CHANNEL_NAME = "Latent Space"

    def test_search_and_resolve_channel(self, authenticated_tracker):
        """Test resolving a real channel."""
        channel = authenticated_tracker.search_and_resolve_channel(self.TEST_CHANNEL_NAME)

        assert channel is not None
        assert channel.id is not None
        assert channel.name is not None
        assert "latent" in channel.name.lower() or "latent" in (channel.handle or "").lower()
        assert channel.subscriber_count is not None
        assert channel.subscriber_count > 0

        logger.info(f"✓ Resolved channel: {channel.name} ({channel.id})")

    def test_fetch_recent_videos(self, authenticated_tracker):
        """Test fetching recent videos from a real channel."""
        # First resolve the channel
        channel = authenticated_tracker.search_and_resolve_channel(self.TEST_CHANNEL_NAME)
        assert channel is not None

        # Fetch videos from last week (more likely to have videos)
        videos = authenticated_tracker.fetch_recent_videos(channel.id, hours=168)

        # Should return a list (may be empty)
        assert isinstance(videos, list)

        if videos:
            # Verify video structure
            video = videos[0]
            assert video.id is not None
            assert video.channel_id == channel.id
            assert video.title is not None
            assert video.published_at is not None
            assert video.status.value == "collected"
            assert video.url is not None

            logger.info(f"✓ Found {len(videos)} videos")
            logger.info(f"✓ Sample video: {video.title}")

    def test_sync_channel(self, authenticated_tracker):
        """Test syncing a single channel."""
        result = authenticated_tracker.sync_channel(self.TEST_CHANNEL_NAME)

        assert result is not None
        assert result.channel is not None
        assert result.channel.id is not None
        assert result.error is None
        assert isinstance(result.videos_collected, list)
        assert result.videos_count == len(result.videos_collected)
        assert result.duration_seconds > 0

        logger.info(
            f"✓ Synced channel: {result.channel.name} - "
            f"{result.videos_count} videos in {result.duration_seconds:.2f}s"
        )

    def test_sync_channel_not_found(self, authenticated_tracker):
        """Test syncing a non-existent channel."""
        result = authenticated_tracker.sync_channel("ThisChannelDefinitelyDoesNotExist12345")

        assert result is not None
        assert result.error is not None
        assert result.channel.id == ""
        assert result.videos_count == 0

    def test_sync_all_channels_with_test_channel(self, authenticated_tracker):
        """Test syncing all configured channels (if test channel is configured)."""
        # This test depends on TRACKED_CHANNELS env var
        tracked_channels = authenticated_tracker.get_tracked_channels()

        if not tracked_channels:
            pytest.skip("No channels configured in TRACKED_CHANNELS")

        result = authenticated_tracker.sync_all_channels()

        assert result is not None
        assert result.channels_processed == len(tracked_channels)
        assert result.channels_found >= 0
        assert result.channels_found <= result.channels_processed
        assert result.total_videos_collected >= 0
        assert result.duration_seconds > 0

        logger.info(
            f"✓ Processed {result.channels_processed} channels, "
            f"found {result.channels_found}, "
            f"collected {result.total_videos_collected} videos"
        )

