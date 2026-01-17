"""Workflow nodes for video analysis."""

import time
import json
from datetime import datetime, timezone

import opik
from google.genai.types import GenerateContentConfig

from app.core.logging import logger
from app.config.settings import settings
from app.core.utils.llm_client import (
    get_genai_client,
    extract_token_usage,
    parse_llm_json,
)
from app.models.video_analysis import VideoAnalysisResponse, VideoAnalysisComplete, ProcessingMetrics
from app.repositories.video_repository import VideoRepository
from app.repositories.channel_repository import ChannelRepository
from app.agents.video_analyzer.state import VideoAnalysisState
from app.agents.video_analyzer.prompts import VideoAnalysisPrompts


async def load_context_node(state: VideoAnalysisState) -> VideoAnalysisState:
    """Load video context (video + transcript + channel metadata)."""
    logger.info(f"Loading context for video {state['video_id']}")

    try:
        video_repo = VideoRepository()
        channel_repo = ChannelRepository()
        video_id = state["video_id"]

        video = video_repo.get_by_id(video_id)
        if not video:
            raise ValueError(f"Video {video_id} not found")

        transcript = video_repo.get_transcript(video_id)
        if not transcript:
            raise ValueError(f"Transcript not found for video {video_id}")

        channel = channel_repo.get_channel_by_id(video.channel_id) if video.channel_id else None

        state["video"] = {
            "title": video.title,
            "description": video.description or "",
            "url": video.url,
            "published_at": video.published_at.isoformat() if video.published_at else "",
            "raw_metadata": video.raw_metadata or {}
        }
        state["transcript"] = {"text": transcript}
        state["channel"] = {
            "name": channel.name if channel else "Unknown",
            "id": video.channel_id or ""
        }

        logger.info(f"Context loaded for video {video_id}")
        return state

    except Exception as e:
        logger.error("Failed to load context for video {}: {}", state['video_id'], e)
        state.setdefault("errors", []).append(f"load_context: {e!s}")
        raise


async def master_extraction_node(state: VideoAnalysisState) -> VideoAnalysisState:
    """Master extraction using Google GenAI with Opik automatic cost tracking."""
    logger.info(f"Starting master extraction for video {state['video_id']}")

    try:
        # Validate required state from previous node
        video = state.get("video")
        transcript = state.get("transcript")
        channel = state.get("channel")
        
        if not video or not transcript or not channel:
            raise ValueError("Missing required state: video, transcript, or channel not loaded")

        # Get prompt from prompts module
        chat_prompt = VideoAnalysisPrompts.get_master_extraction_prompt()

        # Format with variables - V2: Full transcript (no truncation)
        formatted_messages = chat_prompt.format(
            variables={
                "title": video["title"],
                "description": video["description"],
                "channel_name": channel["name"],
                "url": video["url"],
                "published_at": video["published_at"],
                "transcript": transcript["text"]  # V2: Full transcript
            }
        )

        # Build prompt content for Google GenAI
        system_content = ""
        user_content = ""
        for msg in formatted_messages:
            content = str(msg.get("content", ""))
            if msg.get("role") == "system":
                system_content = content
            else:
                user_content = content

        # Add JSON schema instruction to user content
        schema_instruction = f"""

Respond with valid JSON matching this exact schema:
{json.dumps(VideoAnalysisResponse.model_json_schema(), indent=2)}

Your response must be valid JSON only, no additional text."""
        
        user_content += schema_instruction

        # Get GenAI client
        client = get_genai_client()
        model_name = settings.analysis_model_name

        # Make LLM call using Google GenAI SDK
        start_time = time.time()
        response = client.models.generate_content(
            model=model_name,
            contents=user_content,
            config=GenerateContentConfig(
                systemInstruction=system_content,
                temperature=1.0,
            )
        )
        processing_time = time.time() - start_time

        # Extract token usage and cost using shared utility
        usage = extract_token_usage(response)

        # Parse JSON response using shared utility (handles markdown fences)
        parsed_response = parse_llm_json(response.text, VideoAnalysisResponse)

        # Create processing metrics with calculated cost
        metrics = ProcessingMetrics(
            workflow_version="2.0",
            extraction_method="single-master-prompt",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_cost=usage.cost_usd,
            processing_time_seconds=processing_time,
            confidence_scores=parsed_response.confidence_scores,
            extraction_completeness={
                "tldr": bool(parsed_response.tldr),
                "teaser_hooks": bool(parsed_response.teaser_hooks),
                "keywords": bool(parsed_response.keywords),
                "core_topics": bool(parsed_response.core_topics),
                "lessons_learned": bool(parsed_response.lessons_learned),
                "sources_referenced": bool(parsed_response.sources_referenced),
                "concepts_mentioned": bool(parsed_response.concepts_mentioned),
                "people_mentioned": bool(parsed_response.people_mentioned),
                "communities_mentioned": bool(parsed_response.communities_mentioned),
                "direct_quotes": bool(parsed_response.direct_quotes),
                "analogies_metaphors": bool(parsed_response.analogies_metaphors),
                "frameworks_shared": bool(parsed_response.frameworks_shared),
                "statistics_data": bool(parsed_response.statistics_data),
                "section_analysis": bool(parsed_response.section_analysis),
                "detailed_insights": bool(parsed_response.detailed_insights)
            }
        )

        state["analysis_response"] = parsed_response
        state["metrics"] = metrics

        # Add metadata to Opik span (if available via track_langgraph)
        try:
            current_span = opik.get_current_span()
            if current_span:
                current_span.update(
                    metadata={
                        "prompt_name": "video-master-extraction",
                        "confidence_avg": sum(parsed_response.confidence_scores.values()) / len(parsed_response.confidence_scores),
                        "tokens_input": usage.input_tokens,
                        "tokens_output": usage.output_tokens,
                        "total_tokens": usage.total_tokens,
                        "cost_usd": usage.cost_usd,
                        "processing_time_seconds": processing_time
                    }
                )
        except (AttributeError, TypeError):
            pass

        logger.info(
            f"Master extraction completed: {usage.total_tokens} tokens, ${usage.cost_usd:.6f}, {processing_time:.2f}s"
        )

        return state

    except Exception as e:
        logger.error("Failed master extraction: {}", e)
        state.setdefault("errors", []).append(f"master_extraction: {e!s}")
        raise


async def save_results_node(state: VideoAnalysisState) -> VideoAnalysisState:
    """Save complete analysis to database."""
    logger.info(f"Saving results for video {state['video_id']}")

    try:
        from app.repositories.video_analysis_repository import VideoAnalysisRepository

        # Validate required state from previous nodes
        response = state.get("analysis_response")
        metrics = state.get("metrics")
        video = state.get("video")
        channel = state.get("channel")
        
        if not response or not metrics:
            raise ValueError("Missing required state: analysis_response or metrics not found")

        analysis_repo = VideoAnalysisRepository()

        complete_analysis = VideoAnalysisComplete(
            video_id=state["video_id"],
            tldr=response.tldr,
            key_audience=response.key_audience,
            teaser_hooks=response.teaser_hooks,
            keywords=response.keywords,
            core_topics=[topic.model_dump() for topic in response.core_topics],
            lessons_learned=response.lessons_learned,
            detailed_insights=response.detailed_insights,
            sources_referenced=[source.model_dump() for source in response.sources_referenced],
            concepts_mentioned=[concept.model_dump() for concept in response.concepts_mentioned],
            people_mentioned=[person.model_dump() for person in response.people_mentioned],
            communities_mentioned=[community.model_dump() for community in response.communities_mentioned],
            direct_quotes=[q.model_dump() for q in response.direct_quotes],
            analogies_metaphors=[a.model_dump() for a in response.analogies_metaphors],
            frameworks_shared=[f.model_dump() for f in response.frameworks_shared],
            statistics_data=[s.model_dump() for s in response.statistics_data],
            section_analysis=[sec.model_dump() for sec in response.section_analysis],
            metadata_extracted={
                "video": video or {},
                "channel": channel or {},
                "workflow_metadata": metrics.model_dump(mode='json')
            },
            input_tokens=metrics.input_tokens,
            output_tokens=metrics.output_tokens,
            total_tokens=metrics.input_tokens + metrics.output_tokens,
            total_cost=metrics.total_cost,
            total_processing_time_seconds=metrics.processing_time_seconds,
            confidence_scores=response.confidence_scores,
            processing_metadata={
                "extraction_method": metrics.extraction_method,
                "workflow_version": metrics.workflow_version,
                "opik_trace_id": None
            },
            model_name=settings.analysis_model_name,
            processed_at=datetime.now(timezone.utc)
        )

        success = await analysis_repo.save_analysis(complete_analysis)

        if not success:
            raise Exception("Failed to save analysis to database")

        logger.info(f"Analysis saved successfully for video {state['video_id']}")
        return state

    except Exception as e:
        logger.error("Failed to save results: {}", e)
        state.setdefault("errors", []).append(f"save_results: {e!s}")
        raise
