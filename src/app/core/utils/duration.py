"""Utilities for parsing YouTube/ISO 8601 durations."""

import re
from typing import Optional


def parse_duration_to_seconds(duration_str: Optional[str]) -> int:
    """
    Parses a YouTube/ISO 8601 duration string into total seconds.
    Example: 'PT1M27S' -> 87
    
    Args:
        duration_str: ISO 8601 duration string (e.g., 'PT1H2M30S')
        
    Returns:
        Total duration in seconds as an integer
    """
    if not duration_str or not isinstance(duration_str, str):
        return 0
        
    # Pattern for ISO 8601 duration: P[n]Y[n]M[n]DT[n]H[n]M[n]S
    # YouTube usually only uses the Time part (starting with T)
    pattern = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')
    match = pattern.match(duration_str)
    
    if not match:
        return 0
        
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    return (hours * 3600) + (minutes * 60) + seconds
