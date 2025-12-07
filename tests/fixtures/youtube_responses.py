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

# Mock recent videos response (for get_recent_videos_with_metadata)
MOCK_RECENT_VIDEOS_RESPONSE = [
    {
        "id": "VIDEO_ID_1",
        "channel_id": "UC_TEST_CHANNEL_ID",
        "title": "Recent Video 1",
        "description": "Description of recent video 1",
        "published_at": "2024-01-15T10:00:00Z",
        "thumbnail": "https://example.com/video1_thumb.jpg",
        "view_count": 1000,
        "like_count": 50,
        "comment_count": 10,
        "duration": "PT10M30S",
        "url": "https://www.youtube.com/watch?v=VIDEO_ID_1",
        "channel_title": "Latent Space",
    },
    {
        "id": "VIDEO_ID_2",
        "channel_id": "UC_TEST_CHANNEL_ID",
        "title": "Recent Video 2",
        "description": "Description of recent video 2",
        "published_at": "2024-01-14T15:00:00Z",
        "thumbnail": "https://example.com/video2_thumb.jpg",
        "view_count": 2000,
        "like_count": 100,
        "comment_count": 20,
        "duration": "PT15M45S",
        "url": "https://www.youtube.com/watch?v=VIDEO_ID_2",
        "channel_title": "Latent Space",
    },
]

