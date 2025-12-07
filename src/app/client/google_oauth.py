"""Simple Google OAuth client for YouTube API."""

import os
from pathlib import Path
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app.core.logging import logger

# YouTube API scope
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]


class GoogleOAuthClient:
    """Simple Google OAuth client for YouTube API."""

    def __init__(
        self, credentials_json_path: str, token_file: Optional[str] = None
    ):
        """
        Initialize OAuth client.

        Args:
            credentials_json_path: Path to OAuth2 credentials JSON file
            token_file: Path to store/load token (defaults to .tokens/token.json or GOOGLE_TOKEN_FILE env var)
        """
        self.credentials_json_path = Path(credentials_json_path)

        # Default token location: .tokens/token.json or from env
        if token_file is None:
            token_file = os.getenv("GOOGLE_TOKEN_FILE", ".tokens/token.json")

        self.token_file = Path(token_file)
        # Ensure token directory exists
        self.token_file.parent.mkdir(parents=True, exist_ok=True)

        self.credentials: Optional[Credentials] = None
        self.youtube_service = None

    def authenticate(self) -> None:
        """Authenticate and build YouTube service."""
        creds = self._get_credentials()
        self.credentials = creds
        self.youtube_service = build("youtube", "v3", credentials=creds)
        logger.info("Authenticated with YouTube API")

    def _get_credentials(self) -> Credentials:
        """Get valid credentials from storage or OAuth flow."""
        creds = None

        # Try to load existing token
        if self.token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)
            except (ValueError, KeyError) as e:
                # Token file is invalid or malformed, delete it and start fresh
                logger.warning(f"Invalid token file: {e}. Starting fresh OAuth flow...")
                self.token_file.unlink()
                creds = None

        # If no valid credentials, do OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired token...")
                creds.refresh(Request())
            else:
                logger.info("Starting OAuth flow...")
                if not self.credentials_json_path.exists():
                    raise FileNotFoundError(
                        f"Credentials file not found: {self.credentials_json_path}"
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_json_path), SCOPES
                )
                creds = flow.run_local_server(port=8080, open_browser=True)

            # Save token
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_file, "w") as token:
                token.write(creds.to_json())
            logger.info(f"Token saved to {self.token_file}")

        return creds

    def search_channel(self, channel_name: str) -> Optional[dict]:
        """Search for a channel by name."""
        if not self.youtube_service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        logger.debug(f"Searching for channel: {channel_name}")
        request = self.youtube_service.search().list(
            part="snippet",
            q=channel_name,
            type="channel",
            maxResults=1,
        )
        response = request.execute()

        if not response.get("items"):
            logger.debug(f"No channel found for: {channel_name}")
            return None

        item = response["items"][0]
        channel_id = item["id"]["channelId"]
        logger.debug(f"Found channel: {channel_id} - {item['snippet']['title']}")
        return {
            "id": channel_id,
            "title": item["snippet"]["title"],
        }

    def get_channel_metadata(self, channel_id: str) -> Optional[dict]:
        """
        Get complete metadata for a channel.

        Args:
            channel_id: YouTube channel ID

        Returns:
            Channel metadata dict with all available fields
        """
        if not self.youtube_service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        logger.debug(f"Getting metadata for channel: {channel_id}")
        try:
            request = self.youtube_service.channels().list(
                part="snippet,statistics,contentDetails",
                id=channel_id,
            )
            response = request.execute()

            if not response.get("items"):
                logger.warning(f"No channel found with ID: {channel_id}")
                return None

            channel = response["items"][0]
            snippet = channel.get("snippet", {})
            statistics = channel.get("statistics", {})
            content_details = channel.get("contentDetails", {})

            metadata = {
                "id": channel["id"],
                "title": snippet.get("title"),
                "description": snippet.get("description"),
                "published_at": snippet.get("publishedAt"),
                "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                "custom_url": snippet.get("customUrl"),
                "subscriber_count": int(statistics.get("subscriberCount", 0)),
                "video_count": int(statistics.get("videoCount", 0)),
                "view_count": int(statistics.get("viewCount", 0)),
                "uploads_playlist_id": content_details.get("relatedPlaylists", {}).get(
                    "uploads"
                ),
            }
            logger.debug(f"Retrieved metadata for channel: {metadata['title']} ({channel_id})")
            return metadata
        except Exception as e:
            logger.error(f"Error getting channel metadata: {e}", exc_info=True)
            return None

    def get_video_metadata(self, video_id: str) -> Optional[dict]:
        """
        Get complete metadata for a video.

        Args:
            video_id: YouTube video ID

        Returns:
            Video metadata dict with all available fields
        """
        if not self.youtube_service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        logger.debug(f"Getting metadata for video: {video_id}")
        try:
            request = self.youtube_service.videos().list(
                part="snippet,statistics,contentDetails",
                id=video_id,
            )
            response = request.execute()

            if not response.get("items"):
                logger.warning(f"No video found with ID: {video_id}")
                return None

            video = response["items"][0]
            snippet = video.get("snippet", {})
            statistics = video.get("statistics", {})
            content_details = video.get("contentDetails", {})

            metadata = {
                "id": video["id"],
                "title": snippet.get("title"),
                "description": snippet.get("description"),
                "published_at": snippet.get("publishedAt"),
                "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                "channel_id": snippet.get("channelId"),
                "channel_title": snippet.get("channelTitle"),
                "duration": content_details.get("duration"),
                "view_count": int(statistics.get("viewCount", 0)),
                "like_count": int(statistics.get("likeCount", 0)),
                "comment_count": int(statistics.get("commentCount", 0)),
                "url": f"https://www.youtube.com/watch?v={video['id']}",
            }
            logger.debug(f"Retrieved metadata for video: {metadata['title']} ({video_id})")
            return metadata
        except Exception as e:
            logger.error(f"Error getting video metadata: {e}", exc_info=True)
            return None

    def get_recent_videos(self, channel_id: str, hours: int = 24) -> list[dict]:
        """Get videos published in the last N hours."""
        if not self.youtube_service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        logger.debug(f"Getting recent videos for channel {channel_id} (last {hours} hours)")
        from datetime import datetime, timedelta

        # Get uploads playlist
        channel_request = self.youtube_service.channels().list(
            part="contentDetails", id=channel_id
        )
        channel_response = channel_request.execute()

        if not channel_response.get("items"):
            logger.warning(f"No channel found with ID: {channel_id}")
            return []

        uploads_playlist_id = channel_response["items"][0]["contentDetails"][
            "relatedPlaylists"
        ]["uploads"]

        # Get videos
        published_after = datetime.utcnow() - timedelta(hours=hours)
        videos = []

        request = self.youtube_service.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=50,
        )
        response = request.execute()

        for item in response.get("items", []):
            published_at = datetime.fromisoformat(
                item["snippet"]["publishedAt"].replace("Z", "+00:00")
            )
            if published_at.replace(tzinfo=None) >= published_after:
                videos.append(
                    {
                        "id": item["snippet"]["resourceId"]["videoId"],
                        "title": item["snippet"]["title"],
                        "published_at": item["snippet"]["publishedAt"],
                    }
                )

        logger.info(f"Found {len(videos)} recent videos for channel {channel_id}")
        return videos

    def get_recent_videos_with_metadata(
        self, channel_id: str, hours: int = 24
    ) -> list[dict]:
        """
        Get videos published in the last N hours with full metadata.

        Args:
            channel_id: YouTube channel ID
            hours: Number of hours to look back

        Returns:
            List of video dicts with complete metadata
        """
        logger.debug(f"Getting recent videos with metadata for channel {channel_id} (last {hours} hours)")
        video_ids = [v["id"] for v in self.get_recent_videos(channel_id, hours)]
        if not video_ids:
            logger.debug(f"No recent videos found for channel {channel_id}")
            return []

        # Get full metadata for all videos
        videos_with_metadata = []
        for video_id in video_ids:
            metadata = self.get_video_metadata(video_id)
            if metadata:
                videos_with_metadata.append(metadata)

        logger.info(f"Retrieved metadata for {len(videos_with_metadata)} videos")
        return videos_with_metadata

