# Video Analysis Implementation Plan (Phase 3)

## Overview
This document outlines the implementation of **Phase 3: Video Processing** using LangGraph and Gemini Flash 3. The system will analyze video transcripts to extract structured insights including TLDR, core topics, lessons learned, sources, concepts, and detailed analysis. All processing will be instrumented with Opik for observability, and cost/time metrics will be tracked at both per-step and aggregate levels.

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
- Integration with Gemini Flash 3
- Opik instrumentation for observability
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

### 1. LangGraph Workflow Structure

**File:** `src/app/agents/video_analyzer/graph.py`

Sequential workflow with the following nodes:

```
START
  ↓
[Load Context] → Fetch video metadata + transcript + channel info
  ↓
[Extract TLDR] → Generate concise summary (1-2 paragraphs)
  ↓
[Extract Core Topics] → Identify main topics, categorize them
  ↓
[Extract Lessons] → Bucket lessons by category (technical, business, etc.)
  ↓
[Extract Sources] → Papers, books, podcasts, links mentioned
  ↓
[Extract Concepts] → Key ideas and concepts discussed
  ↓
[Extract People & Communities] → Names, roles, discords, events
  ↓
[Generate Detailed Insights] → Extended analysis section
  ↓
[Assemble Metadata] → Preserve all video metadata
  ↓
[Save Results] → Store complete analysis to database
  ↓
END
```

**Key Design Principles:**
- **Sequential Processing**: No parallel nodes (simplifies error handling and cost tracking)
- **State Management**: Each node receives and returns state dict with video context + extracted data
- **Error Handling**: If any node fails, entire workflow fails (can be enhanced later for partial results)
- **Idempotency**: Workflow can be re-run safely (upsert pattern in repository)

### 2. Prompt Storage Strategy

**Decision: Store prompts in agent file for v1**

**File:** `src/app/agents/video_analyzer/prompts.py`

**Rationale:**
- **V1 Simplicity**: Keep prompts close to code for easy iteration
- **Version Control**: Git tracks prompt changes naturally
- **Future Migration**: Can migrate to Opik prompt versioning later without code changes

**Structure:**
```python
# Each prompt as a function that takes context and returns formatted prompt
def get_tldr_prompt(video_title: str, transcript: str, description: str) -> str:
    """Generate TLDR extraction prompt."""
    ...

def get_core_topics_prompt(transcript: str, tldr: str) -> str:
    """Generate core topics extraction prompt."""
    ...
```

**Future Consideration:**
- Opik prompt versioning can be added later
- Consider prompt registry pattern if prompts grow complex

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
ALTER TABLE video_processed_data ADD COLUMN IF NOT EXISTS total_tokens INTEGER;
ALTER TABLE video_processed_data ADD COLUMN IF NOT EXISTS total_cost DECIMAL(10, 6);
ALTER TABLE video_processed_data ADD COLUMN IF NOT EXISTS total_processing_time_seconds DECIMAL(10, 3);
ALTER TABLE video_processed_data ADD COLUMN IF NOT EXISTS processing_metadata JSONB;  -- Per-node details
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

### 4. Opik Integration

**Purpose:** Observability for LangGraph agent execution

**Configuration:**
- Environment variables: `OPIK_API_KEY`, `OPIK_PROJECT_NAME`, `OPIK_WORKSPACE`
- Initialize Opik client in agent initialization
- Instrument each LangGraph node with Opik tracing

**What to Track:**
- Each node execution (start/end time, tokens, cost)
- LLM calls (prompt, response, metadata)
- Errors and retries
- Workflow-level metrics

**File:** `src/app/agents/video_analyzer/opik_instrumentation.py`

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

### Phase 2: Data Models

#### 2.1 Create Video Analysis Models
**File:** `src/app/models/video_analysis.py`

**Models:**
```python
class CoreTopic(BaseModel):
    topic: str
    category: str  # e.g., "technical", "business", "philosophy"
    importance: str  # "high", "medium", "low"

class SourceReference(BaseModel):
    type: str  # "paper", "book", "podcast", "link", "discord", "community", "event"
    title: str
    url: Optional[str] = None
    author: Optional[str] = None

class Concept(BaseModel):
    concept: str
    description: str
    relevance: str  # Brief relevance note

class PersonMentioned(BaseModel):
    name: str
    role: Optional[str] = None
    affiliation: Optional[str] = None

class CommunityMentioned(BaseModel):
    type: str  # "discord", "community", "event"
    name: str
    url: Optional[str] = None

class NodeExecutionMetrics(BaseModel):
    node_name: str
    tokens_input: int
    tokens_output: int
    cost_usd: float
    processing_time_seconds: float
    status: str  # "success", "failed"
    error: Optional[str] = None

class ProcessingMetadata(BaseModel):
    nodes: List[NodeExecutionMetrics]
    workflow_version: str
    prompt_versions: Dict[str, str]
    opik_trace_id: Optional[str] = None

class VideoAnalysis(BaseModel):
    video_id: str
    tldr: str
    core_topics: List[CoreTopic]
    lessons_learned: Dict[str, List[str]]  # Category -> list of lessons
    detailed_insights: str
    sources_referenced: List[SourceReference]
    concepts_mentioned: List[Concept]
    people_mentioned: List[PersonMentioned]
    communities_mentioned: List[CommunityMentioned]
    metadata_extracted: Dict[str, Any]  # Full video/channel metadata
    total_tokens: int
    total_cost: float
    total_processing_time_seconds: float
    processing_metadata: ProcessingMetadata
    model_name: str = "gemini-2.0-flash-exp"
    processed_at: datetime
```

---

### Phase 3: LangGraph Agent Implementation

#### 3.1 Create Agent Directory Structure
**Files:**
- `src/app/agents/__init__.py`
- `src/app/agents/video_analyzer/__init__.py`
- `src/app/agents/video_analyzer/graph.py` - Main workflow definition
- `src/app/agents/video_analyzer/nodes.py` - Individual node implementations
- `src/app/agents/video_analyzer/prompts.py` - Prompt templates
- `src/app/agents/video_analyzer/models.py` - Agent-specific models
- `src/app/agents/video_analyzer/opik_instrumentation.py` - Opik integration

#### 3.2 Implement Prompts
**File:** `src/app/agents/video_analyzer/prompts.py`

**Prompt Functions:**
- `get_tldr_prompt()` - Generate TLDR (1-2 paragraphs)
- `get_core_topics_prompt()` - Extract topics with categories
- `get_lessons_learned_prompt()` - Extract lessons by category
- `get_sources_prompt()` - Extract papers, books, podcasts, links
- `get_concepts_prompt()` - Extract key concepts and ideas
- `get_people_communities_prompt()` - Extract people, discords, communities, events
- `get_detailed_insights_prompt()` - Generate extended analysis

**Prompt Design Principles:**
- Use structured output (JSON schema) for reliable extraction
- Include examples in prompts where helpful
- Keep prompts focused and specific
- Version prompts (store version in processing_metadata)

#### 3.3 Implement LangGraph Nodes
**File:** `src/app/agents/video_analyzer/nodes.py`

**Node Functions:**
```python
async def load_context_node(state: dict) -> dict:
    """Load video metadata, transcript, and channel info."""
    # Fetch from repositories
    # Return state with context loaded

async def extract_tldr_node(state: dict) -> dict:
    """Extract TLDR summary."""
    # Call Gemini with TLDR prompt
    # Track metrics (tokens, time, cost)
    # Return state with tldr added

async def extract_core_topics_node(state: dict) -> dict:
    """Extract core topics with categories."""
    # Call Gemini with core topics prompt
    # Parse structured JSON response
    # Track metrics
    # Return state with core_topics added

# ... similar for other nodes
```

**Node Pattern:**
1. Start timer
2. Prepare prompt from context
3. Call Gemini API (with Opik instrumentation)
4. Parse response (structured JSON)
5. Calculate metrics (tokens, cost, time)
6. Update state
7. Log metrics
8. Return updated state

#### 3.4 Implement LangGraph Workflow
**File:** `src/app/agents/video_analyzer/graph.py`

**Workflow Definition:**
```python
from langgraph.graph import StateGraph, END

def create_video_analysis_graph() -> StateGraph:
    """Create LangGraph workflow for video analysis."""
    workflow = StateGraph(dict)  # State is a dict
    
    # Add nodes
    workflow.add_node("load_context", load_context_node)
    workflow.add_node("extract_tldr", extract_tldr_node)
    workflow.add_node("extract_core_topics", extract_core_topics_node)
    workflow.add_node("extract_lessons", extract_lessons_node)
    workflow.add_node("extract_sources", extract_sources_node)
    workflow.add_node("extract_concepts", extract_concepts_node)
    workflow.add_node("extract_people_communities", extract_people_communities_node)
    workflow.add_node("generate_detailed_insights", generate_detailed_insights_node)
    workflow.add_node("assemble_metadata", assemble_metadata_node)
    
    # Define edges (sequential)
    workflow.set_entry_point("load_context")
    workflow.add_edge("load_context", "extract_tldr")
    workflow.add_edge("extract_tldr", "extract_core_topics")
    workflow.add_edge("extract_core_topics", "extract_lessons")
    workflow.add_edge("extract_lessons", "extract_sources")
    workflow.add_edge("extract_sources", "extract_concepts")
    workflow.add_edge("extract_concepts", "extract_people_communities")
    workflow.add_edge("extract_people_communities", "generate_detailed_insights")
    workflow.add_edge("generate_detailed_insights", "assemble_metadata")
    workflow.add_edge("assemble_metadata", END)
    
    return workflow.compile()
```

#### 3.5 Implement Opik Instrumentation
**File:** `src/app/agents/video_analyzer/opik_instrumentation.py`

**Functions:**
- `initialize_opik()` - Setup Opik client
- `instrument_node()` - Decorator/wrapper for node execution tracking
- `log_llm_call()` - Log individual LLM calls with Opik

**Integration Points:**
- Wrap each node execution
- Log each Gemini API call
- Track workflow-level metrics

---

### Phase 4: Gemini Client Integration

#### 4.1 Create Gemini Client
**File:** `src/app/client/gemini_client.py`

**Purpose:** Thin client wrapper for Gemini API calls

**Class:** `GeminiClient`
**Methods:**
- `__init__(api_key: str)` - Initialize with API key from settings
- `generate_content(prompt: str, model: str = "gemini-2.0-flash-exp") -> GeminiResponse`
- `generate_structured_content(prompt: str, response_schema: dict, model: str) -> dict`

**Response Model:**
```python
class GeminiResponse(BaseModel):
    text: str
    tokens_input: int
    tokens_output: int
    model: str
    finish_reason: str
```

**Cost Calculation:**
- Use Gemini Flash 3 pricing (store in constants)
- Calculate cost: `(input_tokens * input_price) + (output_tokens * output_price)`

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
analysis_model_name: str = Field(default="gemini-2.0-flash-exp", alias="ANALYSIS_MODEL_NAME")
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
ANALYSIS_MODEL_NAME=gemini-2.0-flash-exp
ANALYSIS_TIMEOUT_SECONDS=300
```

---

### Phase 10: Dependencies

#### 10.1 Update pyproject.toml
**File:** `pyproject.toml`

**Add Dependencies:**
```toml
"langgraph>=0.2.0",
"langchain-core>=0.3.0",  # For LangGraph compatibility
"google-generativeai>=0.8.0",  # Gemini SDK (or use langchain-google-genai)
```

**Note:** Check if `langchain-google-genai` already provides Gemini integration

---

## Implementation Checklist

### Database & Models
- [ ] Create migration file for `video_processed_data` schema updates
- [ ] Create `VideoAnalysis` models (`src/app/models/video_analysis.py`)
- [ ] Define JSONB field structures

### LangGraph Agent
- [ ] Create agent directory structure (`src/app/agents/video_analyzer/`)
- [ ] Implement prompts (`prompts.py`)
- [ ] Implement nodes (`nodes.py`)
- [ ] Create workflow graph (`graph.py`)
- [ ] Add Opik instrumentation (`opik_instrumentation.py`)

### Client Layer
- [ ] Create `GeminiClient` (`src/app/client/gemini_client.py`)
- [ ] Implement cost calculation logic
- [ ] Add structured output support

### Repository Layer
- [ ] Create `VideoAnalysisRepository` (`src/app/repositories/video_analysis_repository.py`)
- [ ] Implement save/retrieve methods
- [ ] Handle JSONB serialization

### Service Layer
- [ ] Create `VideoAnalysisService` (`src/app/services/video_analysis_service.py`)
- [ ] Integrate LangGraph workflow
- [ ] Add error handling

### Orchestrator Integration
- [ ] Update `_process_videos()` method in `ContentOrchestrator`
- [ ] Filter videos with transcripts
- [ ] Call `VideoAnalysisService`
- [ ] Update status tracking

### API Layer
- [ ] Add `/process-video/{video_id}` endpoint
- [ ] Add `/process-video/{video_id}/async` endpoint
- [ ] Create response models

### Configuration
- [ ] Update `Settings` class with Gemini and Opik config
- [ ] Update `.env.example` (already done)
- [ ] Add analysis configuration options

### Dependencies
- [ ] Update `pyproject.toml` with LangGraph dependencies
- [ ] Verify Gemini SDK availability

---

## Key Design Decisions Summary

### 1. Sequential Processing
- **Decision**: No parallel node execution
- **Rationale**: Simplifies error handling, cost tracking, and debugging
- **Future**: Can add parallelization later if needed

### 2. Prompt Storage
- **Decision**: Store prompts in `prompts.py` file
- **Rationale**: Simple for v1, easy to version control
- **Future**: Can migrate to Opik prompt versioning

### 3. Cost Tracking
- **Decision**: Track per-node and aggregate metrics
- **Storage**: Per-node in `processing_metadata`, aggregate in dedicated columns
- **Calculation**: Based on Gemini Flash 3 pricing

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

### New Files
```
src/app/agents/
  __init__.py
  video_analyzer/
    __init__.py
    graph.py
    nodes.py
    prompts.py
    models.py
    opik_instrumentation.py

src/app/client/
  gemini_client.py

src/app/models/
  video_analysis.py

src/app/repositories/
  video_analysis_repository.py

src/app/services/
  video_analysis_service.py

supabase/migrations/
  YYYYMMDDHHMMSS_video_analysis_schema.sql
```

### Modified Files
```
src/app/services/orchestrator.py  # Update _process_videos()
src/app/api/orchestrator.py       # Add single video endpoints
src/app/config/settings.py        # Add Gemini/Opik config
.env.example                      # Add GOOGLE_API_KEY
pyproject.toml                    # Add LangGraph dependencies
```

---

This implementation plan provides a comprehensive roadmap for building Phase 3 video analysis with LangGraph, Gemini Flash 3, and Opik observability, following the established architectural patterns and design principles of the LTAI News project.

