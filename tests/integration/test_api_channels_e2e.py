"""End-to-end tests for channel tracking API endpoints."""

import os
import logging
from pathlib import Path

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from app.main import app

load_dotenv()

logger = logging.getLogger(__name__)

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(scope="module")
def requires_auth():
    """Skip tests if credentials are not configured."""
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_JSON_PATH")
    if not credentials_path:
        pytest.skip("GOOGLE_CREDENTIALS_JSON_PATH not set")


class TestChannelsAPI:
    """End-to-end tests for /api/channels endpoints."""

    def test_list_tracked_channels(self, client):
        """Test GET /api/channels/list endpoint."""
        response = client.get("/api/channels/list")

        assert response.status_code == 200
        data = response.json()
        assert "channels" in data
        assert "lookback_hours" in data
        assert isinstance(data["channels"], list)
        assert isinstance(data["lookback_hours"], int)

    def test_resolve_channel_success(self, client, requires_auth):
        """Test POST /api/channels/resolve/{channel_name} with valid channel."""
        response = client.post("/api/channels/resolve/Latent Space")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "name" in data
        assert data["id"] is not None
        assert data["name"] is not None

    def test_resolve_channel_not_found(self, client, requires_auth):
        """Test POST /api/channels/resolve/{channel_name} with invalid channel."""
        response = client.post("/api/channels/resolve/ThisChannelDefinitelyDoesNotExist12345")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_sync_channels(self, client, requires_auth):
        """Test POST /api/channels/sync endpoint."""
        response = client.post("/api/channels/sync")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "channels_processed" in data
        assert "channels_found" in data
        assert "channels_not_found" in data
        assert "total_videos_collected" in data
        assert "lookback_hours" in data
        assert "sync_results" in data
        assert "started_at" in data
        assert "completed_at" in data

        # Verify types
        assert isinstance(data["channels_processed"], int)
        assert isinstance(data["channels_found"], int)
        assert isinstance(data["channels_not_found"], list)
        assert isinstance(data["total_videos_collected"], int)
        assert isinstance(data["sync_results"], list)

        # Verify sync results structure
        if data["sync_results"]:
            sync_result = data["sync_results"][0]
            assert "channel" in sync_result
            assert "videos_collected" in sync_result
            assert "videos_count" in sync_result
            assert "sync_started_at" in sync_result
            assert "sync_completed_at" in sync_result

            # Verify channel structure
            channel = sync_result["channel"]
            assert "id" in channel
            assert "name" in channel

            # Verify video structure if videos exist
            if sync_result["videos_collected"]:
                video = sync_result["videos_collected"][0]
                assert "id" in video
                assert "channel_id" in video
                assert "title" in video
                assert "status" in video
                assert video["status"] == "collected"

    def test_sync_channels_error_handling(self, client):
        """Test that sync endpoint handles errors gracefully."""
        # This test might fail if credentials are invalid
        # but should return 500, not crash
        response = client.post("/api/channels/sync")

        # Should either succeed (200) or fail gracefully (500)
        assert response.status_code in [200, 500]

        if response.status_code == 500:
            data = response.json()
            assert "detail" in data

    def test_api_root(self, client):
        """Test root endpoint still works."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "LTAI News"
        assert data["status"] == "running"

