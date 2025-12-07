"""Unit tests for GoogleOAuthClient with mocked API responses."""

from unittest.mock import Mock, patch

import pytest

from app.client.google_oauth import GoogleOAuthClient
from tests.fixtures.youtube_responses import (
    MOCK_CHANNEL_METADATA_RESPONSE,
    MOCK_CHANNEL_SEARCH_RESPONSE,
    MOCK_EMPTY_SEARCH_RESPONSE,
    MOCK_PLAYLIST_ITEMS_RESPONSE,
    MOCK_VIDEO_METADATA_RESPONSE,
)


class TestGoogleOAuthClient:
    """Unit tests for GoogleOAuthClient."""

    @pytest.fixture
    def client(self, mock_credentials_path, mock_token_path):
        """Create a client instance."""
        return GoogleOAuthClient(
            credentials_json_path=mock_credentials_path,
            token_file=mock_token_path,
        )

    @pytest.fixture
    def mock_youtube_service(self):
        """Mock YouTube service."""
        service = Mock()
        return service

    def test_search_channel_found(self, client, mock_youtube_service):
        """Test searching for a channel that exists."""
        client.youtube_service = mock_youtube_service
        mock_youtube_service.search.return_value.list.return_value.execute.return_value = (
            MOCK_CHANNEL_SEARCH_RESPONSE
        )

        result = client.search_channel("Latent Space")

        assert result is not None
        assert result["id"] == "UC_TEST_CHANNEL_ID"
        assert result["title"] == "Latent Space"

    def test_search_channel_not_found(self, client, mock_youtube_service):
        """Test searching for a channel that doesn't exist."""
        client.youtube_service = mock_youtube_service
        mock_youtube_service.search.return_value.list.return_value.execute.return_value = (
            MOCK_EMPTY_SEARCH_RESPONSE
        )

        result = client.search_channel("NonExistent Channel")

        assert result is None

    def test_search_channel_not_authenticated(self, client):
        """Test that search fails when not authenticated."""
        with pytest.raises(RuntimeError, match="Not authenticated"):
            client.search_channel("Test Channel")

    def test_get_channel_metadata_complete(self, client, mock_youtube_service):
        """Test getting complete channel metadata."""
        client.youtube_service = mock_youtube_service
        mock_youtube_service.channels.return_value.list.return_value.execute.return_value = (
            MOCK_CHANNEL_METADATA_RESPONSE
        )

        result = client.get_channel_metadata("UC_TEST_CHANNEL_ID")

        assert result is not None
        assert result["id"] == "UC_TEST_CHANNEL_ID"
        assert result["title"] == "Latent Space"
        assert result["subscriber_count"] == 35600
        assert result["video_count"] == 716
        assert result["view_count"] == 5000000
        assert result["custom_url"] == "@LatentSpacePod"
        assert result["uploads_playlist_id"] == "UU_TEST_UPLOADS_PLAYLIST_ID"

    def test_get_channel_metadata_not_found(self, client, mock_youtube_service):
        """Test getting metadata for non-existent channel."""
        client.youtube_service = mock_youtube_service
        mock_youtube_service.channels.return_value.list.return_value.execute.return_value = {
            "items": []
        }

        result = client.get_channel_metadata("INVALID_ID")

        assert result is None

    def test_get_video_metadata_complete(self, client, mock_youtube_service):
        """Test getting complete video metadata."""
        client.youtube_service = mock_youtube_service
        mock_youtube_service.videos.return_value.list.return_value.execute.return_value = (
            MOCK_VIDEO_METADATA_RESPONSE
        )

        result = client.get_video_metadata("TEST_VIDEO_ID")

        assert result is not None
        assert result["id"] == "TEST_VIDEO_ID"
        assert result["title"] == "Test Video Title"
        assert result["view_count"] == 1000
        assert result["like_count"] == 50
        assert result["comment_count"] == 10
        assert result["duration"] == "PT10M30S"
        assert result["channel_id"] == "UC_TEST_CHANNEL_ID"
        assert result["channel_title"] == "Latent Space"
        assert "youtube.com/watch" in result["url"]

    def test_get_video_metadata_not_found(self, client, mock_youtube_service):
        """Test getting metadata for non-existent video."""
        client.youtube_service = mock_youtube_service
        mock_youtube_service.videos.return_value.list.return_value.execute.return_value = {
            "items": []
        }

        result = client.get_video_metadata("INVALID_ID")

        assert result is None

    def test_get_recent_videos_not_authenticated(self, client):
        """Test that get_recent_videos fails when not authenticated."""
        with pytest.raises(RuntimeError, match="Not authenticated"):
            client.get_recent_videos("UC_TEST_CHANNEL_ID")

