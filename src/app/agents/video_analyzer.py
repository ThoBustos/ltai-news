"""Video analysis workflow using LangGraph and ChatGoogleGenerativeAI with single master extraction."""

import time
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from typing_extensions import TypedDict, NotRequired

import opik
from opik import track
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.logging import logger
from app.core.opik_manager import opik_manager
from app.config.settings import settings
from app.models.video_analysis import VideoAnalysisResponse, VideoAnalysisComplete, ProcessingMetrics
from app.repositories.video_repository import VideoRepository
from app.repositories.channel_repository import ChannelRepository


# === Type-safe state definition ===

class VideoAnalysisState(TypedDict):
    """Type-safe state for video analysis workflow."""
    
    # Input data (loaded in first node)
    video_id: str
    video: NotRequired[Dict[str, Any]]  # Video metadata
    transcript: NotRequired[Dict[str, Any]]  # Transcript data
    channel: NotRequired[Dict[str, Any]]  # Channel metadata
    
    # Analysis results (filled by nodes)
    analysis_response: NotRequired[VideoAnalysisResponse]
    
    # Processing tracking
    metrics: NotRequired[ProcessingMetrics]
    errors: NotRequired[List[str]]


# === Prompt management with Opik ===

class VideoAnalysisPrompts:
    """Centralized prompt management using Opik ChatPrompt system."""
    
    @staticmethod
    def get_master_extraction_prompt() -> opik.ChatPrompt:
        """Get comprehensive analysis prompt with structured output schema."""
        messages = [
            {
                "role": "system", 
                "content": """You are an expert at analyzing technical videos and extracting comprehensive insights.
                
                Your task is to analyze the video content and extract ALL the following information in a single structured response:
                - TLDR summary (1-2 paragraphs)
                - Core topics and their categories
                - Lessons learned (technical, business, general)
                - Sources referenced (papers, books, podcasts, links)
                - Key concepts mentioned
                - People and communities mentioned
                - Overall insights and analysis"""
            },
            {
                "role": "user",
                "content": """
                VIDEO TITLE: {{title}}
                VIDEO DESCRIPTION: {{description}}
                CHANNEL: {{channel_name}}
                VIDEO URL: {{url}}
                PUBLISHED AT: {{published_at}}
                RAW METADATA: {{raw_metadata}}
                TRANSCRIPT: {{transcript}}
                
                Analyze this video comprehensively and extract:

                1. TLDR: Create a 1-2 paragraph summary capturing the main purpose, key insights, and target audience
                2. CORE TOPICS: Identify 3-7 main topics with categories (technical/business/philosophy/general) and importance levels
                3. LESSONS LEARNED: Extract actionable lessons organized by category (technical/business/general)
                4. SOURCES: Identify any papers, books, podcasts, links, or external references mentioned
                5. CONCEPTS: Extract key concepts, frameworks, or ideas discussed
                6. PEOPLE & COMMUNITIES: Note any people, organizations, communities, events, or Discord servers mentioned
                7. INSIGHTS: Provide detailed analysis of the video's value and implications

                Provide confidence scores (0.0-1.0) for each extraction category.
                """
            }
        ]
        
        return opik.ChatPrompt(
            name="video-master-extraction",
            messages=messages,
            metadata={
                "category": "video-analysis",
                "output_schema": "VideoAnalysisResponse",
                "version": "1.0",
                "extraction_type": "comprehensive"
            }
        )


# === Workflow nodes ===

@track(name="load_context_node")
async def load_context_node(state: VideoAnalysisState) -> VideoAnalysisState:
    """Load video context (video + transcript + channel metadata)."""
    
    logger.info(f"Loading context for video {state['video_id']}")
    
    try:
        video_repo = VideoRepository()
        channel_repo = ChannelRepository()
        video_id = state["video_id"]

        # Get video metadata
        video = video_repo.get_video_by_id(video_id)
        if not video:
            raise ValueError(f"Video {video_id} not found")

        # Get transcript
        transcript = video_repo.get_transcript(video_id)
        if not transcript:
            raise ValueError(f"Transcript not found for video {video_id}")

        # Get channel metadata (if needed)
        channel = channel_repo.get_channel_by_id(video.channel_id) if video.channel_id else None
        
        # Update state
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


@track(name="master_extraction_node")
async def master_extraction_node(state: VideoAnalysisState) -> VideoAnalysisState:
    """Master extraction using ChatGoogleGenerativeAI with structured output."""
    
    logger.info(f"Starting master extraction for video {state['video_id']}")
    
    try:
        # Get prompt from Opik
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
                "transcript": state["transcript"]["text"][:12000]  # Truncate for token limits
            }
        )
        
        # Initialize ChatGoogleGenerativeAI with valid model name
        model_name = settings.analysis_model_name or "gemini-3-flash-preview"
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=1.0,  # Gemini 3.0+ defaults to 1.0
            api_key=settings.google_api_key,
        )
        
        # Create structured output version using JSON schema method
        structured_llm = llm.with_structured_output(
            schema=VideoAnalysisResponse.model_json_schema(),
            method="json_schema"  # Uses Gemini's native structured output
        )
        
        # Convert Opik ChatPrompt messages to LangChain messages
        langchain_messages = []
        for msg in formatted_messages:
            content = str(msg.get("content", ""))
            if msg.get("role") == "system":
                langchain_messages.append(SystemMessage(content=content))
            else:
                langchain_messages.append(HumanMessage(content=content))
        
        # Track timing and make structured LLM call
        # This returns a dict directly (validated against schema)
        start_time = time.time()
        structured_response_dict = await structured_llm.ainvoke(langchain_messages)
        processing_time = time.time() - start_time
        
        # Parse to Pydantic model for validation
        # structured_llm.ainvoke() returns a dict, but type checker may not know this
        if not isinstance(structured_response_dict, dict):
            # Convert to dict if needed
            structured_response_dict = dict(structured_response_dict) if hasattr(structured_response_dict, '__dict__') else {}
        
        response = VideoAnalysisResponse(**structured_response_dict)
        
        # Estimate token usage (structured_llm doesn't expose usage_metadata directly)
        # We'll estimate based on input/output text length
        # For more accurate tracking, we could make a parallel lightweight call
        input_text = "\n".join([
            msg.content if hasattr(msg, 'content') and isinstance(msg.content, str) 
            else str(msg.content) if hasattr(msg, 'content')
            else str(msg)
            for msg in langchain_messages
        ])
        output_text = json.dumps(structured_response_dict)
        
        # Rough token estimation: 1 token ≈ 4 characters for most text
        # This is an approximation - for exact counts, would need model-specific tokenizer
        input_tokens = max(1, len(input_text) // 4)
        output_tokens = max(1, len(output_text) // 4)
        
        # Calculate cost (Gemini 2.5 Flash pricing)
        INPUT_PRICE_PER_1K = 0.000075   # $0.075 per 1M input tokens
        OUTPUT_PRICE_PER_1K = 0.0003    # $0.30 per 1M output tokens
        cost = (input_tokens / 1000) * INPUT_PRICE_PER_1K + (output_tokens / 1000) * OUTPUT_PRICE_PER_1K
        
        # Create processing metrics
        metrics = ProcessingMetrics(
            workflow_version="1.0",
            extraction_method="single-master-prompt",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_cost=cost,
            processing_time_seconds=processing_time,
            confidence_scores=response.confidence_scores,
            extraction_completeness={
                "tldr": bool(response.tldr),
                "core_topics": bool(response.core_topics),
                "lessons_learned": bool(response.lessons_learned),
                "sources_referenced": bool(response.sources_referenced),
                "concepts_mentioned": bool(response.concepts_mentioned),
                "people_mentioned": bool(response.people_mentioned),
                "communities_mentioned": bool(response.communities_mentioned),
                "detailed_insights": bool(response.detailed_insights)
            }
        )
        
        # Update state
        state["analysis_response"] = response
        state["metrics"] = metrics
        
        # Add to Opik trace context (if available)
        try:
            current_span = opik.get_current_span()
            if current_span:
                current_span.update(
                    metadata={
                        "prompt_name": "video-master-extraction", 
                        "confidence_avg": sum(response.confidence_scores.values()) / len(response.confidence_scores),
                        "tokens_input": input_tokens,
                        "tokens_output": output_tokens,
                        "total_tokens": input_tokens + output_tokens,
                        "cost_usd": cost,
                        "processing_time_seconds": processing_time
                    },
                    prompts=[chat_prompt]
                )
        except (AttributeError, TypeError):
            # Opik span not available, skip update
            pass
        
        logger.info(
            f"Master extraction completed: {input_tokens + output_tokens} tokens, "
            f"${cost:.4f}, {processing_time:.2f}s, avg confidence: {sum(response.confidence_scores.values()) / len(response.confidence_scores):.2f}"
        )
        
        return state
        
    except Exception as e:
        logger.error(f"Failed master extraction: {e}")
        state.setdefault("errors", []).append(f"master_extraction: {e}")
        raise


@track(name="save_results_node")
async def save_results_node(state: VideoAnalysisState) -> VideoAnalysisState:
    """Save complete analysis to database."""
    
    logger.info(f"Saving results for video {state['video_id']}")
    
    try:
        from app.repositories.video_analysis_repository import VideoAnalysisRepository
        
        analysis_repo = VideoAnalysisRepository()
        response = state["analysis_response"]
        metrics = state["metrics"]
        
        # Create complete analysis for database storage
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
                "workflow_metadata": metrics.model_dump(mode='json')  # Serialize datetimes to ISO strings
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
                "opik_trace_id": None  # Will be populated by Opik tracer if available
            },
            model_name=settings.analysis_model_name or "gemini-3-flash-preview",
            processed_at=datetime.now(timezone.utc)
        )
        
        # Save to database
        success = await analysis_repo.save_analysis(complete_analysis)
        
        if not success:
            raise Exception("Failed to save analysis to database")
        
        logger.info(f"Analysis saved successfully for video {state['video_id']}")
        return state
        
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
        state.setdefault("errors", []).append(f"save_results: {e}")
        raise


# === Workflow definition ===

def create_video_analysis_workflow():
    """Create video analysis workflow with Opik tracking."""
    
    # Create workflow with type-safe state
    workflow = StateGraph(VideoAnalysisState)
    
    # Add nodes - simplified to 3 nodes (load, extract, save)
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
    
    # Wrap with Opik tracking using centralized manager
    tracked_workflow = opik_manager.track_workflow(
        compiled_workflow, 
        workflow_name="video-analysis",
        tags=["video", "analysis", settings.analysis_model_name or "gemini-3-flash-preview", "single-master-prompt"]
    )
    
    return tracked_workflow


# === Factory function for service integration ===

def get_video_analysis_workflow():
    """Get configured video analysis workflow instance."""
    return create_video_analysis_workflow()


# === Main execution function ===

async def analyze_video(video_id: str) -> Optional[VideoAnalysisComplete]:
    """Analyze a single video using the LangGraph workflow.
    
    Args:
        video_id: YouTube video ID to analyze
        
    Returns:
        VideoAnalysisComplete if successful, None if failed
    """
    logger.info(f"Starting video analysis workflow for {video_id}")
    
    try:
        # Create workflow
        workflow = get_video_analysis_workflow()
        
        # Initialize state
        initial_state = VideoAnalysisState(video_id=video_id)
        
        # Execute workflow
        final_state = await workflow.ainvoke(initial_state)
        
        if "errors" in final_state and final_state["errors"]:
            logger.error(f"Workflow completed with errors: {final_state['errors']}")
            return None
            
        if "analysis_response" not in final_state:
            logger.error("Workflow completed but no analysis response found")
            return None
        
        # Convert to complete analysis (this would be done in save_results_node)
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
            model_name="gemini-3.0-flash"
        )
        
        logger.info(f"Video analysis completed successfully for {video_id}")
        return complete_analysis
        
    except Exception as e:
        logger.error(f"Video analysis workflow failed for {video_id}: {e}", exc_info=True)
        return None