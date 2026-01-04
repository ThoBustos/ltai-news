# Newsletter System Overview

A daily AI/tech intelligence brief generated from curated YouTube content.

---

## What We're Building

An automated pipeline that transforms YouTube videos into a professional newsletter:

```
YouTube Videos → Transcripts → AI Analysis → Daily Digest → Email Newsletter
```

**Goal**: Save readers hours of video watching by delivering dense, actionable insights in a 5-15 minute read.

---

## Core Philosophy

### Layered Reading

Not everyone has the same time budget. The newsletter supports three reading depths:

| Layer | Time | Section | Purpose |
|-------|------|---------|---------|
| Skim | 30 sec | Big Picture Bullets | Quick scan of key insights |
| Read | 3-5 min | Deeper Picture | Connected synthesis across videos |
| Deep Dive | 15+ min | Video Breakdowns | Full analysis per video |

### Signal Over Noise

- **Specific over generic** — Numbers, names, frameworks, not vague summaries
- **Quotes over paraphrasing** — Verbatim insights that stick
- **Connections over isolation** — How ideas across videos relate

### Professional, Not Flashy

- Zero emojis
- Clear titles that teach something
- Dense but scannable formatting

---

## Architecture

### Pipeline Stages

```
1. VIDEO COLLECTION
   └── Curated YouTube channels → New videos detected

2. TRANSCRIPT EXTRACTION
   └── YouTube API → Full transcript with timestamps

3. VIDEO ANALYSIS (per video)
   └── LLM extracts: quotes, frameworks, statistics, people, concepts
   └── Output: VideoAnalysisResponse (structured JSON)

4. DAILY DIGEST GENERATION
   └── LLM synthesizes all videos into unified digest
   └── Cross-video connections, convergence, tensions
   └── Output: DigestContentResponse (structured JSON)

5. FORMATTING
   └── Markdown + HTML rendering
   └── Ready for email delivery

6. DISTRIBUTION
   └── Email service sends to subscribers
```

### Key Models

**VideoAnalysisResponse** — Per-video extraction:
- `tldr`, `key_audience`, `teaser_hooks`
- `direct_quotes`, `frameworks_shared`, `statistics_data`
- `people_mentioned` (with social_links), `communities_mentioned`
- `section_analysis` for deep dives

**DigestContentResponse** — Daily synthesis:
- `big_picture_bullets` — 1-2 per video, skimmable
- `deeper_picture` — 2-6 paragraphs connecting concepts
- `convergence_points` — Where multiple videos agree
- `key_tensions` — Where videos disagree
- `video_sections` — Per-video breakdown with `logical_flow`
- `contrarian_corner` — Counterintuitive insight with `so_what`
- `action_items` — Concrete actions with `first_step`

---

## Strategic Decisions

### 1. Entity Linking (STRICT Policy)

**Problem**: LLMs confidently hallucinate URLs and social handles.

**Decision**: Only include links explicitly present in video context.
- Reuse: URLs, handles, arXiv links from video description/transcript
- Never guess: Even for famous people like @sama or openai.com
- Plain text is acceptable if no link available

**Why**: Wrong link is worse than no link. Trust is paramount.

### 2. Cross-Video Analysis

**Problem**: Videos in isolation miss compound insights.

**Decision**: Explicitly surface connections:
- **Convergence Points** — When 2+ videos discuss same concept
- **Key Tensions** — When videos disagree
- **Connections** — Per video: Extends/Contradicts/Deepens other content

**Why**: The newsletter's value is synthesis, not just summarization.

### 3. Empty Lists Are Valid

**Problem**: Forced connections feel artificial.

**Decision**: Allow empty `convergence_points` and `key_tensions`.
- Single video? No cross-video analysis possible
- Unrelated videos? Don't invent connections
- Prompt explicitly states: "Do NOT force connections"

**Why**: Authenticity over completeness.

### 4. Logical Flow Over Tags

**Problem**: Tags like "AI | ML | Tech" don't convey the journey.

**Decision**: Each video has `logical_flow` showing intellectual progression:
```
BAD:  ["AI", "ML", "Future"]
GOOD: ["Problem: context collapse", "→ 700k token evidence", "→ Agentic RAG solution"]
```

**Why**: Readers should understand the argument structure before diving in.

### 5. Actionable Insights

**Problem**: "Think about X differently" isn't actionable.

**Decision**: Every contrarian insight has `so_what`, every action item has `first_step`:
```
BAD:  "Implement better context management"
GOOD: "Run your RAG at 50%, 70%, 90% utilization. Measure retrieval accuracy."
```

**Why**: Readers should know exactly what to do next.

---

## Current State (v2.1)

### Implemented

- Video analysis with depth extractions (quotes, frameworks, statistics)
- Daily digest generation with structured output
- Layered overview (big_picture_bullets + deeper_picture)
- Cross-video analysis (convergence_points, key_tensions)
- Per-video logical_flow
- Enhanced contrarian corner with so_what
- Enhanced action items with first_step
- Entity linking with strict policy
- Social links extraction (when explicit in context)
- Markdown + HTML formatters
- Backwards-compatible schema (new fields have defaults)

### Not Yet Implemented

- [ ] Internal anchor links (e.g., `[Video Title](#video-id)`) — Deferred, slug handling is tricky
- [ ] Frontend components for new sections
- [ ] A/B testing different digest formats
- [ ] Reader engagement tracking

---

## File Structure

```
src/app/
├── models/
│   ├── daily_digest.py      # DigestContentResponse, VideoSection, etc.
│   └── video_analysis.py    # VideoAnalysisResponse, PersonMention, etc.
├── agents/
│   ├── video_analyzer/
│   │   └── prompts.py       # Video extraction prompt (v2.1)
│   └── daily_digest/
│       ├── prompts.py       # Digest generation prompt (v2.1)
│       └── formatters.py    # Markdown + HTML rendering
└── services/
    └── orchestrator.py      # Pipeline coordination

docs/
├── NEWSLETTER-OVERVIEW.md   # This file
├── IMPLEMENTATION-GUIDE-V2.md # Detailed technical guide
└── newsletter-v2-mockup.md  # Before/after examples
```

---

## Quality Checklist

When reviewing generated digests:

- [ ] Big picture bullets: ~1-2 per video
- [ ] Deeper picture: Explicitly references videos
- [ ] Logical flow: Shows journey, not buzzwords
- [ ] Contrarian corner: Has actionable so_what
- [ ] Action items: Have concrete first_step
- [ ] Connections: Use Extends/Contradicts/Deepens pattern
- [ ] Entity links: Only when URL was in context
- [ ] No emojis anywhere
- [ ] Title teaches something specific

---

## Guiding Principle

> The newsletter's job is to make readers smarter in less time than watching the videos. Every sentence must earn its place.
