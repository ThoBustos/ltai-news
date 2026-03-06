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

### Daily Digest Operations

#### Generate Digest for a Specific Day
Generate the newsletter digest for a specific date (requires videos to be analyzed first):

```bash
# Synchronous (waits for completion)
curl -X POST "http://localhost:8000/api/orchestrator/generate-digest/2025-12-29"

# Asynchronous (returns immediately, runs in background)
curl -X POST "http://localhost:8000/api/orchestrator/generate-digest/2025-12-29/async"
```
(it supports regeneration using upsert pattern)

#### Get Digest Content
Retrieve the generated digest for a specific date:

```bash
curl "http://localhost:8000/api/orchestrator/digest/2025-12-29"
```

#### Send Digest Email
Send the digest to subscribers or a test email:

```bash
# Send to all subscribers
curl -X POST "http://localhost:8000/api/orchestrator/send-digest/2025-12-29"

# Send test email
curl -X POST "http://localhost:8000/api/orchestrator/send-digest/2025-12-29" \
  -H "Content-Type: application/json" \
  -d '{"test_email": "test@example.com"}'
```

#### Reprocess Failed Videos
Retry analysis for videos that failed processing on a specific date:

```bash
# Synchronous (waits for completion)
curl -X POST "http://localhost:8000/api/orchestrator/reprocess-failed/2025-12-29"

# Asynchronous (returns immediately, runs in background)
curl -X POST "http://localhost:8000/api/orchestrator/reprocess-failed/2025-12-29/async"
```

This endpoint will:
1. Find all videos with status "failed" for the date
2. Delete any partial analysis data
3. Reset their status to "collected"
4. Re-run the analysis pipeline

### Weekly Digest Operations

#### Generate Weekly Digest
Generate a weekly summary digest (requires daily digests for the week to exist):

```bash
# Synchronous (waits for completion)
curl -X POST "http://localhost:8000/api/orchestrator/generate-weekly/2025-01-27"

# Asynchronous (returns immediately, runs in background)
curl -X POST "http://localhost:8000/api/orchestrator/generate-weekly/2025-01-27/async"
```

**Note:** The date should be the **Monday** of the week you want to generate (e.g., `2025-01-27` for the week of Jan 27 - Feb 2).

#### Get Weekly Digest Content
Retrieve generated weekly digests:

```bash
# Get the latest weekly digest
curl "http://localhost:8000/api/orchestrator/weekly/latest"

# Get a specific week's digest
curl "http://localhost:8000/api/orchestrator/weekly/2025-01-27"
```

### References & Entities

#### Get Top References
Retrieve the most frequently mentioned people, tools, and resources across all analyses:

```bash
curl "http://localhost:8000/api/orchestrator/references/top"
```

#### Search References
Search for a specific reference by name:

```bash
curl "http://localhost:8000/api/orchestrator/references/search/Sam%20Altman"
```

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

## X/Twitter Setup

This project can automatically post daily digest threads to X (formerly Twitter) using OAuth 2.0 PKCE authentication.

### Quick Start

1. **Developer Account**: Apply for X Developer access at [developer.twitter.com](https://developer.twitter.com)
2. **Create App**: Create a new project and app in the Developer Portal
3. **Configure Authentication**:
   - App permissions: **"Read and write"** (required for posting!)
   - Type: **"Web App"**
   - Callback URI: `http://127.0.0.1:8080/callback`
4. **Generate Tokens**:
   ```bash
   source .venv/bin/activate
   python scripts/generate_twitter_oauth2_tokens_auto.py
   ```
5. **Update `.env`**:
   ```env
   TWITTER_OAUTH2_CLIENT_ID=<from_developer_portal>
   TWITTER_OAUTH2_CLIENT_SECRET=<from_developer_portal>
   TWITTER_OAUTH2_ACCESS_TOKEN=<from_script_output>
   TWITTER_OAUTH2_REFRESH_TOKEN=<from_script_output>
   AUTO_POST_TO_X=false  # Set to true after testing
   ```
6. **Test Posting**:
   ```bash
   curl -X POST "http://localhost:8000/api/x-thread/post-to-x/2025-01-24"
   ```

### Documentation

For detailed setup instructions, troubleshooting, and security best practices:
- **[X Authentication Setup Guide](docs/X_AUTHENTICATION_SETUP.md)** - Complete setup walkthrough
- **[OAuth 2.0 Migration Summary](docs/OAUTH2_MIGRATION_SUMMARY.md)** - Migration from OAuth 1.0a

### Authentication Notes

- **OAuth 2.0 PKCE Only**: This project uses OAuth 2.0 with PKCE (OAuth 1.0a removed)
- **Local Development**: Uses HTTP localhost callback (`http://127.0.0.1:8080/callback`) which is safe and standard practice
- **Auto-Refresh**: Tokens automatically refresh every 2 hours using the refresh token
- **Security**: Never commit `.env` to git - credentials are gitignored

### Posting Threads

#### Preview Thread
Preview the thread content before posting (useful for testing format):

```bash
curl "http://localhost:8000/api/x-thread/preview/2025-01-27"
```

#### Manual Post
```bash
curl -X POST "http://localhost:8000/api/x-thread/post-to-x/YYYY-MM-DD"
```

#### Auto-Post (Phase 5 of Daily Pipeline)
Set `AUTO_POST_TO_X=true` in `.env` to automatically post threads after digest generation.

#### Thread Format
Threads include:
- Opening hook with date
- Video summaries with links
- Closing CTA
- Auto-threaded replies

**Example:** [See X Authentication Setup Guide](docs/X_AUTHENTICATION_SETUP.md#testing) for full testing procedures.

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
> The main "beautiful UI" lives on the website (thomasbustos.com) which reads from Supabase.

---

## Security

This project uses **Row Level Security (RLS)** to protect the database. See **[SECURITY.md](./SECURITY.md)** for full documentation including:

- Architecture diagrams (frontend vs backend access)
- Authentication vs Authorization (CS fundamentals)
- RLS policy explanation and configuration
- The two Supabase keys (`anon` vs `service_role`)
- Defense in depth security model
- Guidelines for contributors adding new tables

**Quick summary:** Only `daily_digests` is publicly readable. All other tables (including `subscribers`) are locked down to backend-only access.

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
```

---

## Technical Notes & Learnings

### Gemini Structured Output for Reliable LLM Generation

**Problem:** Daily digest generation was producing incomplete outputs - only 4 of 13 video sections would be generated, with missing `deep_analysis` and `key_quotes` fields.

**Initial hypothesis:** Context window or output token limits.

**Actual root cause:** Model "laziness" and lack of schema enforcement.

**Solution (3 lines of code):**

```python
# Before (unreliable)
config=GenerateContentConfig(
    systemInstruction=system_content,
    temperature=1.0,
)

# After (reliable)
config=GenerateContentConfig(
    systemInstruction=system_content,
    temperature=0.2,  # Low for deterministic output
    response_mime_type="application/json",  # Force JSON mode
    response_schema=DigestContentResponse.model_json_schema(),  # Enforce ALL fields
)
```

**Key learnings:**

1. **Gemini Flash supports 64K output tokens** - truncation was NOT the issue. 13 videos × 700 tokens = ~9,100 tokens (well under limit).

2. **High temperature (1.0) causes non-deterministic outputs** - the model would "skip" fields randomly. Lowering to 0.2 made outputs consistent.

3. **`response_schema` is critical** - it forces Gemini to populate ALL required fields in your Pydantic model. Without it, the model may "be lazy" and omit fields.

4. **Structured output eliminates JSON parsing** - no need for manual extraction of JSON from markdown code blocks. The response is guaranteed valid JSON. (idk why models tend to love to try to parse jsons instead of using existing structured outputs existing logics.)

**Results:**| Metric | Before | After |
|--------|--------|-------|
| Video sections | 4/13 (31%) | **13/13 (100%)** |
| deep_analysis | Often empty | 100-137 words each |
| key_quotes | Often missing | 2 per video |
| Cost | Unknown | **$0.006** |
| Reliability | Inconsistent | **Deterministic** |**Reference:** `src/app/agents/daily_digest/nodes.py:249-260`