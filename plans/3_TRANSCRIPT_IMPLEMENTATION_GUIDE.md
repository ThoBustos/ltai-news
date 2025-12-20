# Transcript Extraction Implementation Guide

## Overview
This document outlines the implementation of the **Transcript Extraction Service** using `transcript.io`. It follows the core architectural principles defined in the `ORCHESTRATOR_IMPLEMENTATION_PLAN.md`, focusing on observability, idempotency, and layered separation of concerns.

## 1. Architectural Alignment

The implementation follows our established 4-layer architecture:

1.  **Client Layer (`src/app/client/transcript_io.py`)**: 
    *   Low-level wrapper for the `transcript.io` HTTP API.
    *   Handles authentication (`Basic` auth), retries, and raw response parsing.
2.  **Service Layer (`src/app/services/transcript_service.py`)**:
    *   Contains business logic: "Should we fetch a transcript? Where do we save it?"
    *   Orchestrates the client and the repository.
3.  **Repository Layer (`src/app/repositories/video_repository.py`)**:
    *   Handles DB operations for the `video_transcripts` table and updates the `videos` table flags.
4.  **Model Layer (`src/app/models/pipeline.py`)**:
    *   Defines structured `TranscriptResult` and `TranscriptRequest` objects for type-safe data flow.

---

## 2. Key Design Patterns

### A. Checkpointing (Resume-ability)
We use the `transcript_fetched` (BOOLEAN) column in the `videos` table as a "Checkpoint."
*   **Logic:** The Orchestrator queries for videos where `status = 'collected' AND transcript_fetched = False`.
*   **Benefit:** If the pipeline fails after 50/100 videos, the next run will skip the first 50 automatically.

### B. Idempotency
Transcripts are stored in a dedicated `video_transcripts` table with a `video_id` PRIMARY KEY.
*   **Logic:** We use an `UPSERT` pattern. If a transcript for Video X already exists, we overwrite it or skip it (preventing duplicate rows).

### C. The "Rule of Thin Client"
The `TranscriptIoClient` knows **nothing** about our database or our `Video` models. It only knows how to take a `video_id` (string) and return text. This makes it easy to test in isolation and highly portable.

### D. Dead Letter Logic (Failure Management)
To prevent infinite retry loops for videos that will never have transcripts (e.g., music-only or transcripts disabled):
*   **Logic:** If the API returns a terminal error (e.g., "No transcript available"), we mark the video as `SKIPPED` or `FAILED` in the database.
*   **Checkpoint Update:** The `transcript_fetched` flag is set to `True` even on terminal failure to ensure the orchestrator doesn't waste credits on the same video in future runs.

---

## 3. Execution Flow

The system supports two execution modes, both utilizing an **Atomic Strategy** (one-by-one processing) for maximum reliability and easier debugging.

### Mode 1: Integrated (Daily Pipeline)
The `ContentOrchestrator.run_daily_pipeline()` adds a new phase after content extraction:
1.  **Phase 1:** Sync YouTube channels (Discover videos).
2.  **Phase 2:** **Extract Transcripts** (Fetch text for newly discovered videos, one-by-one).
3.  **Phase 3:** Process/Analyze (AI steps).

### Mode 2: Standalone (Atomic Extraction)
A new API endpoint `POST /api/orchestrator/extract-transcripts/{date}` allows triggering only the transcript logic. This is useful for:
*   Backfilling old videos that were collected but not transcribed.
*   Recovering from API downtime or credit exhaustion on the transcript provider.

---

## 4. Configuration

### Environment Variables (`.env`)
Add these to connect to the external provider:
```bash
# Transcript.io Configuration
TRANSCRIPT_IO_API_KEY="Basic <your_key_here>"
TRANSCRIPT_IO_BASE_URL="https://api.youtube-transcript.io/v1"
```

---

## 5. Database Schema Impact

The implementation utilizes two existing tables in Supabase:

1.  **`videos`**:
    *   `transcript_fetched` (bool): Updated to `True` upon successful extraction.
2.  **`video_transcripts`**:
    *   `video_id` (text, PK): Foreign key to `videos.id`.
    *   `transcript` (text): The raw content.
    *   `language_code` (text): Defaulting to `en`.

## 6. Implementation Checklist

- [ ] Create `TranscriptIoClient` for API communication.
- [ ] Update `TranscriptService` to use the real client instead of placeholders.
- [ ] Add `VideoRepository` method to save transcripts and update `transcript_fetched` flag.
- [ ] Add `extract_transcripts` method to `ContentOrchestrator`.
- [ ] Register standalone endpoint in `src/app/api/orchestrator.py`.