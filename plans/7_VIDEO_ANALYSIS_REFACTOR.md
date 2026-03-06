# 7. Video Analysis Refactor - Architecture & Bug Fixes

## Overview

This plan addresses architectural improvements, bug fixes, and best practices identified during code review. The goal is to create a clean, maintainable video analysis system with accurate token tracking and proper observability.

---

## Review Notes (2025-12-28)

**User Decisions:**
- **Model name**: Keep current setting from env/settings (`gemini-3-flash-preview` is the default)
- **Method names (Issue #8)**: Standardize to `get_by_id`, make `get_video_by_id` an alias

**Validation Complete:**
- ✅ Token tracking fix validated - `response.usage_metadata` works with regular `ainvoke()`
- ✅ Missing method bug confirmed - `get_videos_by_status()` doesn't exist, `get_unprocessed_videos()` does
- ✅ Repository methods: `get_by_id` delegates to `get_video_by_id` currently - will flip this

---

## Issues Identified

| ID | Issue | Severity | Category |
|----|-------|----------|----------|
| 1 | Token estimation instead of real counts | 🔴 High | Accuracy |
| 2 | `gemini_client.py` is dead code (never imported) | 🟡 Medium | Cleanup |
| 3 | `get_videos_by_status()` called but doesn't exist | 🔴 High | Bug |
| 4 | JSONB double-serialization (`json.dumps` on JSONB columns) | 🔴 High | Data Integrity |
| 5 | Opik traces arriving as separate events | 🟡 Medium | Observability |
| 6 | Monolithic agent file (452 lines) | 🟡 Medium | Maintainability |
| 7 | API response models in route file | 🟢 Low | Architecture |
| 8 | Duplicate methods (`get_by_id` / `get_video_by_id`) | 🟢 Low | Consistency |

---

## Phase 1: Critical Bug Fixes

### 1.1 Fix Token Tracking (Issue #1)

**Problem:** Lines 222-230 in `video_analyzer.py` estimate tokens with `len(text) // 4` instead of using real values.

**Root Cause:** `with_structured_output()` returns a dict, stripping `usage_metadata` from the AIMessage.

**Solution:** Use regular `ainvoke()` and manually parse JSON, preserving access to `usage_metadata`.

#### File: `src/app/agents/video_analyzer/nodes.py` (to be created)

**Before (current pattern):**
```python
structured_llm = llm.with_structured_output(schema=VideoAnalysisResponse.model_json_schema(), method="json_schema")
structured_response_dict = await structured_llm.ainvoke(langchain_messages)
# usage_metadata NOT available here!
input_tokens = max(1, len(input_text) // 4)  # ESTIMATION
```

**After (correct pattern):**
```python
# Use regular invoke - returns AIMessage with usage_metadata
response = await llm.ainvoke(langchain_messages)

# Extract real token counts
usage = response.usage_metadata
input_tokens = usage.get("input_tokens", 0)
output_tokens = usage.get("output_tokens", 0)

# Parse content as JSON and validate with Pydantic
response_text = response.content
# ... JSON cleanup logic ...
parsed_response = VideoAnalysisResponse.model_validate_json(response_text)
```

**Cost calculation update:**
```python
# Gemini 2.5 Flash pricing (verify current rates)
INPUT_PRICE_PER_1M = 0.075   # $0.075 per 1M input tokens
OUTPUT_PRICE_PER_1M = 0.30    # $0.30 per 1M output tokens

cost = (input_tokens / 1_000_000) * INPUT_PRICE_PER_1M + (output_tokens / 1_000_000) * OUTPUT_PRICE_PER_1M
```

---

### 1.2 Fix Missing Method Bug (Issue #3)

**Problem:** `video_analysis_service.py:107` calls `get_videos_by_status("collected")` which doesn't exist.

**File:** `src/app/services/video_analysis_service.py`

**Line 107 - Change:**
```python
# FROM:
videos = self.video_repo.get_videos_by_status("collected", limit=limit)

# TO:
videos = self.video_repo.get_unprocessed_videos(limit=limit)
```

---

### 1.3 Fix JSONB Double-Serialization (Issue #4)

**Problem:** Repository uses `json.dumps()` on JSONB columns, causing escaped JSON strings in database.

**File:** `src/app/repositories/video_analysis_repository.py`

**Lines 44-60 - Change:**
```python
# FROM (double-serialized):
data = {
    "key_points": json.dumps([...]),
    "tags": json.dumps(self._extract_tags(analysis)),
    "core_topics": json.dumps(analysis.core_topics, default=_json_serializer),
    "lessons_learned": json.dumps(analysis.lessons_learned, default=_json_serializer),
    # ... etc
}

# TO (correct - pass Python objects directly for JSONB):
data = {
    "video_id": analysis.video_id,
    "summary": analysis.tldr,
    "analysis": analysis.detailed_insights,
    "key_points": [f"{topic['topic']} ({topic['category']})" for topic in analysis.core_topics],
    "tags": self._extract_tags(analysis),
    "tldr": analysis.tldr,
    "core_topics": analysis.core_topics,  # Python list, not json.dumps()
    "lessons_learned": analysis.lessons_learned,  # Python dict
    "detailed_insights": analysis.detailed_insights,
    "sources_referenced": analysis.sources_referenced,  # Python list
    "concepts_mentioned": analysis.concepts_mentioned,
    "people_mentioned": analysis.people_mentioned,
    "communities_mentioned": analysis.communities_mentioned,
    "metadata_extracted": analysis.metadata_extracted,
    "input_tokens": analysis.input_tokens,
    "output_tokens": analysis.output_tokens,
    "total_tokens": analysis.total_tokens,
    "total_cost": analysis.total_cost,
    "total_processing_time_seconds": analysis.total_processing_time_seconds,
    "processing_metadata": analysis.processing_metadata,  # Python dict or None
    "model_name": analysis.model_name,
    "tokens_used": analysis.total_tokens,
    "processed_at": analysis.processed_at.isoformat() if analysis.processed_at else datetime.now(timezone.utc).isoformat()
}
```

**Note:** Only `processed_at` needs `.isoformat()` because it's a TIMESTAMP column, not JSONB.

---

## Phase 2: Observability Fixes

### 2.1 Fix Opik Trace Grouping (Issue #5)

**Problem:** Using `@track` decorators on nodes creates separate traces instead of nested spans under `track_langgraph`.

**Solution:** Remove `@track` decorators from nodes; let `track_langgraph` handle all tracing.

**File:** `src/app/agents/video_analyzer/nodes.py`

**Remove decorators:**
```python
# FROM:
@track(name="load_context_node")
async def load_context_node(state: VideoAnalysisState) -> VideoAnalysisState:

# TO:
async def load_context_node(state: VideoAnalysisState) -> VideoAnalysisState:
```

Apply to all three nodes:
- `load_context_node`
- `master_extraction_node`
- `save_results_node`

**Opik span metadata (inside nodes):**
The manual `opik.get_current_span()` calls can stay - they add metadata to the span created by `track_langgraph`:

```python
# This is fine - adds metadata to existing span
try:
    current_span = opik.get_current_span()
    if current_span:
        current_span.update(metadata={...})
except (AttributeError, TypeError):
    pass
```

---

## Phase 3: Code Cleanup

### 3.1 Delete Dead Code (Issue #2)

**Action:** Delete `src/app/client/gemini_client.py`

**Verification:** Grep confirms no imports exist:
```bash
grep -r "from app.client.gemini_client\|import.*gemini_client" src/
# Returns: No matches
```

---

### 3.2 Fix Repository Method Inconsistency (Issue #8)

**File:** `src/app/repositories/video_repository.py`

**Option A (Recommended):** Keep `get_by_id` as the canonical method, deprecate `get_video_by_id`:

```python
def get_by_id(self, video_id: str) -> Optional[Video]:
    """Get video by YouTube video ID.
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        Video model or None if not found
    """
    # Full implementation here (move from get_video_by_id)
    try:
        result = (
            self.client.table(self.table)
            .select("*")
            .eq("id", video_id)
            .single()
            .execute()
        )
        if result.data:
            return Video(**result.data)
        return None
    except Exception as e:
        error_str = str(e)
        if "PGRST116" in error_str or "No rows" in error_str:
            return None
        logger.error(f"Failed to get video {video_id}: {e}")
        raise

# Alias for backwards compatibility (can remove later)
get_video_by_id = get_by_id
```

**Update all callers to use `get_by_id`:**
- `src/app/agents/video_analyzer/nodes.py` (load_context_node)
- `src/app/services/video_analysis_service.py` (_validate_prerequisites)

---

## Phase 4: Architecture Refactor

### 4.1 Split Agent Module (Issue #6)

**Current structure:**
```
src/app/agents/
├── __init__.py
└── video_analyzer.py  # 452 lines - too large
```

**New structure:**
```
src/app/agents/
├── __init__.py
└── video_analyzer/
    ├── __init__.py          # Public exports
    ├── state.py              # VideoAnalysisState TypedDict
    ├── prompts.py            # VideoAnalysisPrompts class
    ├── nodes.py              # Node functions
    └── workflow.py           # Graph creation & execution
```

#### File: `src/app/agents/video_analyzer/__init__.py`
```python
"""Video analysis workflow using LangGraph and Gemini."""

from app.agents.video_analyzer.workflow import (
    analyze_video,
    get_video_analysis_workflow,
    create_video_analysis_workflow,
)
from app.agents.video_analyzer.state import VideoAnalysisState

__all__ = [
    "analyze_video",
    "get_video_analysis_workflow", 
    "create_video_analysis_workflow",
    "VideoAnalysisState",
]
```

#### File: `src/app/agents/video_analyzer/state.py`
```python
"""Type-safe state definition for video analysis workflow."""

from typing import Dict, Any, List
from typing_extensions import TypedDict, NotRequired

from app.models.video_analysis import VideoAnalysisResponse, ProcessingMetrics


class VideoAnalysisState(TypedDict):
    """Type-safe state for video analysis workflow."""
    
    # Input data (loaded in first node)
    video_id: str
    video: NotRequired[Dict[str, Any]]
    transcript: NotRequired[Dict[str, Any]]
    channel: NotRequired[Dict[str, Any]]
    
    # Analysis results (filled by nodes)
    analysis_response: NotRequired[VideoAnalysisResponse]
    
    # Processing tracking
    metrics: NotRequired[ProcessingMetrics]
    errors: NotRequired[List[str]]
```

#### File: `src/app/agents/video_analyzer/prompts.py`
```python
"""Prompt management for video analysis using Opik ChatPrompt."""

import opik


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
- Overall insights and analysis

IMPORTANT: Respond with valid JSON only. No additional text before or after the JSON."""
            },
            {
                "role": "user",
                "content": """VIDEO TITLE: {{title}}
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

Provide confidence scores (0.0-1.0) for each extraction category."""
            }
        ]
        
        return opik.ChatPrompt(
            name="video-master-extraction",
            messages=messages,
            metadata={
                "category": "video-analysis",
                "output_schema": "VideoAnalysisResponse",
                "version": "1.1",
                "extraction_type": "comprehensive"
            }
        )
```

#### File: `src/app/agents/video_analyzer/nodes.py`
```python
"""Workflow nodes for video analysis."""

import time
import json
from datetime import datetime, timezone
from typing import Dict, Any

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
        
        # Initialize LLM (uses settings.analysis_model_name, default: gemini-3-flash-preview)
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
        
        # Calculate cost with real token counts
        INPUT_PRICE_PER_1M = 0.075
        OUTPUT_PRICE_PER_1M = 0.30
        cost = (input_tokens / 1_000_000) * INPUT_PRICE_PER_1M + (output_tokens / 1_000_000) * OUTPUT_PRICE_PER_1M
        
        # Parse JSON response
        response_text = response.content.strip()
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
```

#### File: `src/app/agents/video_analyzer/workflow.py`
```python
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
```

---

### 4.2 Move API Response Models (Issue #7)

**Create:** `src/app/api/schemas/orchestrator.py`

```python
"""API request/response schemas for orchestrator endpoints."""

from typing import List, Optional
from pydantic import BaseModel

from app.models.pipeline import PipelineResult, TranscriptExtractionResult
from app.models.video_analysis import VideoAnalysisComplete


class PipelineRunResponse(BaseModel):
    """Response for pipeline run requests."""
    message: str
    target_date: str
    status: str
    result: PipelineResult


class BackfillRequest(BaseModel):
    """Request for backfill operations."""
    start_date: str
    end_date: str


class BackfillResponse(BaseModel):
    """Response for backfill requests."""
    message: str
    date_range: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    results: List[PipelineResult]


class TranscriptExtractionResponse(BaseModel):
    """Response for transcript extraction requests."""
    message: str
    target_date: str
    status: str
    result: TranscriptExtractionResult


class VideoAnalysisResponse(BaseModel):
    """Response for single video analysis requests."""
    message: str
    video_id: str
    status: str
    analysis: Optional[VideoAnalysisComplete] = None
    processing_time_seconds: Optional[float] = None
    total_cost: Optional[float] = None
    total_tokens: Optional[int] = None
```

**Update:** `src/app/api/orchestrator.py` - Replace local model definitions with imports:

```python
from app.api.schemas.orchestrator import (
    PipelineRunResponse,
    BackfillRequest,
    BackfillResponse,
    TranscriptExtractionResponse,
    VideoAnalysisResponse,
)
```

---

## Phase 5: File Operations Summary

### Files to CREATE:
| Path | Description |
|------|-------------|
| `src/app/agents/video_analyzer/__init__.py` | Module exports |
| `src/app/agents/video_analyzer/state.py` | State TypedDict |
| `src/app/agents/video_analyzer/prompts.py` | Prompt management |
| `src/app/agents/video_analyzer/nodes.py` | Workflow nodes |
| `src/app/agents/video_analyzer/workflow.py` | Graph definition |
| `src/app/api/schemas/__init__.py` | Schema module |
| `src/app/api/schemas/orchestrator.py` | API DTOs |

### Files to MODIFY:
| Path | Changes |
|------|---------|
| `src/app/repositories/video_analysis_repository.py` | Remove `json.dumps()` from JSONB columns |
| `src/app/repositories/video_repository.py` | Make `get_by_id` canonical, alias `get_video_by_id` |
| `src/app/services/video_analysis_service.py` | Fix `get_videos_by_status` → `get_unprocessed_videos` |
| `src/app/api/orchestrator.py` | Import schemas from new module |

### Files to DELETE:
| Path | Reason |
|------|--------|
| `src/app/client/gemini_client.py` | Dead code, never imported |
| `src/app/agents/video_analyzer.py` | Replaced by module structure |

---

## Implementation Order

1. **Phase 1** (Critical bugs - do first):
   - Fix `get_videos_by_status` → `get_unprocessed_videos`
   - Fix JSONB double-serialization
   
2. **Phase 4** (Architecture - creates new files):
   - Create `src/app/agents/video_analyzer/` module structure
   - This includes the token tracking fix (Issue #1)
   - This includes the Opik trace fix (Issue #5)

3. **Phase 3** (Cleanup):
   - Delete `gemini_client.py`
   - Delete old `video_analyzer.py`
   - Fix repository method consistency

4. **Phase 4.2** (API schemas):
   - Create API schemas module
   - Update orchestrator imports

---

## Testing Checklist

After implementation, verify:

- [ ] Token counts in DB match real values (not estimated)
- [ ] JSONB columns contain proper JSON (not escaped strings)
- [ ] Opik traces show single grouped trace per video analysis
- [ ] `get_videos_by_status` error is gone
- [ ] All imports resolve correctly
- [ ] Video analysis workflow completes successfully

**Test command:**
```bash
# Run single video analysis
curl -X POST "http://localhost:8000/api/orchestrator/process-video/VIDEO_ID"

# Check DB for proper JSONB format
# In Supabase: SELECT core_topics FROM video_processed_data WHERE video_id = 'VIDEO_ID';
# Should show: [{"topic": "...", "category": "...", "importance": "..."}]
# NOT: "[{\"topic\": \"...\", ...}]"
```

---

## Notes

- **Workflow version** bumped from "1.0" to "1.1" to track this refactor
- **Model name** uses `settings.analysis_model_name` (default: `gemini-3-flash-preview`)
- **Cost calculation** uses per-million pricing (verify current Gemini rates)


