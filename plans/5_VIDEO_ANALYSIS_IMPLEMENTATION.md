# Video Analysis Implementation Plan (Phase 3) - ENHANCED

## Overview
This document outlines the implementation of **Phase 3: Video Processing** using LangGraph and **Gemini 3.0 Flash**. The system will analyze video transcripts to extract structured insights including TLDR, core topics, lessons learned, sources, concepts, and detailed analysis. All processing will be instrumented with **Opik for comprehensive observability**, using **structured outputs with Pydantic models**, **centralized prompt management**, and **app-level Opik configuration**. Cost/time metrics will be tracked at both per-step and aggregate levels.

### ✨ Key Enhancements
- **Structured Outputs**: Direct Pydantic model validation with `llm.with_structured_output()`
- **Opik Prompt Management**: Centralized prompt versioning and management
- **App-Level Opik Config**: Centralized configuration for all agents and workflows
- **Enhanced Data Models**: Clean separation between LLM schemas and database entities  
- **Gemini 3.0 Flash**: Latest model with enhanced capabilities
- **Type-Safe State**: TypedDict for LangGraph state management

---

## Current State Analysis

### ✅ What's Already Implemented

**Database Schema**
- `videos` table with processing status tracking (`collected`, `processing`, `processed`, `failed`)
- `video_transcripts` table storing transcript text
- `video_processed_data` table with basic structure:
  - `video_id` (PK)
  - `summary` (TEXT)
  - `analysis` (TEXT) - Core column for extensive analysis
  - `key_points` (JSONB) - Array of strings
  - `tags` (JSONB) - Specific extracted tags
  - `model_name` (TEXT)
  - `tokens_used` (INTEGER)
  - `processed_at` (TIMESTAMPTZ)

**Services & Infrastructure**
- `ContentOrchestrator` with `_process_videos()` method (placeholder implementation)
- `VideoRepository` with status management and transcript retrieval
- `TranscriptService` for fetching and storing transcripts
- `AnalysisService` placeholder with basic structure
- Configuration management via `Settings` class

**Current Flow**
- Phase 1: Content extraction (videos collected with status `collected`)
- Phase 2: Transcript extraction (transcripts saved, `transcript_fetched` flag set)
- Phase 3: **Video Processing** (placeholder - needs implementation)
- Phase 4: Digest generation (placeholder)

### ❌ What Needs to Be Built

**LangGraph Agent/Workflow**
- Multi-node workflow for structured extraction
- Integration with Gemini 3.0 Flash
- App-level Opik instrumentation for observability
- Structured outputs using Pydantic models
- Cost and time tracking per node

**Data Models**
- Rich `VideoAnalysis` model with all extracted fields
- Processing metrics model (tokens, cost, time)
- Node execution tracking

**Database Schema Updates**
- Enhanced `video_processed_data` table with new columns
- Cost and time tracking fields

**Service Layer**
- `VideoAnalysisService` to orchestrate LangGraph agent
- Integration with existing orchestrator

**Repository Layer**
- `VideoAnalysisRepository` for saving rich analysis data
- Methods to update processing metrics

**API Endpoints**
- Single video processing endpoint
- Integration with daily pipeline

---

## Architecture & Design Decisions

### 1. LangGraph Workflow Structure ✨ UPDATED

**File:** `src/app/agents/video_analyzer.py` (single file)

**Simplified workflow with single master extraction:**

```
START
  ↓
[Load Context] → Fetch video metadata + transcript + channel info
  ↓
[Master Extraction] → Single comprehensive prompt extracts all data at once
  ↓
[Save Results] → Store complete analysis to database
  ↓
END
```

**Key Design Principles:**
- **Cost-Optimized**: Single API call instead of 8 (1 vs 8 = 87.5% cost reduction)
- **Comprehensive Extraction**: One master prompt with structured output for all fields
- **Future-Ready**: Infrastructure supports multiple nodes for case studies later
- **State Management**: Simple state dict with video context + extracted data
- **Error Handling**: Single point of failure, easier debugging
- **Idempotency**: Workflow can be re-run safely (upsert pattern in repository)

**Future Enhancement Path:**
- Easy to split into individual nodes for prompt comparison studies
- Token tracking infrastructure ready for per-section analysis
- Opik integration supports both single and multi-node approaches

### 2. Enhanced Prompt Management with Opik ✨ NEW

**Decision: Use Opik ChatPrompt for Centralized Management**

**File:** `src/app/agents/video_analyzer/prompts.py`

**Benefits:**
- **Automatic Versioning**: Opik tracks prompt changes automatically
- **Central Management**: View/edit prompts in Opik UI
- **Experiment Linking**: Connect prompts to specific experiment runs
- **Team Collaboration**: Share prompts across team members
- **Structured Output Schema Binding**: Link prompts to Pydantic response models

**Structure:**
```python
import opik
from app.models.video_analysis import VideoAnalysisResponse  # Simplified import

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
```

**Integration with Opik Experiments:**
- Prompts automatically linked to traces and experiments
- Version history tracked in Opik platform
- A/B testing different prompt versions

### 3. Cost & Time Tracking

**Per-Node Tracking:**
- Track tokens (input + output) per node
- Track processing time per node
- Track cost estimate per node (based on Gemini pricing)

**Aggregate Tracking:**
- Total tokens (sum across all nodes)
- Total cost (sum across all nodes)
- Total processing time (sum across all nodes)
- Store in `video_processed_data.processing_metadata` (JSONB)

**Database Fields:**
```sql
-- Add to video_processed_data table
ALTER TABLE video_processed_data ADD COLUMN IF NOT EXISTS input_tokens INTEGER;   -- Track input tokens
ALTER TABLE video_processed_data ADD COLUMN IF NOT EXISTS output_tokens INTEGER;  -- Track output tokens  
ALTER TABLE video_processed_data ADD COLUMN IF NOT EXISTS total_tokens INTEGER;
ALTER TABLE video_processed_data ADD COLUMN IF NOT EXISTS total_cost DECIMAL(10, 6);
ALTER TABLE video_processed_data ADD COLUMN IF NOT EXISTS total_processing_time_seconds DECIMAL(10, 3);
ALTER TABLE video_processed_data ADD COLUMN IF NOT EXISTS processing_metadata JSONB;  -- Per-node details (future case studies)
```

**Processing Metadata Structure:**
```json
{
  "nodes": [
    {
      "node_name": "extract_tldr",
      "tokens_input": 1500,
      "tokens_output": 200,
      "cost_usd": 0.0012,
      "processing_time_seconds": 2.5,
      "status": "success"
    },
    ...
  ],
  "workflow_version": "1.0",
  "prompt_versions": {
    "tldr": "1.0",
    "core_topics": "1.0",
    ...
  }
}
```

### 4. App-Level Opik Integration Strategy ✨ NEW

**Decision: Centralized App-Level Opik Configuration**

**File:** `src/app/core/opik_manager.py`

**Rationale:**
- **Centralized Config**: Single place to manage Opik settings for all agents
- **Consistent Project Naming**: All workflows under same project umbrella  
- **Shared Authentication**: Single API key and workspace management
- **Cross-Workflow Debugging**: Easier to trace across multiple agents

**Implementation:**
```python
# src/app/core/opik_manager.py
import opik
from opik.integrations.langchain import track_langgraph, OpikTracer
from app.core.logging import logger
from app.config.settings import settings

class OpikManager:
    """Centralized Opik management for all agents and workflows."""
    
    def __init__(self):
        if settings.opik_api_key:
            opik.configure(
                api_key=settings.opik_api_key,
                project_name=settings.opik_project_name or "ltai-news",
                workspace=settings.opik_workspace
            )
            self.enabled = True
            logger.info(f"Opik configured for project: {settings.opik_project_name}")
        else:
            self.enabled = False
            logger.warning("Opik API key not found - tracing disabled")
    
    def create_tracer(self, workflow_name: str, tags: list = None) -> OpikTracer:
        """Create workflow-specific tracer with consistent project settings."""
        if not self.enabled:
            return None
            
        return OpikTracer(
            project_name=settings.opik_project_name or "ltai-news",
            tags=(tags or []) + [workflow_name, "production"],
            metadata={
                "workflow": workflow_name,
                "version": "1.0",
                "environment": "production"
            }
        )
    
    def track_workflow(self, compiled_graph, workflow_name: str, tags: list = None):
        """Wrap LangGraph with Opik tracking."""
        if not self.enabled:
            return compiled_graph
            
        tracer = self.create_tracer(workflow_name, tags)
        return track_langgraph(compiled_graph, tracer)

# Global instance
opik_manager = OpikManager()
```

**What to Track:**
- Each node execution (start/end time, tokens, cost, confidence scores)
- LLM calls with structured prompts and responses
- Errors and retry attempts
- Workflow-level metrics and performance
- Prompt usage and effectiveness metrics

---

## Implementation Plan

### Phase 1: Database Schema Updates

#### 1.1 Create Migration File
**File:** `supabase/migrations/YYYYMMDDHHMMSS_video_analysis_schema.sql`

**Changes:**
```sql
-- Enhanced video_processed_data table
ALTER TABLE video_processed_data ADD COLUMN IF NOT EXISTS tldr TEXT;
ALTER TABLE video_processed_data ADD COLUMN IF NOT EXISTS core_topics JSONB;
ALTER TABLE video_processed_data ADD COLUMN IF NOT EXISTS lessons_learned JSONB;
ALTER TABLE video_processed_data ADD COLUMN IF NOT EXISTS detailed_insights TEXT;
ALTER TABLE video_processed_data ADD COLUMN IF NOT EXISTS sources_referenced JSONB;
ALTER TABLE video_processed_data ADD COLUMN IF NOT EXISTS concepts_mentioned JSONB;
ALTER TABLE video_processed_data ADD COLUMN IF NOT EXISTS people_mentioned JSONB;
ALTER TABLE video_processed_data ADD COLUMN IF NOT EXISTS communities_mentioned JSONB;
ALTER TABLE video_processed_data ADD COLUMN IF NOT EXISTS metadata_extracted JSONB;
ALTER TABLE video_processed_data ADD COLUMN IF NOT EXISTS total_tokens INTEGER;
ALTER TABLE video_processed_data ADD COLUMN IF NOT EXISTS total_cost DECIMAL(10, 6);
ALTER TABLE video_processed_data ADD COLUMN IF NOT EXISTS total_processing_time_seconds DECIMAL(10, 3);

-- Update processing_metadata to store per-node details
-- (column already exists, just document structure)
```

**JSONB Field Structures:**
- `core_topics`: `[{"topic": "string", "category": "string", "importance": "high|medium|low"}]`
- `lessons_learned`: `{"technical": ["..."], "business": ["..."], "general": ["..."]}`
- `sources_referenced`: `[{"type": "paper|book|podcast|link", "title": "...", "url": "..."}]`
- `concepts_mentioned`: `[{"concept": "...", "description": "...", "relevance": "..."}]`
- `people_mentioned`: `[{"name": "...", "role": "...", "affiliation": "..."}]`
- `communities_mentioned`: `[{"type": "discord|community|event", "name": "...", "url": "..."}]`
- `metadata_extracted`: `{"channel": {...}, "video": {...}, "participants": [...]}`

---

### Phase 2: Simplified Data Models ✨ UPDATED

#### 2.1 Create Single Video Analysis Model File

**Simplified Structure (matching current patterns):**
```
src/app/models/
├── video_analysis.py  # Single file with all models (matches existing pattern)
```

#### 2.1.1 Complete Video Analysis Models
**File:** `src/app/models/video_analysis.py`

**Purpose:** All video analysis models in single file (matches current codebase pattern)

```python
"""Video analysis models for comprehensive extraction and database storage."""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional, Any, Literal
from datetime import datetime

# === LLM Response Model (for structured output) ===

class CoreTopic(BaseModel):
    """Individual topic with metadata."""
    topic: str = Field(description="Clear, specific topic name")
    category: Literal["technical", "business", "philosophy", "general"] = Field(description="Topic category")
    importance: Literal["high", "medium", "low"] = Field(description="Relative importance")

class SourceReference(BaseModel):
    """Individual source reference."""
    type: Literal["paper", "book", "podcast", "link", "discord", "community", "event"] = Field(description="Source type")
    title: str = Field(description="Source title or name")
    url: Optional[str] = Field(None, description="URL if available")
    author: Optional[str] = Field(None, description="Author or creator")

class ConceptMention(BaseModel):
    """Key concept or framework mentioned."""
    concept: str = Field(description="Concept or framework name")
    description: str = Field(description="Brief description of the concept")
    relevance: str = Field(description="Why this concept is relevant to the video")

class PersonMention(BaseModel):
    """Person mentioned in the video."""
    name: str = Field(description="Person's name")
    role: Optional[str] = Field(None, description="Their role or title")
    affiliation: Optional[str] = Field(None, description="Organization or company")

class CommunityMention(BaseModel):
    """Community, event, or organization mentioned."""
    name: str = Field(description="Community or organization name")
    type: Literal["discord", "community", "event", "organization"] = Field(description="Type of mention")
    url: Optional[str] = Field(None, description="URL if available")

class VideoAnalysisResponse(BaseModel):
    """Master structured response for comprehensive video analysis."""
    
    # Core analysis components
    tldr: str = Field(description="1-2 paragraph summary of the video")
    key_audience: str = Field(description="Who would benefit most from this content")
    
    # Structured extractions
    core_topics: List[CoreTopic] = Field(description="3-7 main topics identified")
    lessons_learned: Dict[str, List[str]] = Field(description="Lessons organized by category (technical/business/general)")
    sources_referenced: List[SourceReference] = Field(description="External sources mentioned")
    concepts_mentioned: List[ConceptMention] = Field(description="Key concepts and frameworks")
    people_mentioned: List[PersonMention] = Field(description="People referenced in the video")
    communities_mentioned: List[CommunityMention] = Field(description="Communities, events, organizations")
    
    # Analysis and insights
    detailed_insights: str = Field(description="Extended analysis and implications")
    
    # Confidence tracking
    confidence_scores: Dict[str, float] = Field(description="Confidence per extraction category (0.0-1.0)")

# === Database Storage Model ===

class VideoAnalysisComplete(BaseModel):
    """Complete video analysis result for database storage."""
    
    video_id: str
    
    # Analysis results (from LLM structured outputs)
    tldr: str
    key_audience: str
    core_topics: List[Dict[str, Any]]  # Serialized CoreTopic objects
    lessons_learned: Dict[str, List[str]]
    detailed_insights: str
    sources_referenced: List[Dict[str, Any]]  # Serialized SourceReference objects
    concepts_mentioned: List[Dict[str, Any]]  # Serialized ConceptMention objects
    people_mentioned: List[Dict[str, Any]]  # Serialized PersonMention objects
    communities_mentioned: List[Dict[str, Any]]  # Serialized CommunityMention objects
    metadata_extracted: Dict[str, Any]  # Full video/channel metadata
    
    # Processing tracking
    input_tokens: int  # Track input tokens separately
    output_tokens: int  # Track output tokens separately
    total_tokens: int
    total_cost: float
    total_processing_time_seconds: float
    confidence_scores: Dict[str, float]
    
    # Processing metadata (for future case studies)
    processing_metadata: Optional[Dict[str, Any]] = Field(None, description="Detailed processing info for case studies")
    
    # Model and timing info
    model_name: str = "gemini-3.0-flash"
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

# === Processing Metrics (for case studies) ===

class ProcessingMetrics(BaseModel):
    """Processing metrics for workflow execution tracking."""
    
    workflow_version: str = "1.0"
    extraction_method: str = "single-master-prompt"  # vs "multi-node" for future comparisons
    opik_trace_id: Optional[str] = None
    opik_experiment_id: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Token and cost breakdown
    input_tokens: int
    output_tokens: int
    total_cost: float
    processing_time_seconds: float
    
    # Quality metrics
    confidence_scores: Dict[str, float]
    extraction_completeness: Dict[str, bool]  # Track which sections were successfully extracted
```

**Key Simplifications:**
- **Single file**: Matches your current `models/video.py` pattern
- **Flat structure**: No nested directories
- **Master extraction**: One comprehensive model instead of multiple response types
- **Token tracking**: Separate input/output token fields for analysis
- **Future-ready**: Infrastructure supports case study comparisons later

**Note on Schema Evolution:**
```python
# Future enhancement: Easy to add new fields without breaking existing data
# Example: Add sentiment analysis later
# sentiment_analysis: Optional[Dict[str, Any]] = Field(None, description="Sentiment metrics (future)")
```

---

### Phase 3: LangGraph Agent Implementation

#### 3.1 Create Simplified Agent Structure ✨ UPDATED
**Files (simplified to match your preferences):**
- `src/app/agents/__init__.py`
- `src/app/agents/video_analyzer.py` - Single file with complete workflow, prompts, and nodes
- `src/app/core/opik_manager.py` - Centralized Opik management

#### 3.2 Implement Type-Safe State Management ✨ NEW
**File:** `src/app/agents/video_analyzer/state.py`

```python
"""Type-safe state definition for video analysis workflow."""

from typing_extensions import TypedDict, NotRequired, List, Dict, Any
from datetime import datetime

class VideoAnalysisState(TypedDict):
    """Type-safe state for video analysis workflow."""
    
    # Input data (loaded in first node)
    video_id: str
    video: NotRequired[Dict[str, Any]]  # Video metadata
    transcript: NotRequired[Dict[str, Any]]  # Transcript data
    channel: NotRequired[Dict[str, Any]]  # Channel metadata
    
    # Analysis results (filled by nodes)
    tldr: NotRequired[str]
    key_audience: NotRequired[str]
    core_topics: NotRequired[List[Dict[str, Any]]]
    lessons_learned: NotRequired[Dict[str, List[str]]]
    detailed_insights: NotRequired[str]
    sources_referenced: NotRequired[List[Dict[str, Any]]]
    concepts_mentioned: NotRequired[List[Dict[str, Any]]]
    people_mentioned: NotRequired[List[Dict[str, str]]]
    communities_mentioned: NotRequired[List[Dict[str, str]]]
    
    # Processing tracking
    metrics: NotRequired[Dict[str, Any]]
    confidence_scores: NotRequired[Dict[str, float]]
    errors: NotRequired[List[str]]
```

#### 3.2 Implement Enhanced Opik Prompts (Already covered above)

**Prompt Design Principles:**
- **Structured Output Schema Binding**: Each prompt linked to specific Pydantic response model
- **Automatic Versioning**: Opik tracks all prompt changes
- **Confidence Tracking**: Include confidence scores in all responses  
- **Context-Aware**: Use previous node outputs to enhance subsequent prompts
- **Token Optimization**: Truncate inputs appropriately for model limits

#### 3.3 Implement Enhanced LangGraph Nodes with Structured Outputs ✨ NEW
**File:** `src/app/agents/video_analyzer/nodes.py`

**Complete Implementation Example:**
```python
"""Enhanced LangGraph nodes with structured outputs and Opik integration."""

import time
from typing import Dict, Any
import opik
from opik import track
from app.client.gemini_client import GeminiClient
from app.models.video_analysis.schemas import TLDRResponse, CoreTopicsResponse
from app.models.video_analysis.metrics import NodeExecutionMetrics
from app.agents.video_analyzer.prompts import VideoAnalysisPrompts
from app.agents.video_analyzer.state import VideoAnalysisState
from app.repositories.video_repository import VideoRepository
from app.repositories.channel_repository import ChannelRepository
from app.core.logging import logger

@track(name="extract_tldr_node")
async def extract_tldr_node(state: VideoAnalysisState) -> VideoAnalysisState:
    """Extract TLDR using Gemini with structured Pydantic output."""
    
    logger.info(f"Extracting TLDR for video {state['video_id']}")
    
    try:
        # Get prompt from Opik
        chat_prompt = VideoAnalysisPrompts.get_tldr_prompt()
        
        # Format with variables  
        formatted_messages = chat_prompt.format(
            variables={
                "title": state["video"]["title"],
                "description": state["video"]["description"] or "",
                "transcript": state["transcript"]["text"][:8000]  # Truncate for token limits
            }
        )
        
        # Create structured LLM with Pydantic model
        gemini_client = GeminiClient()
        structured_llm = gemini_client.with_structured_output(TLDRResponse)
        
        # Track timing and make LLM call
        start_time = time.time()
        response: TLDRResponse = await structured_llm.ainvoke(formatted_messages)
        processing_time = time.time() - start_time
        
        # Calculate metrics
        input_tokens = gemini_client.calculate_tokens(str(formatted_messages))
        output_tokens = gemini_client.calculate_tokens(response.tldr)
        cost = gemini_client.calculate_cost(input_tokens, output_tokens)
        
        # Update state with structured response
        state["tldr"] = response.tldr
        state["key_audience"] = response.key_audience
        state.setdefault("confidence_scores", {})["tldr"] = response.confidence
        
        # Track metrics
        node_metrics = NodeExecutionMetrics(
            node_name="extract_tldr",
            tokens_input=input_tokens,
            tokens_output=output_tokens,
            cost_usd=cost,
            processing_time_seconds=processing_time,
            confidence_scores={"tldr": response.confidence},
            status="success",
            prompt_name="video-tldr-extraction"
        )
        
        # Add to Opik trace context
        opik.get_current_span().update(
            metadata={
                "prompt_name": "video-tldr-extraction", 
                "confidence": response.confidence,
                "tokens": input_tokens + output_tokens,
                "cost_usd": cost
            },
            prompts=[chat_prompt]
        )
        
        state.setdefault("metrics", {"nodes": []})["nodes"].append(node_metrics)
        
        logger.info(
            f"TLDR extracted: {input_tokens + output_tokens} tokens, "
            f"${cost:.4f}, {processing_time:.2f}s, confidence: {response.confidence:.2f}"
        )
        
        return state
        
    except Exception as e:
        logger.error(f"Failed to extract TLDR: {e}")
        
        # Track error in metrics
        error_metrics = NodeExecutionMetrics(
            node_name="extract_tldr",
            tokens_input=0,
            tokens_output=0,
            cost_usd=0.0,
            processing_time_seconds=0.0,
            status="failed",
            error=str(e),
            prompt_name="video-tldr-extraction"
        )
        
        state.setdefault("metrics", {"nodes": []})["nodes"].append(error_metrics)
        state.setdefault("errors", []).append(f"extract_tldr: {e}")
        
        raise  # Re-raise to fail the workflow

@track(name="extract_core_topics_node") 
async def extract_core_topics_node(state: VideoAnalysisState) -> VideoAnalysisState:
    """Extract core topics using structured output."""
    
    logger.info(f"Extracting core topics for video {state['video_id']}")
    
    # Similar pattern to extract_tldr_node but with CoreTopicsResponse
    # ... implementation follows same pattern
    
    return state

# ... Additional nodes following same pattern
```

**Enhanced Node Pattern:**
1. **Opik Tracking**: `@track` decorator for automatic span creation
2. **Type Safety**: Use `VideoAnalysisState` TypedDict for state management
3. **Structured Outputs**: `llm.with_structured_output(PydanticModel)` for reliable parsing
4. **Prompt Integration**: Use Opik ChatPrompt with automatic versioning
5. **Comprehensive Metrics**: Track tokens, cost, time, confidence scores
6. **Error Handling**: Structured error tracking with failed status
7. **Context Updates**: Add prompts and metadata to Opik spans
8. **Detailed Logging**: Loguru integration with structured information

#### 3.4 Implement Enhanced LangGraph Workflow ✨ NEW
**File:** `src/app/agents/video_analyzer/graph.py`

**Enhanced Workflow Definition:**
```python
"""Enhanced video analysis workflow with type safety and Opik integration."""

from langgraph.graph import StateGraph, START, END
from app.core.opik_manager import opik_manager
from app.agents.video_analyzer.state import VideoAnalysisState
from app.agents.video_analyzer.nodes import (
    load_context_node,
    extract_tldr_node,
    extract_core_topics_node,
    extract_lessons_node,
    extract_sources_node,
    extract_concepts_node,
    extract_people_communities_node,
    generate_detailed_insights_node,
    save_results_node
)

def create_video_analysis_workflow():
    """Create enhanced video analysis workflow with Opik tracking."""
    
    # Create workflow with type-safe state
    workflow = StateGraph(VideoAnalysisState)
    
    # Add nodes with enhanced implementations
    workflow.add_node("load_context", load_context_node)
    workflow.add_node("extract_tldr", extract_tldr_node)
    workflow.add_node("extract_core_topics", extract_core_topics_node)
    workflow.add_node("extract_lessons", extract_lessons_node)
    workflow.add_node("extract_sources", extract_sources_node)
    workflow.add_node("extract_concepts", extract_concepts_node)
    workflow.add_node("extract_people_communities", extract_people_communities_node)
    workflow.add_node("generate_detailed_insights", generate_detailed_insights_node)
    workflow.add_node("save_results", save_results_node)
    
    # Define sequential edges
    workflow.add_edge(START, "load_context")
    workflow.add_edge("load_context", "extract_tldr")
    workflow.add_edge("extract_tldr", "extract_core_topics")
    workflow.add_edge("extract_core_topics", "extract_lessons")
    workflow.add_edge("extract_lessons", "extract_sources")
    workflow.add_edge("extract_sources", "extract_concepts")
    workflow.add_edge("extract_concepts", "extract_people_communities")
    workflow.add_edge("extract_people_communities", "generate_detailed_insights")
    workflow.add_edge("generate_detailed_insights", "save_results")
    workflow.add_edge("save_results", END)
    
    # Compile workflow
    compiled_workflow = workflow.compile()
    
    # Wrap with Opik tracking using centralized manager
    tracked_workflow = opik_manager.track_workflow(
        compiled_workflow, 
        workflow_name="video-analysis",
        tags=["video", "analysis", "gemini-3.0-flash"]
    )
    
    return tracked_workflow

# Factory function for service integration
def get_video_analysis_workflow():
    """Get configured video analysis workflow instance."""
    return create_video_analysis_workflow()
```

**Key Enhancements:**
- **Type Safety**: Uses `VideoAnalysisState` TypedDict for compile-time checking
- **Centralized Opik**: Uses `opik_manager` for consistent configuration
- **Automatic Tracking**: Workflow wrapped with Opik instrumentation
- **Clean Separation**: Factory function for easy service integration
- **Enhanced Tags**: Proper tagging for filtering in Opik UI

#### 3.5 Centralized Opik Integration (Replaced by App-Level Manager) ✨ UPDATED

**Note:** Individual workflow instrumentation has been replaced by the centralized `OpikManager` approach.

**Integration Points Now Handled By:**
- **App-Level Configuration**: `src/app/core/opik_manager.py` 
- **Node-Level Tracking**: `@track` decorators in each node function
- **Prompt Management**: Opik ChatPrompt integration in prompts.py
- **Workflow Wrapping**: `opik_manager.track_workflow()` in graph.py

**Benefits of Centralized Approach:**
- **Consistent Configuration**: All workflows use same project settings
- **Reduced Duplication**: No need for per-workflow instrumentation code
- **Easier Maintenance**: Single place to update Opik configuration
- **Better Organization**: Clear separation between business logic and observability

---

### Phase 4: Enhanced Gemini 3.0 Flash Client Integration ✨ NEW

#### 4.1 Create Enhanced Gemini Client with Structured Output Support
**File:** `src/app/client/gemini_client.py`

**Purpose:** Enhanced client wrapper for Gemini 3.0 Flash with structured output support

**Complete Implementation:**
```python
"""Enhanced Gemini client with structured output support for 3.0 Flash."""

import google.generativeai as genai
from pydantic import BaseModel
from typing import Type, Union, List, Dict, Any
from app.config.settings import settings
from app.core.logging import logger

class GeminiResponse(BaseModel):
    """Standard Gemini API response model."""
    text: str
    tokens_input: int
    tokens_output: int
    model: str
    finish_reason: str

class GeminiClient:
    """Enhanced Gemini client with structured output support for 3.0 Flash."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.google_api_key
        genai.configure(api_key=self.api_key)
        self.model_name = "gemini-3.0-flash"  # Updated to 3.0
        
        # Initialize model
        self.model = genai.GenerativeModel(self.model_name)
        
        logger.info(f"Initialized GeminiClient with model: {self.model_name}")
    
    def with_structured_output(self, schema: Type[BaseModel]):
        """Create structured output client for Pydantic model validation."""
        
        class StructuredGeminiClient:
            def __init__(self, client: 'GeminiClient', response_schema: Type[BaseModel]):
                self.client = client
                self.response_schema = response_schema
            
            async def ainvoke(self, messages: Union[str, List[Dict]]) -> BaseModel:
                """Generate structured response using Pydantic schema."""
                
                # Convert messages to prompt
                if isinstance(messages, list):
                    prompt = self._format_chat_messages(messages)
                else:
                    prompt = messages
                
                # Add schema instruction to prompt
                schema_instruction = f"""
                
                IMPORTANT: Respond with valid JSON that matches this exact schema:
                {self.response_schema.model_json_schema()}
                
                Your response must be valid JSON only, no additional text.
                """
                
                full_prompt = prompt + schema_instruction
                
                # Generate response
                response = await self.client.model.generate_content_async(full_prompt)
                
                # Parse and validate with Pydantic
                try:
                    response_text = response.text.strip()
                    if response_text.startswith('```json'):
                        response_text = response_text.replace('```json', '').replace('```', '').strip()
                    
                    return self.response_schema.model_validate_json(response_text)
                except Exception as e:
                    logger.error(f"Failed to parse structured response: {e}")
                    logger.error(f"Raw response: {response.text}")
                    raise
            
            def _format_chat_messages(self, messages: List[Dict]) -> str:
                """Convert chat messages to single prompt string."""
                formatted = ""
                for msg in messages:
                    role = msg["role"].upper()
                    content = msg["content"]
                    formatted += f"{role}: {content}\n\n"
                return formatted
        
        return StructuredGeminiClient(self, schema)
    
    async def generate_content(self, prompt: str) -> GeminiResponse:
        """Generate content with standard response format."""
        response = await self.model.generate_content_async(prompt)
        
        # Calculate approximate tokens (implement properly based on Gemini tokenization)
        input_tokens = self.calculate_tokens(prompt)
        output_tokens = self.calculate_tokens(response.text)
        
        return GeminiResponse(
            text=response.text,
            tokens_input=input_tokens,
            tokens_output=output_tokens,
            model=self.model_name,
            finish_reason=response.finish_reason if hasattr(response, 'finish_reason') else 'stop'
        )
    
    def calculate_tokens(self, text: str) -> int:
        """Estimate token count (implement proper tokenization for Gemini)."""
        # Rough approximation: 1 token ≈ 4 characters for most text
        # TODO: Use proper Gemini tokenization when available
        return len(text) // 4
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on Gemini 3.0 Flash pricing."""
        # Updated rates for Gemini 3.0 Flash (update with current pricing)
        INPUT_PRICE_PER_1K = 0.000075   # Example rate - update with actual
        OUTPUT_PRICE_PER_1K = 0.0003    # Example rate - update with actual
        
        input_cost = (input_tokens / 1000) * INPUT_PRICE_PER_1K
        output_cost = (output_tokens / 1000) * OUTPUT_PRICE_PER_1K
        
        return input_cost + output_cost

# Factory function for dependency injection
def get_gemini_client() -> GeminiClient:
    """Get configured Gemini client instance."""
    return GeminiClient()
```

**Key Features:**
- **Structured Output Support**: Direct Pydantic model validation
- **Async Support**: Full async/await compatibility  
- **Cost Calculation**: Updated pricing for Gemini 3.0 Flash
- **Error Handling**: Robust parsing and validation
- **Chat Message Support**: Convert OpenAI-style messages to Gemini format
- **Token Estimation**: Approximation with plan for proper tokenization

---

### Phase 5: Repository Layer

#### 5.1 Create Video Analysis Repository
**File:** `src/app/repositories/video_analysis_repository.py`

**Class:** `VideoAnalysisRepository`
**Methods:**
- `save_analysis(analysis: VideoAnalysis) -> bool`
- `get_analysis(video_id: str) -> Optional[VideoAnalysis]`
- `has_analysis(video_id: str) -> bool`
- `update_analysis_metrics(video_id: str, metrics: ProcessingMetadata) -> bool`

**Implementation Details:**
- Use upsert pattern (idempotent)
- Convert Pydantic models to database format
- Handle JSONB serialization
- Update `videos.summary_generated` and `videos.tags_extracted` flags

**Database Operations:**
- Insert/update `video_processed_data` table
- Update `videos` table status flags
- Handle JSONB field serialization

---

### Phase 6: Service Layer

#### 6.1 Create Video Analysis Service
**File:** `src/app/services/video_analysis_service.py`

**Class:** `VideoAnalysisService`
**Dependencies:**
- `VideoAnalysisRepository`
- `VideoRepository` (for fetching video/transcript)
- `ChannelRepository` (for fetching channel metadata)
- `GeminiClient`
- LangGraph workflow instance

**Methods:**
- `analyze_video(video_id: str) -> VideoAnalysis`
- `has_analysis(video_id: str) -> bool`
- `get_analysis(video_id: str) -> Optional[VideoAnalysis]`

**Implementation Flow:**
1. Check if analysis already exists (idempotency)
2. Load video context (video + transcript + channel)
3. Initialize LangGraph workflow
4. Execute workflow with context
5. Collect results and metrics
6. Save to database
7. Return `VideoAnalysis` model

**Error Handling:**
- Catch node failures
- Track which node failed
- Save partial results if desired (future enhancement)
- Update video status appropriately

---

### Phase 7: Orchestrator Integration

#### 7.1 Update Orchestrator Service
**File:** `src/app/services/orchestrator.py`

**Update:** `_process_videos()` method

**Current Logic (lines 202-281):**
```python
async def _process_videos(self, target_date: date, transcript_result: Optional[TranscriptExtractionResult] = None) -> ProcessingResult:
    # Get videos that need processing
    processing_queue = self.get_processing_queue(target_date)
    
    for video in processing_queue:
        # Update status to PROCESSING
        # Placeholder: call analysis service
        # Update status to PROCESSED
```

**New Logic:**
```python
async def _process_videos(self, target_date: date, transcript_result: Optional[TranscriptExtractionResult] = None) -> ProcessingResult:
    started_at = datetime.now(timezone.utc)
    errors = []
    analyses_completed = 0
    
    # Initialize video analysis service
    analysis_service = VideoAnalysisService()
    
    # Get videos that need processing (status = COLLECTED, transcript_fetched = True)
    processing_queue = self.get_processing_queue(target_date)
    
    # Filter to only videos with transcripts
    videos_with_transcripts = [
        v for v in processing_queue 
        if self.video_repo.has_transcript(v.id)
    ]
    
    for video in videos_with_transcripts:
        try:
            # Update status to PROCESSING
            self.video_repo.update_status(
                video.id,
                VideoProcessingStatus.PROCESSING,
                processed_at=datetime.now(timezone.utc)
            )
            
            # Analyze video
            analysis = await analysis_service.analyze_video(video.id)
            
            if analysis:
                analyses_completed += 1
                # Update status to PROCESSED
                self.video_repo.update_status(
                    video.id,
                    VideoProcessingStatus.PROCESSED,
                    processed_at=datetime.now(timezone.utc)
                )
            else:
                raise Exception("Analysis returned None")
                
        except Exception as e:
            error_msg = f"Failed to process video {video.id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)
            
            # Mark as failed
            self.video_repo.update_status(
                video.id,
                VideoProcessingStatus.FAILED,
                processing_error=str(e)
            )
    
    completed_at = datetime.now(timezone.utc)
    
    return ProcessingResult(
        videos_processed=len(videos_with_transcripts),
        transcripts_extracted=transcript_result.transcripts_extracted if transcript_result else 0,
        analyses_completed=analyses_completed,
        errors=errors,
        started_at=started_at,
        completed_at=completed_at,
    )
```

**Key Changes:**
- Import `VideoAnalysisService`
- Filter videos to only those with transcripts
- Call `analysis_service.analyze_video()` for each video
- Track `analyses_completed` count
- Handle errors appropriately

---

### Phase 8: API Endpoints

#### 8.1 Add Single Video Processing Endpoint
**File:** `src/app/api/orchestrator.py`

**New Endpoints:**
```python
@router.post("/process-video/{video_id}")
async def process_single_video(video_id: str) -> VideoAnalysisResponse:
    """Process a single video through the analysis pipeline."""
    # Validate video exists
    # Check if already processed
    # Call VideoAnalysisService
    # Return response

@router.post("/process-video/{video_id}/async")
async def process_single_video_async(video_id: str, background_tasks: BackgroundTasks):
    """Process a single video asynchronously."""
    # Similar to async endpoints above
```

**Response Models:**
```python
class VideoAnalysisResponse(BaseModel):
    message: str
    video_id: str
    status: str
    analysis: Optional[VideoAnalysis] = None
    processing_time_seconds: Optional[float] = None
    total_cost: Optional[float] = None
    total_tokens: Optional[int] = None
```

---

### Phase 9: Configuration Updates

#### 9.1 Update Settings
**File:** `src/app/config/settings.py`

**Add Configuration:**
```python
# Gemini Configuration
google_api_key: str = Field(..., alias="GOOGLE_API_KEY")

# Opik Configuration
opik_api_key: Optional[str] = Field(default=None, alias="OPIK_API_KEY")
opik_project_name: Optional[str] = Field(default=None, alias="OPIK_PROJECT_NAME")
opik_workspace: Optional[str] = Field(default=None, alias="OPIK_WORKSPACE")

# Video Analysis Configuration  
analysis_model_name: str = Field(default="gemini-3.0-flash", alias="ANALYSIS_MODEL_NAME")  # Updated to 3.0
analysis_timeout_seconds: int = Field(default=300, alias="ANALYSIS_TIMEOUT_SECONDS")
```

#### 9.2 Update Environment Example
**File:** `.env.example`

**Already Updated:**
- `GOOGLE_API_KEY=`
- `OPIK_API_KEY=`
- `OPIK_PROJECT_NAME=`
- `OPIK_WORKSPACE=`

**Add (if needed):**
```bash
ANALYSIS_MODEL_NAME=gemini-3.0-flash  # Updated to 3.0
ANALYSIS_TIMEOUT_SECONDS=300
```

---

### Phase 10: Dependencies ✨ UPDATED

#### 10.1 Required Dependencies to Add

**Add these to your `pyproject.toml` dependencies array:**

```toml
# LangGraph and LangChain (for workflow orchestration)
"langgraph",              # Latest stable version - for workflow management
"langchain-core",         # Required for LangGraph compatibility

# Gemini Integration (for LLM API)
"google-generativeai",    # Latest version - Gemini 3.0 Flash SDK

# Opik (for observability and prompt management)  
"opik",                   # Latest version - for tracing and prompt versioning

# Type Safety (for TypedDict support)
"typing-extensions",      # Latest version - for enhanced type safety
```

**Installation command:**
```bash
# Add to your existing dependencies and run:
pip install langgraph langchain-core google-generativeai opik typing-extensions
```

**Note:** Use latest stable versions during implementation - the plan avoids pinning specific versions to prevent conflicts with your existing dependencies.

---

## Implementation Checklist ✨ ENHANCED

### Core Infrastructure
- [ ] **Create centralized Opik manager** (`src/app/core/opik_manager.py`)
- [ ] **Update settings with Opik configuration** (`src/app/config/settings.py`) 
- [ ] **Create migration file** for `video_processed_data` schema updates

### Enhanced Data Models
- [ ] **Create domain-organized models directory** (`src/app/models/video_analysis/`)
  - [ ] **LLM response schemas** (`schemas.py`) for structured outputs
  - [ ] **Database entity models** (`responses.py`) for storage
  - [ ] **Processing metrics models** (`metrics.py`) for tracking
- [ ] **Update existing models** to use new namespace

### Gemini 3.0 Flash Client
- [ ] **Create enhanced Gemini client** (`src/app/client/gemini_client.py`)
- [ ] **Implement structured output support** with Pydantic validation
- [ ] **Add cost calculation** for Gemini 3.0 Flash pricing
- [ ] **Add token estimation** and proper error handling

### LangGraph Agent with Enhanced Features
- [ ] **Create enhanced agent directory** (`src/app/agents/video_analyzer/`)
  - [ ] **Type-safe state definition** (`state.py`) with TypedDict
  - [ ] **Opik ChatPrompt integration** (`prompts.py`) with versioning
  - [ ] **Enhanced nodes** (`nodes.py`) with `@track` decorators and structured outputs
  - [ ] **Enhanced workflow** (`graph.py`) with centralized Opik tracking
- [ ] **Implement complete TLDR node** as template for other nodes
- [ ] **Add comprehensive error handling** and metrics tracking

### Repository Layer
- [ ] **Create VideoAnalysisRepository** (`src/app/repositories/video_analysis_repository.py`)
- [ ] **Implement save/retrieve methods** with proper JSONB handling
- [ ] **Add upsert patterns** for idempotent operations

### Service Layer  
- [ ] **Create VideoAnalysisService** (`src/app/services/video_analysis_service.py`)
- [ ] **Integrate enhanced LangGraph workflow** with proper error handling
- [ ] **Add comprehensive logging** and metrics collection

### Orchestrator Integration
- [ ] **Update ContentOrchestrator** `_process_videos()` method
- [ ] **Add VideoAnalysisService integration** with proper filtering
- [ ] **Update status tracking** and error handling

### API Layer
- [ ] **Add single video processing endpoints** in `src/app/api/orchestrator.py`
- [ ] **Create enhanced response models** with detailed metrics
- [ ] **Add async processing support** with proper error handling

### Configuration & Dependencies
- [ ] **Add required dependencies** to pyproject.toml (LangGraph, Opik, google-generativeai, typing-extensions)
- [ ] **Update .env.example** with Gemini 3.0 and Opik configuration
- [ ] **Verify dependency compatibility** and version constraints

---

## Key Design Decisions Summary

### 1. Master Prompt Approach ✨ UPDATED
- **Decision**: Single comprehensive extraction instead of sequential nodes
- **Rationale**: 87.5% cost reduction (1 API call vs 8), faster execution, simpler debugging
- **Future**: Can split into individual nodes for prompt comparison case studies later

### 2. Prompt Management ✨ UPDATED
- **Decision**: Use Opik ChatPrompt for centralized management
- **Rationale**: Automatic versioning, team collaboration, experiment linking
- **Implementation**: ChatPrompt classes with structured output schema binding

### 3. Cost Tracking
- **Decision**: Track per-node and aggregate metrics
- **Storage**: Per-node in `processing_metadata`, aggregate in dedicated columns
- **Calculation**: Based on Gemini 3.0 Flash pricing

### 4. Error Handling
- **Decision**: Fail-fast (if any node fails, entire workflow fails)
- **Rationale**: Ensures data consistency
- **Future**: Can add partial result saving

### 5. Idempotency
- **Decision**: Check if analysis exists before processing
- **Mechanism**: Query `video_processed_data` table
- **Benefit**: Safe to re-run pipeline

### 6. Testing Strategy
- **Decision**: No tests for v1
- **Rationale**: Focus on implementation first
- **Future**: Add unit and integration tests

---

## Success Metrics

### Functional Metrics
- [ ] Successfully analyze videos with transcripts
- [ ] Extract all required fields (TLDR, topics, lessons, sources, etc.)
- [ ] Store complete analysis in database
- [ ] Track cost and time metrics accurately

### Technical Metrics
- [ ] Process videos sequentially without errors
- [ ] Opik instrumentation captures all LLM calls
- [ ] Cost tracking accurate within 5% of actual
- [ ] Processing time tracked per node and total

### Data Quality Metrics
- [ ] Structured JSONB fields parse correctly
- [ ] All video metadata preserved
- [ ] Analysis results are complete and consistent

---

## Next Steps After Implementation

1. **Monitor & Iterate**
   - Review Opik traces for prompt effectiveness
   - Adjust prompts based on results
   - Optimize cost by reducing token usage where possible

2. **Enhancements**
   - Add parallel processing for multiple videos
   - Implement partial result saving on node failures
   - Add retry logic for transient failures
   - Implement prompt versioning system

3. **Testing**
   - Add unit tests for nodes
   - Add integration tests for workflow
   - Add end-to-end tests for full pipeline

4. **Documentation**
   - Document prompt design decisions
   - Create runbook for common issues
   - Document cost optimization strategies

---

## File Path Summary

### New Files ✨ UPDATED (Simplified Structure)
```
src/app/core/
  opik_manager.py  # NEW: Centralized Opik management

src/app/agents/
  __init__.py
  video_analyzer.py  # NEW: Single file with complete workflow (matches your pattern)

src/app/client/
  gemini_client.py  # Enhanced with structured output support for 3.0 Flash

src/app/models/
  video_analysis.py  # NEW: All models in single file (matches current pattern)

src/app/repositories/
  video_analysis_repository.py  # Enhanced with proper JSONB handling

src/app/services/
  video_analysis_service.py  # Enhanced with comprehensive error handling

supabase/migrations/
  YYYYMMDDHHMMSS_video_analysis_schema.sql  # Enhanced with input/output token tracking
```

### Modified Files
```
src/app/services/orchestrator.py  # Update _process_videos()
src/app/api/orchestrator.py       # Add single video endpoints
src/app/config/settings.py        # Add Gemini/Opik config
.env.example                      # Add GOOGLE_API_KEY, OPIK_* config
```

---

## Summary ✨ ENHANCED

This **enhanced implementation plan** provides a comprehensive roadmap for building Phase 3 video analysis with:

### 🚀 **Core Technologies**
- **LangGraph**: Sequential workflow with type-safe state management
- **Gemini 3.0 Flash**: Latest model with enhanced structured output capabilities
- **Opik**: Comprehensive observability with centralized configuration, prompt management, and experiment tracking
- **Pydantic**: Robust data validation and structured outputs

### 🎯 **Key Improvements Over Original Plan**
1. **Master Prompt Approach**: 87.5% cost reduction with single API call vs 8 sequential calls
2. **Simplified Architecture**: Single-file approach matching existing codebase patterns
3. **Token Tracking**: Separate input/output token fields for detailed cost analysis
4. **Future-Ready Infrastructure**: Easy to split into multi-node for case studies later
5. **Structured Outputs**: Direct Pydantic model validation eliminates JSON parsing errors
6. **Centralized Opik Management**: App-level configuration reduces duplication

### 🛠 **Implementation Benefits**
- **Reliability**: Structured outputs and proper error handling
- **Observability**: Rich Opik integration with prompt versioning and experiment linking
- **Maintainability**: Centralized configuration and clean architecture
- **Scalability**: App-level design supports multiple workflows and agents
- **Team Collaboration**: Shared prompts and experiments through Opik platform

### 📊 **Expected Outcomes**
- **High-Quality Extractions**: Structured outputs ensure consistent, valid responses
- **Rich Observability**: Complete visibility into workflow execution and performance
- **Cost Optimization**: Accurate tracking enables optimization opportunities  
- **Team Efficiency**: Centralized prompt management and experiment tracking

This implementation follows established architectural patterns while introducing modern best practices for LLM application development, observability, and team collaboration.

