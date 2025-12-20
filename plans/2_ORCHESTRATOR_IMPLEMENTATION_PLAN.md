# LTAI News - Orchestrator Implementation Plan

## Current State Analysis

### ✅ What's Already Implemented

**Models & Data Layer**
- `Video` model with processing status enum (collected, processing, processed, failed, skipped)
- `Channel` model with sync tracking
- Complete Supabase schema with proper relationships and indices
- `VideoRepository` with upsert logic and status management
- `ChannelRepository` with sync tracking

**Services & Infrastructure**
- `ChannelTracker` service for YouTube content extraction
- Google OAuth client for YouTube API access
- Database migrations and schema
- Configuration management with environment variables
- API endpoints for channel management (`/api/channels/*`)

**Current Workflow**
- Manual channel sync via `/api/channels/sync` endpoint
- Automatic video collection with metadata
- Status tracking (videos start as "collected")
- Database persistence with proper error handling

### ❌ What Needs to Be Built

**Orchestrator Layer**
- Central pipeline coordinator
- Date-based window processing
- State machine management
- Idempotent operations

**Content Processing Services**
- Transcript extraction service
- AI analysis service 
- Digest generation service

**Time Management**
- Date window utilities for 24h processing
- Backfill capabilities

## Implementation Plan

### Phase 1: Core Orchestrator Foundation

#### 1.1 Create Time Window Utilities
**File:** `src/app/core/utils/time_window.py`
```python
# Purpose: Convert dates to strict UTC windows for idempotent processing
# Why Strict UTC: Prevents issues with server location and Daylight Savings.
# Optimal Visibility: Target release 12:00-14:00 UTC (AM in US, PM in EU).
# Functions:
# - get_window(date) -> (start_utc, end_utc)
# - get_current_date_window() -> (start_utc, end_utc)
# - parse_date(date_str) -> date
# - get_paris_offset_window(target_hour=8) -> TimeWindow  # Handles Paris wake-up logic
```

#### 1.2 Create Orchestrator Service
**File:** `src/app/services/orchestrator.py`
```python
# Purpose: Central pipeline coordinator (The "Boss")
# Composition: Uses specific service orchestrators (The "Workers") for sub-tasks.
# Class: ContentOrchestrator
# Methods:
# - run_daily_pipeline(target_date: date) -> PipelineResult
# - extract_content(window: TimeWindow) -> ExtractionResult
# - get_processing_queue(target_date: date) -> List[Video] 
#   # Finds "collected" videos pending transcript/analysis.
# - mark_processing_complete(video_id: str, status: ProcessingStatus)
#   # Updates state to ensure idempotency (no double-processing).
```

#### 1.3 Create Pipeline Models
**File:** `src/app/models/pipeline.py`
```python
# Purpose: Pipeline execution tracking
# Classes:
# - TimeWindow (start_utc, end_utc)
# - ExtractionResult (videos_found, videos_saved, errors)
# - PipelineResult (extraction, processing, completion stats)
# - ProcessingStatus (extracted, transcribed, analyzed, completed)
```

### Phase 2: Content Extraction Integration

#### 2.1 Enhance Channel Tracker for Date Windows
**Updates to:** `src/app/services/channel_tracker.py`
```python
# Add methods:
# - sync_channels_for_date(target_date: date) -> ChannelTrackerResult
# - fetch_videos_in_window(channel_id: str, window: TimeWindow) -> List[Video]
```

#### 2.2 Update Video Repository for Date Queries
**Updates to:** `src/app/repositories/video_repository.py`
```python
# Add methods:
# - get_videos_for_date(target_date: date) -> List[Video]
# - get_videos_in_window(window: TimeWindow) -> List[Video]
# - get_pending_processing(target_date: date) -> List[Video]
```

### Phase 3: Content Processing Integration

#### 3.1 Implement Transcript Service (Integration with transcript.io)
**File:** `src/app/client/transcript_io.py`
```python
# Purpose: Low-level API client for youtube-transcript.io
# Class: TranscriptIoClient
# Methods:
# - fetch_transcript(video_id: str) -> TranscriptResult
# - fetch_batch_transcripts(video_ids: List[str]) -> List[TranscriptResult]
```

**File:** `src/app/services/transcript_service.py`
```python
# Purpose: Domain logic for transcript management
# Strategy: Atomic processing (one-by-one) for reliability.
# Failure Handling: Dead Letter logic (marks as fetched/failed on terminal errors).
# Class: TranscriptService
# Methods:
# - process_video_transcript(video: Video) -> TranscriptResult
# - get_pending_transcripts(limit: int) -> List[Video]
```

#### 3.2 Create Analysis Service (Placeholder)
**File:** `src/app/services/analysis_service.py`
```python
# Purpose: AI analysis coordination
# Class: AnalysisService  
# Methods:
# - analyze_video(video: Video, transcript: str) -> AnalysisResult
# - save_analysis(video_id: str, analysis: dict) -> bool
```

#### 3.3 Create Digest Service (Placeholder)
**File:** `src/app/services/digest_service.py`
```python
# Purpose: Daily digest generation
# Class: DigestService
# Methods:
# - generate_digest(target_date: date) -> DigestResult
# - save_digest(digest: DailyDigest) -> bool
```

### Phase 4: API Integration

#### 4.1 Create Orchestrator API Endpoint
**File:** `src/app/api/orchestrator.py`
```python
# Endpoints:
# POST /api/orchestrator/run-daily/{date}
# GET /api/orchestrator/status/{date}
# POST /api/orchestrator/backfill/{start_date}/{end_date}
```

#### 4.2 Update Main API Router
**Updates to:** `src/app/main.py`
```python
# Include orchestrator router
# Add health check endpoints
# Add pipeline status endpoints
```

### Phase 5: Configuration & Environment

#### 5.1 Update Settings
**Updates to:** `src/app/config/settings.py`
```python
# Add orchestrator settings:
# - processing_batch_size
# - max_retry_attempts
# - processing_timeout_minutes
# - default_pipeline_date (for testing)
```

#### 5.2 Update Environment Variables
**Updates to:** `.env.example`
```bash
# Add pipeline configuration
PROCESSING_BATCH_SIZE=10
MAX_RETRY_ATTEMPTS=3
PROCESSING_TIMEOUT_MINUTES=30
DEFAULT_PIPELINE_DATE=2023-12-20
```

## Implementation Priority & Dependencies

### High Priority (Immediate Implementation)
1. **Time Window Utilities** - Foundation for all date-based operations
2. **Pipeline Models** - Data structures for orchestration
3. **Core Orchestrator** - Central coordination logic
4. **Channel Tracker Integration** - Connect existing extraction to orchestrator

### Medium Priority (Next Phase)
1. **Repository Enhancements** - Date-based queries
2. **Orchestrator API** - External trigger mechanism
3. **Configuration Updates** - Environment setup

### Low Priority (Placeholder Implementation)
1. **Transcript Service** - Stub implementation for future
2. **Analysis Service** - Stub implementation for future  
3. **Digest Service** - Stub implementation for future

## Key Design Principles

### 1. Idempotency First
- Every operation can be run multiple times safely
- Unique constraints prevent duplicates
- Upsert patterns for data persistence
- **Checkpointing:** Feature flags (e.g., `transcript_fetched`) prevent redundant work

### 2. Date-Window Based Processing
- All operations work on explicit date ranges
- No "relative time" dependencies
- Enables easy backfilling and reprocessing

### 3. State Machine Clarity
- Clear status transitions: collected → processing → processed
- Error states with retry capabilities
- Resumable operations
- **Atomic Strategy:** Process complex items (transcripts/AI) one-by-one to isolate failures

### 4. Repository Pattern Consistency
- All database operations go through repositories
- Business logic stays in services (separation of "What to do" vs "How to store it")
- Enables switching storage backends without breaking core logic

### 5. Orchestrator as Coordinator
- Thin API layer (only handles HTTP/web concerns)
- Orchestrator manages the "Brain" and workflow logic
- Services handle specific domain operations (YouTube, AI, DB)
- **Thin Client Principle:** External API clients are "dumb" and decoupled from domain models

### 6. Layered Architecture
- API -> Service -> Repository -> Model
- Dependency flow: Outer layers depend on inner layers, never the reverse.

### 7. Failure Management (Dead Letter)
- Terminal errors (e.g., "No transcript available") are caught
- Mark items as processed/skipped to avoid infinite retry loops
- Preserve system credits and quotas

## Code Quality & Engineering Standards

### 1. Guardrails (Tooling)
- **Formatter/Linter**: `Ruff` (Unified, fast tool for PEP8 and logic errors)
- **Type Checking**: `Mypy` (Static typing to prevent runtime bugs)
- **Package Management**: `uv` (Fast, modern dependency management)

### 2. Implementation "Opinions"
- **Type Hints**: Mandatory for all function signatures.
- **Rule of Three**:
    - **DRY (Don't Repeat Yourself)**: Functionize logic used 3+ times.
    - **KISS (Keep It Simple)**: If a function can't be explained in one sentence, split it.
- **The "Rule of Thin API"**: Controllers should have < 10 lines of logic; move the rest to Services.
- **Pydantic/Dataclasses**: Use for "Contract" models (TimeWindow, Results) instead of raw dictionaries.

## Success Metrics

### Technical Metrics
- **Zero Duplicates**: No duplicate videos regardless of sync frequency
- **Resume-ability**: Can stop/start processing without data loss
- **Audit Trail**: Complete history of all operations
- **Performance**: Process 100 videos in under 5 minutes

### Functional Metrics
- **Reliability**: 99% success rate for content extraction
- **Consistency**: Same results when reprocessing same date
- **Scalability**: Handle 50+ channels with 1000+ daily videos
- **Maintainability**: Clear error messages and debugging capabilities

## Testing Strategy

### Unit Tests
- Time window calculations
- Repository operations
- Service integrations
- Error handling

### Integration Tests
- Full pipeline execution
- Database state verification
- API endpoint functionality
- OAuth authentication flow

### End-to-End Tests
- Complete date processing cycle
- Backfill operations
- Error recovery scenarios
- Performance benchmarks

## Next Steps

1. **Implement Phase 3 Transcript Extraction** (Real client + updated service)
2. **Integrate with existing ChannelTracker** (Date window support)
3. **Build orchestrator API endpoint** (Manual trigger capability)
4. **Add comprehensive testing** (Unit + Integration for Transcripts)
5. **Create placeholder AI services** (Future analysis work)

This plan provides a solid foundation for implementing the orchestrator pattern while maintaining compatibility with existing code and enabling future AI processing capabilities.