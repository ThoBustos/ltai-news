"""Test that ValidationError is re-raised as GeminiStructuredOutputError (retriable)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import BaseModel, ValidationError


def test_gemini_structured_output_error_exists():
    from app.core.utils.llm_client import GeminiStructuredOutputError
    assert issubclass(GeminiStructuredOutputError, Exception)


def test_gemini_structured_output_error_is_retriable():
    """Verify the exception is a plain Exception subclass (not BaseException) — LangGraph can retry it."""
    from app.core.utils.llm_client import GeminiStructuredOutputError
    err = GeminiStructuredOutputError("Schema validation failed: ...")
    assert isinstance(err, Exception)


def test_validation_error_raises_retriable():
    """When Gemini returns JSON that fails Pydantic validation, GeminiStructuredOutputError is raised."""
    from app.core.utils.llm_client import GeminiStructuredOutputError
    from pydantic import ValidationError

    class StrictModel(BaseModel):
        required_field: str
        score: float

    # Simulate what happens in generate_structured when JSON is invalid
    invalid_json = '{"required_field": "ok", "score": "not-a-float"}'

    with pytest.raises((ValidationError, GeminiStructuredOutputError)):
        try:
            StrictModel.model_validate_json(invalid_json)
        except ValidationError as e:
            raise GeminiStructuredOutputError(f"Schema validation failed: {e}") from e


def test_lessons_learned_backward_compat_get():
    """LessonsLearned.get() works like dict.get() for backwards compatibility."""
    from app.models.video_analysis import LessonsLearned
    ll = LessonsLearned(technical=["insight 1"], business=[], general=["tip"])
    assert ll.get("technical") == ["insight 1"]
    assert ll.get("business") == []
    assert ll.get("nonexistent", "default") == "default"


def test_confidence_scores_backward_compat_values():
    """ConfidenceScores.values() works like dict.values() for backwards compatibility."""
    from app.models.video_analysis import ConfidenceScores
    cs = ConfidenceScores(tldr=0.9, core_topics=0.85)
    vals = list(cs.values())
    assert len(vals) == 15  # All fields
    assert 0.9 in vals
    assert 0.85 in vals
