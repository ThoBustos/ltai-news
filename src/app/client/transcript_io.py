"""Client for transcript.io API integration."""

import asyncio
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from app.core.logging import logger


class TranscriptIoError(Exception):
    """Base exception for transcript.io API errors."""
    pass


class TranscriptNotFoundError(TranscriptIoError):
    """Raised when transcript is not available for a video."""
    pass


class TranscriptApiError(TranscriptIoError):
    """Raised when API returns an error response."""
    pass


class TranscriptIoClient:
    """Client for interacting with transcript.io API using the POST /api/transcripts endpoint."""
    
    def __init__(self, api_key: str, base_url: str = "https://www.youtube-transcript.io/api"):
        """Initialize client with API credentials.
        
        Args:
            api_key: Basic auth API key (should include 'Basic ' prefix)
            base_url: Base URL for the API (defaults to the latest documented one)
        """
        self.api_key = api_key
        
        # Ensure base_url has /api if it's just the domain
        base_url = base_url.rstrip('/')
        if not base_url.endswith('/api'):
            logger.debug(f"Appending /api to base_url: {base_url}")
            base_url = f"{base_url}/api"
            
        self.base_url = base_url
        self.timeout = 180.0  # 3 minutes for long-form content (podcasts, interviews)
        
        # Ensure API key has proper Basic auth format
        if not self.api_key.startswith('Basic '):
            self.api_key = f"Basic {self.api_key}"
    
    async def get_transcripts_batch(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch transcripts for a list of YouTube video IDs using POST /api/transcripts.
        
        Args:
            video_ids: List of YouTube video IDs (max 50 per request)
            
        Returns:
            List of dicts containing transcript data for each video
            
        Raises:
            TranscriptApiError: If API returns an error
            TranscriptIoError: For other API-related issues
        """
        if not video_ids:
            return []
            
        if len(video_ids) > 50:
            logger.warning(f"Batch size {len(video_ids)} exceeds API limit of 50. Only first 50 will be processed.")
            video_ids = video_ids[:50]

        url = f"{self.base_url}/transcripts"
        
        payload = {
            "ids": video_ids
        }
        
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "ltai-news/1.1",
            "Accept": "application/json",
        }
        
        logger.debug(f"Fetching transcripts for {len(video_ids)} videos via POST")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    # The documentation doesn't specify the exact response structure for /api/transcripts
                    # but typically it's a list or a map of ID -> transcript.
                    # Based on the singular behavior, we expect a list of results.
                    logger.debug(f"Successfully fetched {len(video_ids)} transcripts")
                    return data if isinstance(data, list) else [data]
                
                elif response.status_code == 401:
                    error_msg = "Invalid API key or unauthorized access"
                    logger.error(error_msg)
                    raise TranscriptApiError(error_msg)
                
                elif response.status_code == 429:
                    error_msg = "Rate limit exceeded (5 requests per 10 seconds)"
                    logger.warning(error_msg)
                    raise TranscriptApiError(error_msg)
                
                else:
                    error_msg = f"API error {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    raise TranscriptApiError(error_msg)
                    
        except httpx.TimeoutException:
            error_msg = f"Timeout while fetching transcripts for batch of {len(video_ids)}"
            logger.error(error_msg)
            raise TranscriptIoError(error_msg)
            
        except httpx.RequestError as e:
            error_msg = f"Request failed for batch: {str(e)}"
            logger.error(error_msg)
            raise TranscriptIoError(error_msg)

    async def get_transcript_text(self, video_id: str, language_code: str = "en") -> str:
        """
        Legacy-compatible method to get a single transcript text.
        Uses the new batch POST method under the hood for a single ID.
        
        Args:
            video_id: YouTube video ID
            language_code: Language code (default: 'en')
            
        Returns:
            Transcript text as string
            
        Raises:
            TranscriptNotFoundError: If transcript is not available
            TranscriptApiError: If API returns an error  
            TranscriptIoError: For other API-related issues
        """
        try:
            results = await self.get_transcripts_batch([video_id])
            
            if not results:
                raise TranscriptNotFoundError(f"No results returned for video {video_id}")
            
            # Find the result for this specific ID
            result = results[0]
            
            if isinstance(result, dict):
                # Check for error in the specific video result if applicable
                if result.get("status") == "error" or "error" in result:
                    error_msg = result.get("error", "Unknown error for video")
                    if "not found" in error_msg.lower():
                        raise TranscriptNotFoundError(f"Transcript not found for {video_id}")
                    raise TranscriptApiError(error_msg)

                # 1. Check for 'text' field which contains the full joined transcript (observed in raw response)
                if result.get("text"):
                    logger.debug(f"Found transcript in 'text' field for {video_id}")
                    return str(result["text"])

                # 2. Check for 'tracks[0].transcript' structure (from user's n8n code)
                tracks = result.get("tracks")
                if isinstance(tracks, list) and len(tracks) > 0:
                    track = tracks[0]
                    if isinstance(track, dict) and "transcript" in track:
                        segments = track["transcript"]
                        if isinstance(segments, list):
                            logger.debug(f"Found transcript in tracks[0]['transcript'] for {video_id}")
                            return " ".join(s.get("text", str(s)) if isinstance(s, dict) else str(s) for s in segments)

                # 3. Extract text from other possible fields
                for field in ['transcript', 'content']:
                    val = result.get(field)
                    if val:
                        logger.debug(f"Found transcript in field '{field}' for {video_id}")
                        if isinstance(val, list):
                            return " ".join(s.get('text', str(s)) if isinstance(s, dict) else str(s) for s in val)
                        return str(val)
                
                # If no text found but response exists
                logger.warning(f"Result returned for {video_id} but no text found in fields: {result.keys()}")
                return str(result)
            
            return str(result)
                
        except TranscriptNotFoundError:
            raise
        except Exception as e:
            if isinstance(e, (TranscriptApiError, TranscriptIoError)):
                raise
            logger.error(f"Failed to extract text from transcript response for video {video_id}: {e}")
            raise TranscriptIoError(str(e))

    def get_client_info(self) -> Dict[str, Any]:
        """Get client configuration information."""
        return {
            "service": "transcript.io",
            "base_url": self.base_url,
            "api_type": "POST /api/transcripts",
            "has_api_key": bool(self.api_key and len(self.api_key) > 10),
        }
