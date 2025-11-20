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
   - Can show archives, stats, or “today’s digest”.

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
