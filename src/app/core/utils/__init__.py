"""Core utilities package."""

from app.core.utils.duration import parse_duration_to_seconds
from app.core.utils.time_window import get_window, parse_date, TimeWindow
from app.core.utils.llm_client import (
    # Pricing
    GeminiFlashPricing,
    GEMINI_FLASH_PRICING,
    # Client
    get_genai_client,
    # Cost calculation
    calculate_cost,
    # Token usage
    TokenUsage,
    extract_token_usage,
    # Structured generation (use response_schema=PydanticClass)
    generate_structured,
    # DEPRECATED: Legacy JSON parsing (use true structured output instead)
    LLMParseError,
    parse_llm_json,
)

__all__ = [
    # Duration utilities
    "parse_duration_to_seconds",
    # Time window utilities
    "get_window",
    "parse_date",
    "TimeWindow",
    # LLM client utilities
    "GeminiFlashPricing",
    "GEMINI_FLASH_PRICING",
    "get_genai_client",
    "calculate_cost",
    "TokenUsage",
    "extract_token_usage",
    "generate_structured",
    # DEPRECATED (kept for backwards compatibility)
    "LLMParseError",
    "parse_llm_json",
]
