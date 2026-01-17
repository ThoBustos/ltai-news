"""Shared LLM utilities for Gemini-based agents.

This module centralizes:
- Google GenAI client management
- Token usage extraction and cost calculation
- JSON response parsing with markdown fence handling
- Structured output generation with automatic fallback
"""

import re
from dataclasses import dataclass
from typing import TypeVar, Type, Optional, Tuple

from pydantic import BaseModel
from google import genai
from google.genai.types import GenerateContentConfig, GenerateContentResponse

from app.config.settings import settings
from app.core.logging import logger


# === Pricing Configuration ===

@dataclass(frozen=True)
class GeminiFlashPricing:
    """Gemini Flash pricing (as of Dec 2024).
    
    See: https://ai.google.dev/pricing
    """
    input_per_1m: float = 0.075   # $0.075 per 1M input tokens
    output_per_1m: float = 0.30   # $0.30 per 1M output tokens


# Default pricing instance - single source of truth
GEMINI_FLASH_PRICING = GeminiFlashPricing()


# === Client Factory ===

def get_genai_client() -> genai.Client:
    """Get configured Google GenAI client."""
    return genai.Client(api_key=settings.google_api_key)


# === Cost Calculation ===

def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    pricing: GeminiFlashPricing = GEMINI_FLASH_PRICING,
) -> float:
    """Calculate cost in USD from token counts.
    
    Args:
        input_tokens: Number of input/prompt tokens
        output_tokens: Number of output/completion tokens
        pricing: Pricing configuration (defaults to Gemini Flash)
        
    Returns:
        Cost in USD
    """
    return (
        (input_tokens / 1_000_000) * pricing.input_per_1m +
        (output_tokens / 1_000_000) * pricing.output_per_1m
    )


# === Token Usage Extraction ===

@dataclass
class TokenUsage:
    """Token usage statistics from LLM response."""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float


def extract_token_usage(
    response: GenerateContentResponse,
    pricing: GeminiFlashPricing = GEMINI_FLASH_PRICING,
) -> TokenUsage:
    """Extract token counts and calculate cost from Gemini response.
    
    Args:
        response: Gemini API response object
        pricing: Pricing configuration for cost calculation
        
    Returns:
        TokenUsage with counts and calculated cost
    """
    usage = response.usage_metadata
    input_tokens = (usage.prompt_token_count or 0) if usage else 0
    output_tokens = (usage.candidates_token_count or 0) if usage else 0
    total_tokens = (usage.total_token_count or 0) if usage else (input_tokens + output_tokens)
    cost = calculate_cost(input_tokens, output_tokens, pricing)
    
    return TokenUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cost_usd=cost,
    )


# === JSON Response Parsing ===

# Regex for markdown code fences (handles ```json, ```JSON, ``` variants)
_FENCE_PATTERN = re.compile(
    r'^```(?:json)?\s*\n?(.*?)\n?```\s*$',
    re.DOTALL | re.IGNORECASE
)

# Regex patterns for common JSON issues from LLMs
_TRAILING_COMMA_PATTERN = re.compile(r',\s*([}\]])')  # Trailing comma before } or ]

T = TypeVar('T', bound=BaseModel)


class LLMParseError(ValueError):
    """Raised when LLM response cannot be parsed to expected schema."""
    
    def __init__(self, message: str, raw_response: str):
        super().__init__(message)
        self.raw_response = raw_response


def parse_llm_json(response_text: Optional[str], model: Type[T]) -> T:
    """Parse LLM response to Pydantic model, handling markdown fences.
    
    Handles common LLM output patterns:
    - ```json ... ``` (with newlines)
    - ``` ... ``` (without language tag)
    - Raw JSON with surrounding explanatory text
    
    Args:
        response_text: Raw LLM output (may include markdown fences)
        model: Pydantic model class to validate against
        
    Returns:
        Validated Pydantic model instance
        
    Raises:
        LLMParseError: If JSON cannot be extracted or validated
    """
    text = (response_text or "").strip()
    
    if not text:
        raise LLMParseError("Empty response from LLM", text)
    
    # Step 1: Try stripping markdown fences with regex
    fence_match = _FENCE_PATTERN.match(text)
    if fence_match:
        text = fence_match.group(1).strip()
        logger.debug("Stripped markdown fence from LLM response")
    
    # Step 2: If still not clean JSON, extract object by brace matching
    if not text.startswith('{'):
        start_idx = text.find('{')
        if start_idx == -1:
            raise LLMParseError(
                f"No JSON object found in response: {text[:200]}...",
                response_text or ""
            )
        
        # Find matching closing brace
        end_idx = text.rfind('}')
        if end_idx == -1 or end_idx < start_idx:
            raise LLMParseError(
                f"Malformed JSON in response (no closing brace): {text[:200]}...",
                response_text or ""
            )
        
        text = text[start_idx:end_idx + 1]
        logger.debug("Extracted JSON object from surrounding text")
    
    # Step 3: Repair common JSON issues (trailing commas)
    repaired_text = _TRAILING_COMMA_PATTERN.sub(r'\1', text)
    if repaired_text != text:
        logger.debug("Repaired trailing comma(s) in JSON response")
        text = repaired_text
    
    # Step 4: Validate against Pydantic model
    try:
        return model.model_validate_json(text)
    except Exception as e:
        raise LLMParseError(
            f"JSON validation failed for {model.__name__}: {e}",
            response_text or ""
        ) from e


# === Structured Output Generation ===

async def generate_structured(
    contents: str,
    response_model: Type[T],
    system_instruction: Optional[str] = None,
    temperature: float = 0.2,
    model_name: Optional[str] = None,
    client: Optional[genai.Client] = None,
) -> Tuple[T, TokenUsage]:
    """Generate structured output with automatic token tracking.
    
    Attempts to use Gemini's native response_schema for guaranteed JSON structure.
    Falls back to prompt-based JSON extraction if native schema fails
    (e.g., for complex nested models with $refs that Gemini can't handle).
    
    Args:
        contents: User message / prompt content
        response_model: Pydantic model class for response validation
        system_instruction: Optional system prompt
        temperature: Sampling temperature (default 0.2 for structured output)
        model_name: Model to use (defaults to settings.analysis_model_name)
        client: GenAI client (creates one if not provided)
        
    Returns:
        Tuple of (validated response model, token usage)
        
    Raises:
        LLMParseError: If response cannot be parsed after fallback
    """
    if client is None:
        client = get_genai_client()
    
    if model_name is None:
        model_name = settings.analysis_model_name
    
    response: Optional[GenerateContentResponse] = None
    
    # Try native structured output first
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=response_model,  # Pass Pydantic class directly
                temperature=temperature,
            )
        )
        result = response_model.model_validate_json(response.text or "")
        logger.debug(f"Native structured output succeeded for {response_model.__name__}")
        
    except Exception as native_error:
        # Fallback: inject schema into prompt and parse manually
        logger.warning(
            f"Native response_schema failed for {response_model.__name__} "
            f"({type(native_error).__name__}: {native_error}), using prompt fallback"
        )
        
        import json
        schema_instruction = (
            f"\n\nRespond with valid JSON matching this exact schema:\n"
            f"{json.dumps(response_model.model_json_schema())}\n\n"
            f"Your response must be valid JSON only, no additional text."
        )
        
        response = client.models.generate_content(
            model=model_name,
            contents=contents + schema_instruction,
            config=GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
            )
        )
        result = parse_llm_json(response.text, response_model)
    
    usage = extract_token_usage(response)
    return result, usage


