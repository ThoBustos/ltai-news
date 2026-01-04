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
    # JSON parsing
    LLMParseError,
    parse_llm_json,
    # Structured generation
    generate_structured,
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
    "LLMParseError",
    "parse_llm_json",
    "generate_structured",
]
