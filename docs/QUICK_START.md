# Quick Start Guide - LTAI News

Get the system running in 10 minutes.

## Prerequisites

- Python 3.11+
- X Developer account ([apply here](https://developer.twitter.com))
- Supabase account
- API keys for: YouTube, Resend, Gemini, Anthropic

## Installation

```bash
git clone <repo>
cd ltai-news
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Configure X/Twitter (see [X Authentication Setup](./X_AUTHENTICATION_SETUP.md)):
   ```bash
   python scripts/generate_twitter_oauth2_tokens_auto.py
   # Follow prompts, update .env with tokens
   ```

3. Add other API keys to `.env` (Supabase, YouTube, etc.)

## Run

```bash
# Start server
python -m uvicorn app.main:app --reload

# Test daily pipeline
curl -X POST "http://localhost:8000/api/orchestrator/run-daily-pipeline/2025-01-24"

# Post thread to X
curl -X POST "http://localhost:8000/api/x-thread/post-to-x/2025-01-24"
```

## Documentation

- [X Authentication Setup](./X_AUTHENTICATION_SETUP.md) - Detailed X/Twitter OAuth 2.0 setup
- [Security](./SECURITY.md) - Database security and RLS
- [README](../README.md) - Full project documentation

## Troubleshooting

**403 Forbidden**: App permissions must be "Read and write" in Developer Portal

**401 Unauthorized**: Regenerate tokens with the script

**No digest found**: Run daily pipeline first before posting threads

See [X Authentication Setup - Troubleshooting](./X_AUTHENTICATION_SETUP.md#troubleshooting) for more.
