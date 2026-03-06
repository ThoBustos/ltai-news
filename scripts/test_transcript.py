import asyncio
import os
import sys
from pathlib import Path

# Add src to python path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from app.services.transcript_service import TranscriptService
from app.models.video import Video
from app.core.logging import logger
from datetime import datetime, timezone


async def test_transcript():
    print("Testing Transcript Service...")
    service = TranscriptService()
    
    if not service.is_available():
        print("WARNING: Transcript service is in simulation mode (no API key).")
    
    # Use a known video ID
    video_id = "jsnrg1zkz7E" 
    video = Video(
        id=video_id,
        channel_id="UCCRxYlYOmLE2l5wxs3ckJtg",
        title="Test Video",
        url=f"https://www.youtube.com/watch?v={video_id}",
        published_at=datetime.now(timezone.utc), # Fix: Use a real datetime
    )
    
    print(f"Extracting transcript for {video_id}...")
    result = await service.extract_transcript(video)
    
    if result.success:
        print(f"SUCCESS: Extracted {len(result.transcript)} characters.")
        print(f"Preview: {result.transcript[:200]}...")
    else:
        print(f"FAILED: {result.error}")

if __name__ == "__main__":
    asyncio.run(test_transcript())




