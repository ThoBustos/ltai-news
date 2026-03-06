"""Models for X thread generation."""

from typing import List
from pydantic import BaseModel, Field


class XThreadResponse(BaseModel):
    """LLM response schema for X thread generation.

    This ensures structured output with validation:
    - Minimum 5 tweets (hook + insights + videos + CTA)
    - Maximum 15 tweets (reasonable thread length)
    - Type safety for downstream processing
    """

    thread_tweets: List[str] = Field(
        description="Complete thread as list of tweet texts. Each <280 chars.",
        min_length=5,
        max_length=15
    )
