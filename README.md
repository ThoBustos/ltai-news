# LTAI News

Daily AI-powered digest of the latest videos from a curated list of YouTube channels for the *Let’s Talk AI* ecosystem.

---

## TL;DR

**LTAI News**:

1. Checks a set of YouTube channels every day.
2. Detects new videos using the **YouTube Data API**.
3. Fetches transcripts via **youtube-transcript.io**.
4. Analyzes content with **LangGraph + Gemini + Anthropic**.
5. Stores everything in **Supabase**.
6. Sends a styled email via **Resend**.
7. Tracks LLM runs & evaluations with **Opik**.
8. Exposes data to the existing frontend at **thomasbustos.com**.

This repo is the backend + pipeline. The frontend already exists and will consume the data (no frontend code here).

---

## System Overview

### Core Flow (Daily)

1. **Vercel Cron** triggers a Python endpoint (e.g. `/api/run_daily`).
2. Backend:
   - Loads the list of channels from **Supabase**.
   - Uses **YouTube Data API** to get the latest videos per channel.
   - Compares with stored videos in Supabase → detects *new* uploads.
   - For each new video:
     - Calls **youtube-transcript.io** to get the transcript.
     - Passes transcript + metadata into a **LangGraph** workflow:
       - Generate summary
       - Extract tags/topics
       - Optional callouts (key ideas, guests, etc.)
       - All LLM calls instrumented with **Opik** for logging/evals.
   - Writes processed results to Supabase (videos, summaries, tags, newsletter items).
3. When processing is done, backend:
   - Builds a **daily digest HTML** (light styling).
   - Sends it to the mailing list via **Resend**.

4. The existing **thomasbustos.com** frontend:
   - Reads from Supabase or a simple read-only API
   - Can show archives, stats, or "today's digest".

---

## Usage

### Starting the Server

```bash
PYTHONPATH=src uv run python src/app/main.py
```

The API will be available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

### Pipeline Operations

#### Run Daily Pipeline
Process all content for a specific date (extraction → transcription → analysis):

```bash
# Synchronous (waits for completion)
curl -X POST http://localhost:8000/api/orchestrator/run-daily/2025-01-20

# Asynchronous (returns immediately, runs in background)
curl -X POST http://localhost:8000/api/orchestrator/run-daily/2025-01-20/async
```

#### Check Pipeline Status
Get the current status of pipeline execution for a date:

```bash
curl http://localhost:8000/api/orchestrator/status/2025-01-20
```

#### Extract Transcripts Only
Extract transcripts for videos on a specific date (standalone operation):

```bash
# Synchronous
curl -X POST http://localhost:8000/api/orchestrator/extract-transcripts/2025-01-20

# Asynchronous
curl -X POST http://localhost:8000/api/orchestrator/extract-transcripts/2025-01-20/async
```

#### Backfill Date Range
Process multiple dates in sequence (useful for historical data):

```bash
# Synchronous
curl -X POST http://localhost:8000/api/orchestrator/backfill \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2025-01-15", "end_date": "2025-01-20"}'

# Asynchronous
curl -X POST http://localhost:8000/api/orchestrator/backfill/async \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2025-01-15", "end_date": "2025-01-20"}'
```

### Video Analysis & Processing

#### Process Single Video
Analyze individual videos with comprehensive AI extraction:

```bash
# Synchronous processing (returns full results)
curl -X POST http://localhost:8000/api/orchestrator/process-video/VIDEO_ID \
  -H "Content-Type: application/json"

# Asynchronous processing (immediate response, runs in background)
curl -X POST http://localhost:8000/api/orchestrator/process-video/VIDEO_ID/async \
  -H "Content-Type: application/json"
```

#### Get Analysis Statistics
Monitor processing costs, performance, and success rates:

```bash
# Last 30 days (default)
curl http://localhost:8000/api/orchestrator/analysis/stats

# Custom time period
curl "http://localhost:8000/api/orchestrator/analysis/stats?days=7"
```

**Example Response:**
```json
{
  "message": "Video dQw4w9WgXcQ analyzed successfully",
  "video_id": "dQw4w9WgXcQ", 
  "status": "completed",
  "analysis": {
    "tldr": "Video summary...",
    "core_topics": [{"topic": "AI", "category": "technical", "importance": "high"}],
    "lessons_learned": {"technical": ["..."], "business": ["..."]},
    "total_cost": 0.0234,
    "total_tokens": 1567
  },
  "processing_time_seconds": 12.4
}
```

**Prerequisites & Notes:**
- Video must have transcript available (use extract-transcripts endpoint first)
- Replace `VIDEO_ID` with actual YouTube video IDs from tracked channels
- Analysis extracts: TLDR, topics, lessons, sources, concepts, people, communities
- Costs and token usage tracked automatically via Opik integration

### Channel Management

#### List Tracked Channels
View all configured channels:

```bash
curl http://localhost:8000/api/channels/list
```

#### Sync Channels
Manually trigger sync of all configured channels (fetch recent videos):

```bash
curl -X POST http://localhost:8000/api/channels/sync
```

#### Resolve Channel
Test channel resolution before adding to tracked list:

```bash
curl -X POST http://localhost:8000/api/channels/resolve/@channelname
```

### Health & Info

```bash
# Service info
curl http://localhost:8000/

# Orchestrator health check
curl http://localhost:8000/api/orchestrator/health

# Interactive API documentation
open http://localhost:8000/docs
```

**Note:** Date format is `YYYY-MM-DD` (e.g., `2025-01-20`). Replace `localhost:8000` with your production server URL when deployed.

---

## Services & Components

- **Backend:** Python (serverless functions on Vercel)
- **Scheduler:** Vercel Cron
- **Database:** Supabase (Postgres + auth if needed later)
- **Email Delivery:** Resend
- **YouTube integration:**
  - YouTube Data API (latest videos by channel)
  - youtube-transcript.io (transcripts)
- **LLM & Orchestration:**
  - LangGraph
  - Gemini models
  - Anthropic models
- **Evaluation & Monitoring:**
  - Opik (LLM traces, metrics, future evals)
- **Frontend (existing):**
  - thomasbustos.com (consumes data, no front code here)

> **Styling & Resend:**  
> Emails are generated as **HTML** in Python.  
> Light styling (basic layout, typography) is done in the email template.  
> The main “beautiful UI” lives on the website (thomasbustos.com) which reads from Supabase.

---

## Proposed Repository Structure (Backend)

```text
ltai-news/
  README.md
  pyproject.toml / requirements.txt
  vercel.json

  src/
    app/
      __init__.py
      api/
        __init__.py
        run_daily.py        # Cron entrypoint
        health.py           # Simple healthcheck endpoint
        latest_digest.py    # (Optional) returns latest digest for frontend
      core/
        config.py           # env vars, settings
        models.py           # Pydantic models / DTOs
        db.py               # Supabase client helpers
        youtube.py          # YouTube Data API helpers
        transcripts.py      # youtube-transcript.io client
        pipeline.py         # main orchestration for daily run
        email_builder.py    # HTML generation for digest
        email_sender.py     # Resend API client
        opik_client.py      # instrumentation wrappers for LLM calls
        langgraph_flow.py   # LangGraph definitions (summary, tags)
      utils/
        logging.py
        time.py

  ops/
    env.example             # example env vars
    postman_collection.json # (optional) API testing
