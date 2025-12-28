"""Workflow nodes for video analysis."""

import time
import json
from datetime import datetime, timezone

import opik
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.logging import logger
from app.config.settings import settings
from app.models.video_analysis import VideoAnalysisResponse, VideoAnalysisComplete, ProcessingMetrics
from app.repositories.video_repository import VideoRepository
from app.repositories.channel_repository import ChannelRepository
from app.agents.video_analyzer.state import VideoAnalysisState
from app.agents.video_analyzer.prompts import VideoAnalysisPrompts


def _extract_text(content) -> str:
    """Extract text from AIMessage content (handles str or list).
    
    Gemini models can return content as a string or as a list of content parts.
    This normalizes both cases to a single string.
    """
    if isinstance(content, str):
        return content
    return "".join(
        p if isinstance(p, str) else p.get("text", "")
        for p in content
    )


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
        logger.error(f"Failed to load context for video {state['video_id']}: {e}")
        state.setdefault("errors", []).append(f"load_context: {e}")
        raise


async def master_extraction_node(state: VideoAnalysisState) -> VideoAnalysisState:
    """Master extraction using ChatGoogleGenerativeAI with real token tracking."""
    logger.info(f"Starting master extraction for video {state['video_id']}")

    try:
        # Get prompt from prompts module
        chat_prompt = VideoAnalysisPrompts.get_master_extraction_prompt()

        # Format with variables
        formatted_messages = chat_prompt.format(
            variables={
                "title": state["video"]["title"],
                "description": state["video"]["description"],
                "channel_name": state["channel"]["name"],
                "url": state["video"]["url"],
                "published_at": state["video"]["published_at"],
                "raw_metadata": str(state["video"]["raw_metadata"]),
                "transcript": state["transcript"]["text"][:12000]
            }
        )

        # Initialize LLM (uses settings.analysis_model_name)
        model_name = settings.analysis_model_name
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=1.0,
            api_key=settings.google_api_key,
        )

        # Convert to LangChain messages
        langchain_messages = []
        for msg in formatted_messages:
            content = str(msg.get("content", ""))
            if msg.get("role") == "system":
                langchain_messages.append(SystemMessage(content=content))
            else:
                langchain_messages.append(HumanMessage(content=content))

        # Add JSON schema instruction
        schema_instruction = f"""

Respond with valid JSON matching this exact schema:
{json.dumps(VideoAnalysisResponse.model_json_schema(), indent=2)}

Your response must be valid JSON only, no additional text."""

        langchain_messages[-1] = HumanMessage(
            content=langchain_messages[-1].content + schema_instruction
        )

        # Make LLM call - use regular ainvoke to get usage_metadata
        start_time = time.time()
        response = await llm.ainvoke(langchain_messages)
        processing_time = time.time() - start_time

        # Extract REAL token counts from usage_metadata
        usage = response.usage_metadata or {}
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        # Calculate cost with real token counts (Gemini Flash pricing)
        INPUT_PRICE_PER_1M = 0.075
        OUTPUT_PRICE_PER_1M = 0.30
        cost = (input_tokens / 1_000_000) * INPUT_PRICE_PER_1M + (output_tokens / 1_000_000) * OUTPUT_PRICE_PER_1M

        # Parse JSON response - handle both str and list content types
        response_text = _extract_text(response.content).strip()
        if response_text.startswith('```json'):
            response_text = response_text.replace('```json', '').replace('```', '').strip()
        elif response_text.startswith('```'):
            response_text = response_text.replace('```', '').strip()

        if '{' in response_text:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            response_text = response_text[start:end]

        parsed_response = VideoAnalysisResponse.model_validate_json(response_text)

        # Create processing metrics with REAL values
        metrics = ProcessingMetrics(
            workflow_version="1.1",
            extraction_method="single-master-prompt",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_cost=cost,
            processing_time_seconds=processing_time,
            confidence_scores=parsed_response.confidence_scores,
            extraction_completeness={
                "tldr": bool(parsed_response.tldr),
                "core_topics": bool(parsed_response.core_topics),
                "lessons_learned": bool(parsed_response.lessons_learned),
                "sources_referenced": bool(parsed_response.sources_referenced),
                "concepts_mentioned": bool(parsed_response.concepts_mentioned),
                "people_mentioned": bool(parsed_response.people_mentioned),
                "communities_mentioned": bool(parsed_response.communities_mentioned),
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
                        "tokens_input": input_tokens,
                        "tokens_output": output_tokens,
                        "total_tokens": input_tokens + output_tokens,
                        "cost_usd": cost,
                        "processing_time_seconds": processing_time
                    }
                )
        except (AttributeError, TypeError):
            pass

        logger.info(
            f"Master extraction completed: {input_tokens + output_tokens} tokens, "
            f"${cost:.6f}, {processing_time:.2f}s"
        )

        return state

    except Exception as e:
        logger.error(f"Failed master extraction: {e}")
        state.setdefault("errors", []).append(f"master_extraction: {e}")
        raise


async def save_results_node(state: VideoAnalysisState) -> VideoAnalysisState:
    """Save complete analysis to database."""
    logger.info(f"Saving results for video {state['video_id']}")

    try:
        from app.repositories.video_analysis_repository import VideoAnalysisRepository

        analysis_repo = VideoAnalysisRepository()
        response = state["analysis_response"]
        metrics = state["metrics"]

        complete_analysis = VideoAnalysisComplete(
            video_id=state["video_id"],
            tldr=response.tldr,
            key_audience=response.key_audience,
            core_topics=[topic.model_dump() for topic in response.core_topics],
            lessons_learned=response.lessons_learned,
            detailed_insights=response.detailed_insights,
            sources_referenced=[source.model_dump() for source in response.sources_referenced],
            concepts_mentioned=[concept.model_dump() for concept in response.concepts_mentioned],
            people_mentioned=[person.model_dump() for person in response.people_mentioned],
            communities_mentioned=[community.model_dump() for community in response.communities_mentioned],
            metadata_extracted={
                "video": state["video"],
                "channel": state["channel"],
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
        logger.error(f"Failed to save results: {e}")
        state.setdefault("errors", []).append(f"save_results: {e}")
        raise
