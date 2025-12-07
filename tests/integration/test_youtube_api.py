"""Integration tests for YouTube API using real API calls."""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from dotenv import load_dotenv

from app.client.google_oauth import GoogleOAuthClient

load_dotenv()

# Get logger for this module
logger = logging.getLogger(__name__)

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def authenticated_client():
    """Create an authenticated client for integration tests."""
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_JSON_PATH")
    if not credentials_path:
        pytest.skip("GOOGLE_CREDENTIALS_JSON_PATH not set")

    # Use .tokens directory for test token
    tokens_dir = Path(".tokens")
    tokens_dir.mkdir(exist_ok=True)
    token_file = tokens_dir / "test_token.json"

    # Validate token file
    if token_file.exists():
        try:
            token_data = json.loads(token_file.read_text())
            # Check if refresh_token exists (required for token refresh)
            if "refresh_token" not in token_data:
                logger.warning(
                    "test_token.json missing refresh_token, will trigger new OAuth flow"
                )
                token_file.unlink()
        except (json.JSONDecodeError, Exception) as e:
            # Invalid JSON or other error, delete and start fresh
            logger.warning(f"Invalid test_token.json ({e}), deleting and starting fresh")
            token_file.unlink()

    client = GoogleOAuthClient(
        credentials_json_path=credentials_path,
        token_file=str(token_file),
    )

    # Authenticate (will trigger OAuth flow if no valid token)
    logger.info("🔐 Authenticating for integration tests...")
    client.authenticate()
    return client


class TestYouTubeAPIIntegration:
    """Integration tests with real YouTube API."""

    # Test channel: Latent Space (@LatentSpacePod)
    TEST_CHANNEL_NAME = "Latent Space"
    TEST_CHANNEL_HANDLE = "@LatentSpacePod"

    def test_search_channel_latent_space(self, authenticated_client):
        """Test searching for Latent Space channel."""
        channel = authenticated_client.search_channel(self.TEST_CHANNEL_NAME)

        # Log API response for debugging
        logger.debug(f"Channel search result: {json.dumps(channel, indent=2)}")

        assert channel is not None
        assert "id" in channel
        assert "title" in channel
        assert "Latent Space" in channel["title"].lower() or "latent" in channel[
            "title"
        ].lower()

        logger.info(f"✓ Found channel: {channel['title']} (ID: {channel['id']})")

    def test_get_channel_metadata_complete(self, authenticated_client):
        """Test getting complete metadata for Latent Space channel."""
        # First search for the channel
        channel = authenticated_client.search_channel(self.TEST_CHANNEL_NAME)
        assert channel is not None

        # Get full metadata
        metadata = authenticated_client.get_channel_metadata(channel["id"])

        assert metadata is not None
        assert metadata["id"] == channel["id"]
        assert metadata["title"] is not None
        assert metadata["subscriber_count"] > 0
        assert metadata["video_count"] > 0
        assert metadata["published_at"] is not None
        assert metadata["thumbnail"] is not None

        # Verify data types
        assert isinstance(metadata["subscriber_count"], int)
        assert isinstance(metadata["video_count"], int)
        assert isinstance(metadata["view_count"], int)

        # Log full metadata for debugging
        logger.debug(
            f"Channel metadata: {json.dumps(metadata, indent=2, default=str)}"
        )

        logger.info(f"✓ Channel: {metadata['title']}")
        logger.info(f"✓ Subscribers: {metadata['subscriber_count']:,}")
        logger.info(f"✓ Videos: {metadata['video_count']:,}")
        logger.info(f"✓ Views: {metadata['view_count']:,}")

    def test_get_recent_videos_date_filtering(self, authenticated_client):
        """Test that recent videos are correctly filtered by date."""
        # Search for channel
        channel = authenticated_client.search_channel(self.TEST_CHANNEL_NAME)
        assert channel is not None

        # Get videos from last 24 hours
        videos_24h = authenticated_client.get_recent_videos(channel["id"], hours=24)

        # Get videos from last 168 hours (1 week)
        videos_168h = authenticated_client.get_recent_videos(channel["id"], hours=168)

        # Videos from last week should be >= videos from last 24h
        assert len(videos_168h) >= len(videos_24h)

        # Verify all videos are within time window
        now = datetime.utcnow()
        for video in videos_24h:
            published_at = datetime.fromisoformat(
                video["published_at"].replace("Z", "+00:00")
            )
            time_diff = (now - published_at.replace(tzinfo=None)).total_seconds() / 3600
            assert time_diff <= 24, f"Video {video['id']} is older than 24 hours"

        logger.info(f"✓ Videos in last 24h: {len(videos_24h)}")
        logger.info(f"✓ Videos in last week: {len(videos_168h)}")

        # Log sample videos for debugging
        if videos_24h and logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"Sample 24h videos: {json.dumps(videos_24h[:3], indent=2, default=str)}"
            )

    def test_get_recent_videos_with_metadata(self, authenticated_client):
        """Test getting recent videos with complete metadata."""
        # Search for channel
        channel = authenticated_client.search_channel(self.TEST_CHANNEL_NAME)
        assert channel is not None

        # Get videos with metadata from last week (more likely to have videos)
        videos = authenticated_client.get_recent_videos_with_metadata(
            channel["id"], hours=168
        )

        if videos:
            # Test first video
            video = videos[0]

            assert "id" in video
            assert "title" in video
            assert "published_at" in video
            assert "view_count" in video
            assert "like_count" in video
            assert "duration" in video
            assert "url" in video
            assert "channel_id" in video
            assert "channel_title" in video

            # Verify data types
            assert isinstance(video["view_count"], int)
            assert isinstance(video["like_count"], int)
            assert isinstance(video["comment_count"], int)

            # Log full video metadata for debugging
            logger.debug(
                f"Video metadata: {json.dumps(video, indent=2, default=str)}"
            )

            logger.info(f"✓ Found {len(videos)} videos with metadata")
            logger.info(f"✓ Sample video: {video['title']}")
            logger.info(f"✓ Views: {video['view_count']:,}")
            logger.info(f"✓ Duration: {video['duration']}")
            logger.info(f"✓ URL: {video['url']}")
        else:
            logger.warning("⚠ No recent videos found (this is OK for testing)")

    def test_get_video_metadata_complete(self, authenticated_client):
        """Test getting complete metadata for a specific video."""
        # Search for channel
        channel = authenticated_client.search_channel(self.TEST_CHANNEL_NAME)
        assert channel is not None

        # Get a recent video
        videos = authenticated_client.get_recent_videos(channel["id"], hours=168)
        if not videos:
            pytest.skip("No recent videos found for testing")

        video_id = videos[0]["id"]
        metadata = authenticated_client.get_video_metadata(video_id)

        assert metadata is not None
        assert metadata["id"] == video_id
        assert metadata["title"] is not None
        assert metadata["description"] is not None
        assert metadata["published_at"] is not None
        assert metadata["thumbnail"] is not None
        assert metadata["channel_id"] == channel["id"]
        assert metadata["url"] == f"https://www.youtube.com/watch?v={video_id}"

        # Log full video metadata for debugging
        logger.debug(
            f"Video metadata: {json.dumps(metadata, indent=2, default=str)}"
        )

        logger.info(f"✓ Video: {metadata['title']}")
        logger.info(f"✓ Published: {metadata['published_at']}")
        logger.info(f"✓ Views: {metadata['view_count']:,}")
        logger.info(f"✓ Likes: {metadata['like_count']:,}")

