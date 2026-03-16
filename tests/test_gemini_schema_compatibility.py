"""Test that Pydantic models don't generate additionalProperties in JSON schema.

additionalProperties in JSON schema causes Gemini native structured output to fail,
forcing every LLM call to use the slower prompt-based fallback.
"""

import json
import pytest
from pydantic import BaseModel


def get_json_schema(model: type[BaseModel]) -> dict:
    return model.model_json_schema()


def has_additional_properties(schema: dict) -> bool:
    """Recursively check if any part of the schema has additionalProperties."""
    if "additionalProperties" in schema:
        return True
    for value in schema.values():
        if isinstance(value, dict) and has_additional_properties(value):
            return True
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and has_additional_properties(item):
                    return True
    return False


def test_video_analysis_core_no_additional_properties():
    from app.models.video_analysis import VideoAnalysisCoreV3
    schema = get_json_schema(VideoAnalysisCoreV3)
    assert not has_additional_properties(schema), (
        f"VideoAnalysisCoreV3 schema has additionalProperties: {json.dumps(schema, indent=2)}"
    )


def test_digest_content_no_additional_properties():
    from app.models.daily_digest import DigestContentResponse
    schema = get_json_schema(DigestContentResponse)
    assert not has_additional_properties(schema), (
        f"DigestContentResponse schema has additionalProperties: {json.dumps(schema, indent=2)}"
    )


def test_video_analysis_response_no_additional_properties():
    """VideoAnalysisResponse (V2) should now also be free of additionalProperties after fix."""
    from app.models.video_analysis import VideoAnalysisResponse
    schema = get_json_schema(VideoAnalysisResponse)
    assert not has_additional_properties(schema), (
        f"VideoAnalysisResponse schema has additionalProperties: {json.dumps(schema, indent=2)}"
    )


def test_lessons_learned_model_no_additional_properties():
    from app.models.video_analysis import LessonsLearned
    schema = get_json_schema(LessonsLearned)
    assert not has_additional_properties(schema)


def test_confidence_scores_model_no_additional_properties():
    from app.models.video_analysis import ConfidenceScores
    schema = get_json_schema(ConfidenceScores)
    assert not has_additional_properties(schema)
