"""Client for transcript.io API integration."""

import asyncio
import httpx
from typing import Optional, Dict, Any
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
    """Client for interacting with transcript.io API."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.youtube-transcript.io/v1"):
        """Initialize client with API credentials.
        
        Args:
            api_key: Basic auth API key (should include 'Basic ' prefix)
            base_url: Base URL for the API
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.timeout = 30.0  # seconds
        
        # Ensure API key has proper Basic auth format
        if not self.api_key.startswith('Basic '):
            self.api_key = f"Basic {self.api_key}"
    
    async def get_transcript(self, video_id: str, language: str = "en") -> Dict[str, Any]:
        """Get transcript for a YouTube video.
        
        Args:
            video_id: YouTube video ID (without URL)
            language: Language code for transcript (default: 'en')
            
        Returns:
            Dict containing transcript data
            
        Raises:
            TranscriptNotFoundError: If transcript is not available
            TranscriptApiError: If API returns an error
            TranscriptIoError: For other API-related issues
        """
        url = f"{self.base_url}/transcript"
        
        params = {
            "video_id": video_id,
            "lang": language,
            "format": "text"  # We want plain text format
        }
        
        headers = {
            "Authorization": self.api_key,
            "User-Agent": "ltai-news/1.0",
            "Accept": "application/json",
        }
        
        logger.debug(f"Fetching transcript for video {video_id} (language: {language})")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                
                # Handle different response status codes
                if response.status_code == 200:
                    data = response.json()
                    logger.debug(f"Successfully fetched transcript for video {video_id}")
                    return data
                
                elif response.status_code == 404:
                    error_msg = f"No transcript available for video {video_id}"
                    logger.warning(error_msg)
                    raise TranscriptNotFoundError(error_msg)
                
                elif response.status_code == 401:
                    error_msg = "Invalid API key or unauthorized access"
                    logger.error(error_msg)
                    raise TranscriptApiError(error_msg)
                
                elif response.status_code == 429:
                    error_msg = "Rate limit exceeded"
                    logger.warning(error_msg)
                    raise TranscriptApiError(error_msg)
                
                else:
                    error_msg = f"API error {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    raise TranscriptApiError(error_msg)
                    
        except httpx.TimeoutException:
            error_msg = f"Timeout while fetching transcript for video {video_id}"
            logger.error(error_msg)
            raise TranscriptIoError(error_msg)
            
        except httpx.RequestError as e:
            error_msg = f"Request failed for video {video_id}: {str(e)}"
            logger.error(error_msg)
            raise TranscriptIoError(error_msg)
    
    async def get_transcript_text(self, video_id: str, language: str = "en") -> str:
        """Get transcript as plain text string.
        
        Args:
            video_id: YouTube video ID
            language: Language code for transcript
            
        Returns:
            Transcript text as string
            
        Raises:
            TranscriptNotFoundError: If transcript is not available
            TranscriptApiError: If API returns an error  
            TranscriptIoError: For other API-related issues
        """
        try:
            data = await self.get_transcript(video_id, language)
            
            # Extract text from response format
            # The API might return different formats, handle common cases
            if isinstance(data, dict):
                # If response has 'transcript' field
                if 'transcript' in data:
                    transcript_data = data['transcript']
                    if isinstance(transcript_data, str):
                        return transcript_data
                    elif isinstance(transcript_data, list):
                        # If transcript is list of segments, combine text
                        return " ".join(
                            segment.get('text', '') if isinstance(segment, dict) else str(segment)
                            for segment in transcript_data
                        )
                
                # If response has 'text' field
                if 'text' in data:
                    return str(data['text'])
                
                # If response is direct text segments
                if 'segments' in data:
                    segments = data['segments']
                    if isinstance(segments, list):
                        return " ".join(
                            segment.get('text', '') if isinstance(segment, dict) else str(segment)
                            for segment in segments
                        )
                
                # Fallback: convert entire response to string
                logger.warning(f"Unexpected response format for video {video_id}: {type(data)}")
                return str(data)
                
            elif isinstance(data, str):
                return data
                
            else:
                logger.warning(f"Unexpected response type for video {video_id}: {type(data)}")
                return str(data)
                
        except Exception as e:
            logger.error(f"Failed to extract text from transcript response for video {video_id}: {e}")
            raise
    
    async def check_transcript_availability(self, video_id: str, language: str = "en") -> bool:
        """Check if transcript is available for a video without fetching full content.
        
        Args:
            video_id: YouTube video ID
            language: Language code to check
            
        Returns:
            True if transcript is available, False otherwise
        """
        try:
            # Try to get transcript, but catch not found errors
            await self.get_transcript(video_id, language)
            return True
            
        except TranscriptNotFoundError:
            return False
            
        except (TranscriptApiError, TranscriptIoError):
            # For other errors, assume transcript is not available
            # This prevents endless retries for videos with API issues
            return False
    
    def get_client_info(self) -> Dict[str, Any]:
        """Get client configuration information.
        
        Returns:
            Dict with client configuration details
        """
        return {
            "service": "transcript.io",
            "base_url": self.base_url,
            "timeout": self.timeout,
            "has_api_key": bool(self.api_key and len(self.api_key) > 10),
            "api_key_prefix": self.api_key[:20] + "..." if self.api_key else None,
        }