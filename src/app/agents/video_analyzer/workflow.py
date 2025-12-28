"""LangGraph workflow definition for video analysis."""

from typing import Optional

from langgraph.graph import StateGraph, START, END

from app.core.logging import logger
from app.core.opik_manager import opik_manager
from app.config.settings import settings
from app.models.video_analysis import VideoAnalysisComplete
from app.agents.video_analyzer.state import VideoAnalysisState
from app.agents.video_analyzer.nodes import (
    load_context_node,
    master_extraction_node,
    save_results_node,
)


def create_video_analysis_workflow():
    """Create video analysis workflow with Opik tracking."""

    workflow = StateGraph(VideoAnalysisState)

    # Add nodes
    workflow.add_node("load_context", load_context_node)
    workflow.add_node("master_extraction", master_extraction_node)
    workflow.add_node("save_results", save_results_node)

    # Define sequential edges
    workflow.add_edge(START, "load_context")
    workflow.add_edge("load_context", "master_extraction")
    workflow.add_edge("master_extraction", "save_results")
    workflow.add_edge("save_results", END)

    # Compile workflow
    compiled_workflow = workflow.compile()

    # Wrap with Opik tracking
    tracked_workflow = opik_manager.track_workflow(
        compiled_workflow,
        workflow_name="video-analysis",
        tags=["video", "analysis", settings.analysis_model_name, "single-master-prompt"]
    )

    return tracked_workflow


def get_video_analysis_workflow():
    """Get configured video analysis workflow instance."""
    return create_video_analysis_workflow()


async def analyze_video(video_id: str) -> Optional[VideoAnalysisComplete]:
    """Analyze a single video using the LangGraph workflow.

    Args:
        video_id: YouTube video ID to analyze

    Returns:
        VideoAnalysisComplete if successful, None if failed
    """
    logger.info(f"Starting video analysis workflow for {video_id}")

    try:
        workflow = get_video_analysis_workflow()
        initial_state = VideoAnalysisState(video_id=video_id)

        final_state = await workflow.ainvoke(initial_state)

        if "errors" in final_state and final_state["errors"]:
            logger.error(f"Workflow completed with errors: {final_state['errors']}")
            return None

        if "analysis_response" not in final_state:
            logger.error("Workflow completed but no analysis response found")
            return None

        response = final_state["analysis_response"]
        metrics = final_state["metrics"]

        complete_analysis = VideoAnalysisComplete(
            video_id=video_id,
            tldr=response.tldr,
            key_audience=response.key_audience,
            core_topics=[topic.model_dump() for topic in response.core_topics],
            lessons_learned=response.lessons_learned,
            detailed_insights=response.detailed_insights,
            sources_referenced=[source.model_dump() for source in response.sources_referenced],
            concepts_mentioned=[concept.model_dump() for concept in response.concepts_mentioned],
            people_mentioned=[person.model_dump() for person in response.people_mentioned],
            communities_mentioned=[community.model_dump() for community in response.communities_mentioned],
            metadata_extracted=final_state.get("video", {}),
            input_tokens=metrics.input_tokens,
            output_tokens=metrics.output_tokens,
            total_tokens=metrics.input_tokens + metrics.output_tokens,
            total_cost=metrics.total_cost,
            total_processing_time_seconds=metrics.processing_time_seconds,
            confidence_scores=response.confidence_scores,
            model_name=settings.analysis_model_name
        )

        logger.info(f"Video analysis completed successfully for {video_id}")
        return complete_analysis

    except Exception as e:
        logger.error(f"Video analysis workflow failed for {video_id}: {e}", exc_info=True)
        return None
