"""Test that schema_version is present on all V3 models stored in Supabase."""

import pytest


def test_video_analysis_core_has_schema_version():
    from app.models.video_analysis import VideoAnalysisCoreV3
    instance = VideoAnalysisCoreV3(
        video_id="test",
        title="Test",
        channel_name="Test Channel",
        summary="Test summary about something important.",
        content_type="news",
        key_points=["point 1", "point 2"],
        tags=["ai"],
        confidence_score=0.9,
    )
    assert instance.schema_version == "v3"
    assert "schema_version" in instance.model_dump()


def test_video_analysis_depth_has_schema_version():
    from app.models.video_analysis import VideoAnalysisDepthV3
    instance = VideoAnalysisDepthV3(
        video_id="test",
        tldr="One sentence summary.",
    )
    assert instance.schema_version == "v3"
    assert "schema_version" in instance.model_dump()


def test_video_analysis_core_content_type_validation():
    from app.models.video_analysis import VideoAnalysisCoreV3
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        VideoAnalysisCoreV3(
            video_id="test",
            title="Test",
            channel_name="Test",
            summary="Summary.",
            content_type="invalid_type",  # Not in Literal
            key_points=["p1"],
            tags=["t1"],
            confidence_score=0.8,
        )


def test_video_analysis_core_confidence_bounds():
    from app.models.video_analysis import VideoAnalysisCoreV3
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        VideoAnalysisCoreV3(
            video_id="test",
            title="Test",
            channel_name="Test",
            summary="Summary.",
            content_type="news",
            key_points=["p1"],
            tags=["t1"],
            confidence_score=1.5,  # Out of bounds
        )
