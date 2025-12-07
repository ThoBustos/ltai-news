"""Mock YouTube API responses for unit testing."""

# Mock channel search response
MOCK_CHANNEL_SEARCH_RESPONSE = {
    "items": [
        {
            "id": {"channelId": "UC_TEST_CHANNEL_ID"},
            "snippet": {
                "title": "Latent Space",
                "description": "The first place where 90,000+ AI Engineers gather...",
                "publishedAt": "2020-01-01T00:00:00Z",
                "thumbnails": {
                    "high": {"url": "https://example.com/thumbnail.jpg"}
                },
                "customUrl": "@LatentSpacePod",
            },
        }
    ]
}

# Mock empty search response
MOCK_EMPTY_SEARCH_RESPONSE = {"items": []}

# Mock channel metadata response
MOCK_CHANNEL_METADATA_RESPONSE = {
    "items": [
        {
            "id": "UC_TEST_CHANNEL_ID",
            "snippet": {
                "title": "Latent Space",
                "description": "The first place where 90,000+ AI Engineers gather...",
                "publishedAt": "2020-01-01T00:00:00Z",
                "thumbnails": {
                    "high": {"url": "https://example.com/thumbnail.jpg"}
                },
                "customUrl": "@LatentSpacePod",
            },
            "statistics": {
                "subscriberCount": "35600",
                "videoCount": "716",
                "viewCount": "5000000",
            },
            "contentDetails": {
                "relatedPlaylists": {
                    "uploads": "UU_TEST_UPLOADS_PLAYLIST_ID"
                }
            },
        }
    ]
}

# Mock video metadata response
MOCK_VIDEO_METADATA_RESPONSE = {
    "items": [
        {
            "id": "TEST_VIDEO_ID",
            "snippet": {
                "title": "Test Video Title",
                "description": "Test video description",
                "publishedAt": "2024-01-15T10:00:00Z",
                "thumbnails": {
                    "high": {"url": "https://example.com/video_thumbnail.jpg"}
                },
                "channelId": "UC_TEST_CHANNEL_ID",
                "channelTitle": "Latent Space",
            },
            "statistics": {
                "viewCount": "1000",
                "likeCount": "50",
                "commentCount": "10",
            },
            "contentDetails": {
                "duration": "PT10M30S",  # 10 minutes 30 seconds
            },
        }
    ]
}

# Mock playlist items response (recent videos)
MOCK_PLAYLIST_ITEMS_RESPONSE = {
    "items": [
        {
            "snippet": {
                "publishedAt": "2024-01-15T10:00:00Z",
                "title": "Recent Video 1",
                "resourceId": {"videoId": "VIDEO_ID_1"},
            }
        },
        {
            "snippet": {
                "publishedAt": "2024-01-14T15:00:00Z",
                "title": "Recent Video 2",
                "resourceId": {"videoId": "VIDEO_ID_2"},
            }
        },
    ]
}

