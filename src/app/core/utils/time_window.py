"""Time window utilities for date-based processing.

Provides strict UTC time window functions for idempotent pipeline processing.
All windows are 24-hour periods starting at 00:00:00 UTC and ending at 23:59:59 UTC.
"""

from datetime import date, datetime, time, timezone
from typing import Tuple

from pydantic import BaseModel


class TimeWindow(BaseModel):
    """Represents a time window with UTC start and end times."""
    
    start_utc: datetime
    end_utc: datetime
    
    @property
    def duration_seconds(self) -> float:
        """Get duration of window in seconds."""
        return (self.end_utc - self.start_utc).total_seconds()
    
    @property
    def date_str(self) -> str:
        """Get date string in YYYY-MM-DD format."""
        return self.start_utc.date().isoformat()
    
    def contains(self, dt: datetime) -> bool:
        """Check if datetime falls within this window."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return self.start_utc <= dt <= self.end_utc


def get_window(target_date: date) -> TimeWindow:
    """Convert a date to a strict 24h UTC window.
    
    Args:
        target_date: The date to create a window for
        
    Returns:
        TimeWindow from 00:00:00 UTC to 23:59:59.999999 UTC
    """
    start_utc = datetime.combine(
        target_date, 
        time(0, 0, 0), 
        timezone.utc
    )
    end_utc = datetime.combine(
        target_date, 
        time(23, 59, 59, 999999), 
        timezone.utc
    )
    
    return TimeWindow(start_utc=start_utc, end_utc=end_utc)


def get_current_date_window() -> TimeWindow:
    """Get the current date's UTC window.
    
    Returns:
        TimeWindow for today's date in UTC
    """
    today = datetime.now(timezone.utc).date()
    return get_window(today)


def parse_date(date_str: str) -> date:
    """Parse a date string in YYYY-MM-DD format.
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        
    Returns:
        date object
        
    Raises:
        ValueError: If date string is invalid
    """
    try:
        return datetime.fromisoformat(date_str).date()
    except ValueError as e:
        raise ValueError(f"Invalid date format '{date_str}'. Expected YYYY-MM-DD") from e


def get_paris_offset_window(target_hour: int = 8) -> TimeWindow:
    """Get a time window offset for Paris timezone wake-up logic.
    
    This creates a window that accounts for Paris time (UTC+1/UTC+2 depending on DST)
    to target optimal release times when people are waking up.
    
    Args:
        target_hour: Target hour in Paris time (default 8 AM)
        
    Returns:
        TimeWindow adjusted for Paris timezone
    """
    # Get current date in UTC
    today = datetime.now(timezone.utc).date()
    
    # Create base window for the date
    base_window = get_window(today)
    
    # For simplicity, assume UTC+1 offset (can be enhanced for DST later)
    # If target is 8 AM Paris time, that's 7 AM UTC (8 - 1)
    offset_hours = target_hour - 1
    
    # Adjust start time by the offset
    start_utc = base_window.start_utc.replace(hour=offset_hours)
    end_utc = base_window.end_utc.replace(hour=offset_hours)
    
    return TimeWindow(start_utc=start_utc, end_utc=end_utc)


def get_window_for_published_at(published_at: datetime) -> TimeWindow:
    """Get the appropriate time window for a video's published date.
    
    Args:
        published_at: Video publication datetime (any timezone)
        
    Returns:
        TimeWindow for the publication date in UTC
    """
    # Ensure published_at is in UTC
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    else:
        published_at = published_at.astimezone(timezone.utc)
    
    # Get the date and create window
    pub_date = published_at.date()
    return get_window(pub_date)