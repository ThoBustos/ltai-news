# LTAI News - Architecture & Design Patterns Guide

This document outlines the professional Computer Science (CS) patterns and architectural decisions used to build the LTAI News pipeline.

---

## 🏗️ Core Architectural Patterns

### 1. Orchestrator Pattern (The "Brain")
Instead of having an API endpoint directly talking to YouTube, then AI, then Email, we use an **Orchestrator**. 
- **Concept**: A central coordinator that manages the workflow logic.
- **Benefit**: Decouples the "What" (Business Logic) from the "How" (Implementation). The API layer stays thin, and the Orchestrator ensures steps happen in the correct order.
- **Implementation**: `src/app/services/orchestrator.py` (The `DailyPipeline` class).

### 2. Idempotent Pipeline
- **Concept**: An operation is **idempotent** if running it multiple times has the same effect as running it once.
- **Benefit**: If a cron job runs twice, or you manually trigger a backfill for a date that was already processed, the system won't create duplicate videos, double-charge AI tokens, or send duplicate emails.
- **Mechanism**: We use unique constraints in Supabase (e.g., YouTube Video ID, `publish_date` for digests) and "Upsert" logic in Repositories.

### 3. Repository Pattern (Data Abstraction)
- **Concept**: A layer that mediates between the domain/business logic and the data mapping layers.
- **Benefit**: Our services don't write SQL or talk directly to the Supabase client. They talk to a `VideoRepository`. If we ever switch databases, we only change the Repository, not the business logic.
- **Implementation**: `src/app/repositories/video_repository.py`.

### 4. State Machine (Status Tracking)
- **Concept**: Tracking the lifecycle of an entity through discrete states.
- **States**: `collected` → `transcribing` → `analyzed` → `digest_ready`.
- **Benefit**: Reliability. If the pipeline fails during the AI analysis of video #5, the next run sees that videos #1-4 are already "analyzed" and resumes exactly where it left off.

---

## 📂 Project Structure & File Map

### New Components to Create
| File | Responsibility |
| :--- | :--- |
| `src/app/services/orchestrator.py` | Coordinates the flow: Sync -> Transcribe -> Analyze -> Build Digest. |
| `src/app/services/transcript_service.py` | Connects to `youtube-transcript.io` and saves to `video_transcripts`. |
| `src/app/services/analysis_service.py` | Orchestrates LLM calls (Gemini/Anthropic) for deep video analysis. |
| `src/app/services/digest_service.py` | Aggregates all processed data into the final HTML/Markdown format. |
| `src/app/core/utils/time_window.py` | Pure logic to convert a `date` into strict UTC `start` and `end` timestamps. |

### Existing Components to Adapt
| File | Change Needed |
| :--- | :--- |
| `src/app/repositories/video_repository.py` | Add methods to save transcripts and processed analysis data. |
| `src/app/api/run_daily.py` | Refactor to act as a simple trigger for the `Orchestrator`. |
| `.env` | Add keys for AI providers, local Supabase, and service URLs. |

---

## ⏱️ The 24h Window Logic

To ensure the pipeline is predictable, we avoid "relative time" (like `now() - 24h`). Instead, we use **Explicit Date Windows**:

1. **Input**: A specific date (e.g., `2023-12-20`).
2. **Window**: 
   - `START`: `2023-12-20T00:00:00Z`
   - `END`:   `2023-12-20T23:59:59Z`
3. **Execution**: The pipeline fetches all content published *within* that strict window. This makes backfilling historical data as easy as passing a different date to the same function.

---

## 🛠️ Implementation Blueprint (The Code Flow)

```python
# Pseudo-logic for the Orchestrator
async def run_pipeline(target_date: date):
    # 1. Define the boundary
    window = TimeUtils.get_window(target_date)
    
    # 2. Extraction (Idempotent)
    # Result: Videos saved to DB with status 'collected'
    await youtube_service.sync_content(window)
    
    # 3. Processing (Resume-able)
    # Fetches only videos for this date that aren't 'processed' yet
    videos_to_process = video_repo.get_pending(target_date)
    
    for video in videos_to_process:
        # Transcript Stage
        transcript = await transcript_service.get_or_fetch(video.id)
        
        # AI Analysis Stage
        analysis = await analysis_service.analyze(video, transcript)
        
        # Update Status
        video_repo.mark_as_processed(video.id)
        
    # 4. Final Assembly
    # Queries video_processed_data for all videos in window
    return await digest_service.generate_daily_digest(target_date)
```

---

## 🎯 Success Metrics
- **Zero Duplicates**: No matter how many times the script runs.
- **Resume-ability**: Can stop and start without losing progress.
- **Audit Trail**: Every LLM run and transcript is saved for future fine-tuning or debugging.

