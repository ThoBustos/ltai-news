# 9. Daily Digest V2 - Clean, Professional, High-Signal Newsletter

## Overview

This plan transforms the daily digest from a "catchy newsletter with emojis" to a **clean, professional intelligence brief** that maximizes signal-to-noise ratio. The redesign focuses on clear navigation, depth on demand, and leveraging the V2 video extraction fields (quotes, frameworks, statistics, analogies, section analysis).

**Version**: 2.0  
**Prompt Version**: Upgrade from 1.0 → 2.0  
**Breaking Changes**: Yes (model changes, no emojis, no thumbnails)

---

## Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Value in the title** | Clear thesis statement, not marketing speak |
| **Zero emojis** | Professional, clean typography throughout |
| **No thumbnails** | Text-focused, fast loading, distraction-free |
| **Easy navigation** | Table of contents with clickable section links |
| **Estimated read time** | Calculated from word count (avg 200 WPM) |
| **Bottom-up/Top-down** | High-level summary → per-video depth |
| **Context clarity** | Who's speaking, duration, tags, channel |
| **Compress/Decompress** | Condensed view → expandable paragraphs |
| **Signal density** | Every sentence earns its place |

---

## Current State Analysis

### What We Have (V1)

| Component | Current | Issue |
|-----------|---------|-------|
| `title` | "Catchy one-sentence insight" | Too vague, marketing-focused |
| `title_emoji` | Single emoji | Must remove |
| `thumbnail_url` | Per video | Must remove |
| `video_sections` | Hook + nuggets + insights | Missing V2 depth fields |
| `stats` | Video count, duration, channels | Missing read time |
| Navigation | None | No TOC |
| Sources intro | None | Channels not shown at top |

### Missing V2 Video Fields (Not Passed to Digest)

Current `format_video_context()` does NOT include:
- `teaser_hooks` - 3 compelling sentences
- `keywords` - 8-15 tags
- `direct_quotes` - Verbatim aha moments
- `analogies_metaphors` - Compression tools
- `frameworks_shared` - Mental models
- `statistics_data` - Numbers and claims
- `section_analysis` - Deep section breakdowns

---

## Architecture Changes

### File Structure

```
src/app/
├── models/
│   └── daily_digest.py           # UPDATE: Remove emoji, add read_time, update video section
├── agents/
│   └── daily_digest/
│       ├── prompts.py            # UPDATE: V2 prompt, no emojis, pass V2 fields
│       ├── nodes.py              # UPDATE: Calculate read time
│       ├── formatters.py         # UPDATE: No thumbnails, add TOC, clean styling
│       └── state.py              # No changes needed
└── repositories/
    └── daily_digest_repository.py  # UPDATE: Remove emoji from title storage
```

---

## Phase 1: Model Updates

### File: `src/app/models/daily_digest.py`

#### 1.1 Update DigestStats - Add Read Time

**Location**: Around line 20

```python
class DigestStats(BaseModel):
    """Overall statistics for the digest."""
    video_count: int
    total_duration_minutes: int
    estimated_read_minutes: int = Field(description="Estimated read time based on word count at 200 WPM")
    channels: List[ChannelStat]
```

#### 1.2 Update DigestContentResponse - Remove Emoji, Update Title

**Location**: Around line 82

**Before:**
```python
class DigestContentResponse(BaseModel):
    """Complete LLM response schema for digest generation."""

    title: str = Field(description="Catchy one-sentence insight that captures the day's theme")
    title_emoji: str = Field(description="Single emoji for the title")
```

**After:**
```python
class DigestContentResponse(BaseModel):
    """Complete LLM response schema for digest generation - V2."""

    title: str = Field(
        description="Clear, specific title that delivers value. Not abstract or hype. "
        "Direct learning statement. Example: 'Specialized AI Models Outperform General Reasoners for Niche Tasks'"
    )
    # REMOVED: title_emoji - no emojis in V2
    
    # NEW: Table of contents for navigation
    table_of_contents: List[str] = Field(
        description="Section titles for navigation: intro, each video title, action items, references"
    )
```

#### 1.3 Update VideoSection - Add V2 Depth Fields

**Location**: Around line 35

**Before:**
```python
class VideoSection(BaseModel):
    """Section for a single video in the digest."""
    video_id: str
    title: str
    channel_name: str
    thumbnail_url: str
    highest_signal_hook: str
    golden_nuggets: List[GoldenNugget]
    key_insights: List[str]
    video_url: str
```

**After:**
```python
class VideoSection(BaseModel):
    """Section for a single video in the digest - V2."""
    video_id: str
    title: str
    channel_name: str
    # REMOVED: thumbnail_url - no thumbnails in V2
    duration_minutes: int = Field(description="Video duration in minutes")
    speakers: List[str] = Field(default_factory=list, description="Main speakers if identifiable")
    tags: List[str] = Field(default_factory=list, description="3-5 topic tags for categorization")
    
    # Core summary
    condensed_summary: str = Field(
        description="2-3 sentence dense summary with specific takeaways, not generic description"
    )
    structure_overview: str = Field(
        description="Brief outline of video structure/sections for context"
    )
    
    # V2 depth fields
    key_quotes: List[str] = Field(
        description="2-3 best verbatim quotes from the video"
    )
    frameworks_mentioned: List[str] = Field(
        default_factory=list, 
        description="Framework/mental model names referenced"
    )
    key_statistics: List[str] = Field(
        default_factory=list,
        description="Important numbers/statistics mentioned"
    )
    key_analogies: List[str] = Field(
        default_factory=list,
        description="Memorable analogies used to explain concepts"
    )
    
    # Deep dive
    deep_analysis: str = Field(
        description="2-4 paragraphs connecting ideas, demonstrating implications, "
        "articulating where ideas connect or diverge. Dense with specifics."
    )
    
    video_url: str
```

#### 1.4 Update GoldenNugget - Simpler Categories

**Location**: Around line 27

```python
class GoldenNugget(BaseModel):
    """A high-value insight extracted from a video."""
    content: str = Field(description="The insight - specific and actionable")
    category: Literal["technical", "business", "framework", "insight"] = Field(
        description="Category of the nugget - no emojis needed"
    )
```

---

## Phase 2: Prompt Updates

### File: `src/app/agents/daily_digest/prompts.py`

#### 2.1 Replace System Prompt

**Location**: Lines 17-56

```python
@staticmethod
def get_digest_generation_prompt() -> opik.ChatPrompt:
    """Get the master prompt for generating daily digests - V2."""
    messages: List[Dict[str, Any]] = [
        {
            "role": "system",
            "content": """You are an expert curator creating a professional intelligence brief from AI/tech video content.

YOUR GOAL: Create a daily digest that makes readers smarter. Every sentence must earn its place.

DESIGN PRINCIPLES:

TITLE
- Clear, specific, direct learning value
- NOT abstract ("The Future of AI")
- NOT hype ("Mind-Blowing Insights")
- YES specific ("Specialized AI Models Outperform General Reasoners for Niche Tasks")
- The title alone should teach something

ZERO EMOJIS
- Professional, clean, text-focused
- No emojis anywhere in the output
- Use clear section headers instead

NAVIGATION
- Provide table of contents with section titles
- Readers should jump directly to what interests them

SIGNAL DENSITY
- Cut filler phrases ("In this video...", "The speaker discusses...")
- Every sentence delivers value
- Specific over generic
- Numbers over vague claims
- Quotes over paraphrasing

COMPOUND KNOWLEDGE
- Connect ideas across videos
- Surface non-obvious patterns
- Show how frameworks from one video apply to another

PER-VIDEO DEPTH
- Condensed summary (2-3 sentences with specifics)
- Structure overview (what sections/topics covered)
- Best quotes (verbatim, attributed)
- Frameworks and mental models named
- Key statistics cited
- Analogies that make ideas stick
- Deep analysis paragraphs for those who want to unpack

IMPORTANT: Respond with valid JSON only. No additional text before or after."""
        },
        {
            "role": "user",
            "content": """DATE: {{date}}
TOTAL VIDEOS: {{video_count}}
SOURCES: {{channel_list}}

===== VIDEO ANALYSES =====
{{videos_context}}
===== END VIDEO ANALYSES =====

Based on these {{video_count}} video analyses from {{date}}, create a comprehensive daily digest.

Your response must include:

1. TITLE
   - Clear, specific statement of the day's key insight
   - Direct value - someone learns just from reading the title
   - NO emoji, NO hype, NO vague abstractions
   - Example good: "LLM Memory Architecture: Why Weights Beat Context Windows for Specialized Tasks"
   - Example bad: "The Future of AI Memory" or "Amazing AI Insights"

2. TABLE_OF_CONTENTS
   - List of section titles for navigation
   - Include: "Overview", each video title (shortened), "Actions", "References"

3. STATS
   - video_count: Number of videos
   - total_duration_minutes: Combined duration
   - estimated_read_minutes: Estimate based on ~200 words per minute
   - channels: List with channel_id, channel_name, video_count

4. DAILY_TLDR (3-4 paragraphs)
   - First sentence in italics: list the sources/channels covered
   - Connect concepts across videos
   - Surface the compound insight (1+1=3)
   - Include specific numbers, frameworks, quotes where relevant
   - Dense but readable

5. VIDEO_SECTIONS (for each video)
   - video_id, title, channel_name
   - duration_minutes: Video length
   - speakers: Main speakers if identifiable
   - tags: 3-5 topic tags
   - condensed_summary: 2-3 sentences with SPECIFIC takeaways
   - structure_overview: Brief outline of video sections
   - key_quotes: 2-3 best verbatim quotes
   - frameworks_mentioned: Names of mental models discussed
   - key_statistics: Important numbers cited
   - key_analogies: Memorable comparisons used
   - deep_analysis: 2-4 paragraphs unpacking the video's core ideas, implications, and connections
   - video_url: Link to watch

6. CONTRARIAN_CORNER
   - One insight that challenges conventional wisdom
   - Why it's counterintuitive
   - Source video

7. ACTION_ITEMS (3-5 items)
   - Concrete, specific actions
   - Context connecting to today's insights
   - Difficulty: quick / medium / deep-dive

8. REFERENCES_INDEX
   - books, papers, frameworks, concepts, people, communities
   - Each with name, author (if applicable), description

9. CONCLUSION
   - Final thought tying everything together
   - No emoji

10. KEYWORDS (8-12)
    - For categorization and search

11. CONFIDENCE_SCORE (0.0-1.0)

QUALITY STANDARDS:
- Zero emojis anywhere
- Every sentence delivers value
- Quotes must be exact from the source
- Statistics must be precise
- Frameworks must be named specifically
- Dense but scannable"""
        }
    ]

    return opik.ChatPrompt(
        name="daily-digest-generation",
        messages=messages,
        metadata={
            "category": "digest-generation",
            "output_schema": "DigestContentResponse",
            "version": "2.0",
            "focus": "clean-professional-high-signal",
            "changes": [
                "Removed all emojis",
                "Clear specific titles over catchy",
                "Added table of contents",
                "Added estimated read time",
                "Expanded video sections with V2 depth fields",
                "Added key_quotes, frameworks, statistics, analogies per video",
                "Added deep_analysis paragraphs per video",
                "Removed thumbnails",
                "Sources in italics at intro start"
            ]
        }
    )
```

#### 2.2 Update format_video_context - Include V2 Fields

**Location**: Lines 107-216

```python
@staticmethod
def format_video_context(video_data: Dict[str, Any]) -> str:
    """Format a single video's data into context for the prompt - V2.

    Now includes V2 extraction fields: quotes, frameworks, statistics, analogies, sections.
    """
    # Video metadata
    title = video_data.get("title", "Unknown Title")
    channel = video_data.get("channel_name", "Unknown Channel")
    video_id = video_data.get("video_id", "")
    duration = video_data.get("duration_seconds", 0)
    duration_mins = duration // 60 if duration else 0

    # Core analysis data
    tldr = video_data.get("tldr", "")
    key_audience = video_data.get("key_audience", "")
    core_topics = video_data.get("core_topics", [])
    lessons = video_data.get("lessons_learned", {})
    insights = video_data.get("detailed_insights", "")
    sources = video_data.get("sources_referenced", [])
    concepts = video_data.get("concepts_mentioned", [])
    people = video_data.get("people_mentioned", [])
    communities = video_data.get("communities_mentioned", [])

    # V2 extraction fields
    teaser_hooks = video_data.get("teaser_hooks", [])
    keywords = video_data.get("keywords", [])
    direct_quotes = video_data.get("direct_quotes", [])
    analogies_metaphors = video_data.get("analogies_metaphors", [])
    frameworks_shared = video_data.get("frameworks_shared", [])
    statistics_data = video_data.get("statistics_data", [])
    section_analysis = video_data.get("section_analysis", [])

    # Format topics
    topics_str = ""
    if core_topics:
        topics_str = "\n  ".join([
            f"- {t.get('topic', '')} ({t.get('category', 'general')}, {t.get('importance', 'medium')})"
            for t in core_topics
        ])

    # Format lessons
    lessons_str = ""
    if lessons:
        for category, items in lessons.items():
            if items:
                lessons_str += f"\n  {category.upper()}:\n"
                lessons_str += "\n".join([f"    - {item}" for item in items])

    # Format references
    sources_str = ""
    if sources:
        sources_str = "\n  ".join([
            f"- {s.get('title', '')} ({s.get('type', '')})"
            + (f" by {s.get('author', '')}" if s.get('author') else "")
            for s in sources
        ])

    concepts_str = ""
    if concepts:
        concepts_str = "\n  ".join([
            f"- {c.get('concept', '')}: {c.get('description', '')}"
            for c in concepts
        ])

    people_str = ""
    if people:
        people_str = "\n  ".join([
            f"- {p.get('name', '')}"
            + (f" ({p.get('role', '')})" if p.get('role') else "")
            + (f" at {p.get('affiliation', '')}" if p.get('affiliation') else "")
            for p in people
        ])

    communities_str = ""
    if communities:
        communities_str = "\n  ".join([
            f"- {c.get('name', '')} ({c.get('type', '')})"
            for c in communities
        ])

    # V2: Format teaser hooks
    teasers_str = ""
    if teaser_hooks:
        teasers_str = "\n  ".join([f"- {t}" for t in teaser_hooks])

    # V2: Format keywords/tags
    keywords_str = ", ".join(keywords) if keywords else ""

    # V2: Format direct quotes
    quotes_str = ""
    if direct_quotes:
        quotes_str = "\n  ".join([
            f'- "{q.get("quote", "")}" ({q.get("speaker", "Unknown")}) - {q.get("impact", "")}'
            for q in direct_quotes
        ])

    # V2: Format analogies
    analogies_str = ""
    if analogies_metaphors:
        analogies_str = "\n  ".join([
            f"- {a.get('analogy', '')}: explains {a.get('explains', '')}"
            for a in analogies_metaphors
        ])

    # V2: Format frameworks
    frameworks_str = ""
    if frameworks_shared:
        frameworks_str = "\n  ".join([
            f"- {f.get('name', '')}: {f.get('description', '')}"
            for f in frameworks_shared
        ])

    # V2: Format statistics
    stats_str = ""
    if statistics_data:
        stats_str = "\n  ".join([
            f"- {s.get('value', '')}: {s.get('context', '')} ({s.get('significance', '')})"
            for s in statistics_data
        ])

    # V2: Format section analysis
    sections_str = ""
    if section_analysis:
        for sec in section_analysis:
            sections_str += f"\n  [{sec.get('title', '')}]\n"
            sections_str += f"    Summary: {sec.get('summary', '')}\n"
            if sec.get('key_points'):
                for point in sec.get('key_points', []):
                    sections_str += f"    - {point}\n"

    return f"""
----- VIDEO: {video_id} -----
TITLE: {title}
CHANNEL: {channel}
DURATION: {duration_mins} minutes
VIDEO_URL: https://youtube.com/watch?v={video_id}

TLDR:
{tldr}

KEY AUDIENCE: {key_audience}

TEASER HOOKS:
  {teasers_str}

KEYWORDS/TAGS: {keywords_str}

CORE TOPICS:
  {topics_str}

LESSONS LEARNED:{lessons_str}

DETAILED INSIGHTS:
{insights}

===== V2 DEPTH EXTRACTIONS =====

DIRECT QUOTES:
  {quotes_str}

ANALOGIES & METAPHORS:
  {analogies_str}

FRAMEWORKS & MENTAL MODELS:
  {frameworks_str}

STATISTICS & DATA POINTS:
  {stats_str}

SECTION-BY-SECTION ANALYSIS:
{sections_str}

===== END V2 DEPTH =====

SOURCES REFERENCED:
  {sources_str}

CONCEPTS & FRAMEWORKS:
  {concepts_str}

PEOPLE MENTIONED:
  {people_str}

COMMUNITIES & EVENTS:
  {communities_str}
----- END VIDEO -----
"""
```

#### 2.3 Update format_all_videos_context - Add Channel List

**Location**: After format_video_context

```python
@staticmethod
def format_all_videos_context(videos: List[Dict[str, Any]]) -> tuple[str, str]:
    """Format all videos into context string and channel list.

    Args:
        videos: List of video data dicts

    Returns:
        Tuple of (combined context string, comma-separated channel list)
    """
    contexts = []
    channels_seen = set()
    
    for video in videos:
        ctx = DailyDigestPrompts.format_video_context(video)
        contexts.append(ctx)
        channels_seen.add(video.get("channel_name", "Unknown"))

    channel_list = ", ".join(sorted(channels_seen))
    return "\n".join(contexts), channel_list
```

---

## Phase 3: Node Updates

### File: `src/app/agents/daily_digest/nodes.py`

#### 3.1 Update generate_digest_node - Pass Channel List, Calculate Read Time

**Location**: Around line 167

**Add channel_list to format call:**

```python
# Format video contexts - V2 returns tuple
videos_context, channel_list = DailyDigestPrompts.format_all_videos_context(video_analyses)

# Format with variables
formatted_messages = chat_prompt.format(
    variables={
        "date": state["target_date"],
        "video_count": str(len(video_analyses)),
        "channel_list": channel_list,  # NEW
        "videos_context": videos_context,
    }
)
```

#### 3.2 Add Read Time Calculation

**Location**: After digest_content validation (around line 258)

```python
# Calculate estimated read time from formatted content
def calculate_read_time(content: DigestContentResponse) -> int:
    """Calculate estimated read time at 200 WPM."""
    word_count = 0
    
    # Count words in main sections
    word_count += len(content.daily_tldr.split())
    word_count += len(content.conclusion.split())
    
    for video in content.video_sections:
        word_count += len(video.condensed_summary.split())
        word_count += len(video.deep_analysis.split())
        word_count += len(video.structure_overview.split())
        for quote in video.key_quotes:
            word_count += len(quote.split())
    
    for action in content.action_items:
        word_count += len(action.action.split())
        word_count += len(action.context.split())
    
    # 200 words per minute, round up
    return max(1, (word_count + 199) // 200)

# Set read time
if not digest_content.stats.estimated_read_minutes:
    digest_content.stats.estimated_read_minutes = calculate_read_time(digest_content)
```

---

## Phase 4: Formatter Updates

### File: `src/app/agents/daily_digest/formatters.py`

#### 4.1 Update format_digest_markdown - Remove Emojis, Add TOC, No Thumbnails

```python
def format_digest_markdown(content: DigestContentResponse, target_date: date) -> str:
    """Format digest content as Markdown - V2 Clean Professional.

    V2 Changes:
    - No emojis
    - No thumbnails
    - Table of contents
    - Estimated read time
    - Expanded video sections with quotes, frameworks, stats
    """
    lines = []

    # Header - NO emoji
    lines.append(f"# {content.title}")
    lines.append("")
    lines.append(f"**{target_date.strftime('%B %d, %Y')}**")
    lines.append("")

    # Stats with read time
    stats = content.stats
    lines.append("---")
    lines.append(f"**{stats.video_count} videos** | **{stats.total_duration_minutes} min watch time** | **{stats.estimated_read_minutes} min read**")
    if stats.channels:
        channel_list = ", ".join([f"{c.channel_name} ({c.video_count})" for c in stats.channels])
        lines.append(f"*Sources: {channel_list}*")
    lines.append("---")
    lines.append("")

    # Table of Contents
    lines.append("## Contents")
    lines.append("")
    for i, toc_item in enumerate(content.table_of_contents):
        # Create anchor-friendly slug
        slug = toc_item.lower().replace(" ", "-").replace(":", "")
        lines.append(f"{i+1}. [{toc_item}](#{slug})")
    lines.append("")

    # Daily TLDR / Overview
    lines.append("---")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append(content.daily_tldr)
    lines.append("")

    # Video Sections - NO thumbnails
    lines.append("---")
    lines.append("")
    lines.append("## Video Breakdowns")
    lines.append("")

    for video in content.video_sections:
        lines.extend(_format_video_section_markdown_v2(video))
        lines.append("")

    # Contrarian Corner - NO emoji
    lines.append("---")
    lines.append("")
    lines.append("## Contrarian Corner")
    lines.append("")
    lines.extend(_format_contrarian_markdown_v2(content.contrarian_corner))
    lines.append("")

    # Action Items - NO emoji
    lines.append("---")
    lines.append("")
    lines.append("## Action Items")
    lines.append("")
    for item in content.action_items:
        difficulty_label = f"[{item.difficulty}]"
        lines.append(f"- **{item.action}** {difficulty_label}")
        lines.append(f"  - {item.context}")
    lines.append("")

    # References Index - NO emoji headers
    lines.append("---")
    lines.append("")
    lines.append("## References")
    lines.append("")
    lines.extend(_format_references_markdown_v2(content.references_index))
    lines.append("")

    # Conclusion - NO emoji
    lines.append("---")
    lines.append("")
    lines.append("## Final Thought")
    lines.append("")
    lines.append(f"*{content.conclusion}*")
    lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    keywords_str = " | ".join(content.keywords)
    lines.append(f"**Keywords:** {keywords_str}")
    lines.append("")

    return "\n".join(lines)


def _format_video_section_markdown_v2(video: VideoSection) -> List[str]:
    """Format a single video section - V2 with depth fields, no thumbnail."""
    lines = []

    # Title and metadata
    lines.append(f"### [{video.title}]({video.video_url})")
    lines.append(f"*{video.channel_name}* | {video.duration_minutes} min")
    if video.speakers:
        lines.append(f"*Speakers: {', '.join(video.speakers)}*")
    if video.tags:
        lines.append(f"Tags: {', '.join(video.tags)}")
    lines.append("")

    # Condensed summary
    lines.append(f"**Summary:** {video.condensed_summary}")
    lines.append("")

    # Structure overview
    if video.structure_overview:
        lines.append(f"**Structure:** {video.structure_overview}")
        lines.append("")

    # Key quotes
    if video.key_quotes:
        lines.append("**Key Quotes:**")
        for quote in video.key_quotes:
            lines.append(f'> "{quote}"')
        lines.append("")

    # Frameworks
    if video.frameworks_mentioned:
        lines.append(f"**Frameworks:** {', '.join(video.frameworks_mentioned)}")
        lines.append("")

    # Statistics
    if video.key_statistics:
        lines.append("**Key Numbers:**")
        for stat in video.key_statistics:
            lines.append(f"- {stat}")
        lines.append("")

    # Analogies
    if video.key_analogies:
        lines.append("**Analogies:**")
        for analogy in video.key_analogies:
            lines.append(f"- {analogy}")
        lines.append("")

    # Deep analysis
    lines.append("**Deep Dive:**")
    lines.append("")
    lines.append(video.deep_analysis)
    lines.append("")

    return lines


def _format_contrarian_markdown_v2(contrarian: ContrarianCorner) -> List[str]:
    """Format contrarian corner - V2 no emoji."""
    lines = []
    lines.append(f"> **{contrarian.insight}**")
    lines.append("")
    lines.append(f"*Why this challenges common wisdom:* {contrarian.why_counterintuitive}")
    return lines


def _format_references_markdown_v2(refs: ReferencesIndex) -> List[str]:
    """Format references index - V2 no emoji headers."""
    lines = []

    def format_ref_list(title: str, items: List[ReferenceItem]):
        if not items:
            return []
        result = [f"### {title}"]
        for ref in items:
            if ref.url:
                result.append(f"- [{ref.name}]({ref.url})" + (f" by {ref.author}" if ref.author else ""))
            else:
                result.append(f"- {ref.name}" + (f" by {ref.author}" if ref.author else ""))
            if ref.description:
                result.append(f"  - {ref.description}")
        result.append("")
        return result

    lines.extend(format_ref_list("Books", refs.books))
    lines.extend(format_ref_list("Papers", refs.papers))
    lines.extend(format_ref_list("Frameworks", refs.frameworks))
    lines.extend(format_ref_list("Concepts", refs.concepts))
    lines.extend(format_ref_list("People", refs.people))
    lines.extend(format_ref_list("Communities", refs.communities))

    return lines
```

#### 4.2 Update format_digest_html - Clean Professional Styling

```python
def format_digest_html(content: DigestContentResponse, target_date: date) -> str:
    """Format digest content as HTML - V2 Clean Professional.

    V2 Changes:
    - No emojis
    - No thumbnails
    - Table of contents navigation
    - Estimated read time
    - Expanded video sections
    """
    # Build TOC HTML
    toc_items = "".join([
        f'<li><a href="#{item.lower().replace(" ", "-").replace(":", "")}">{item}</a></li>'
        for item in content.table_of_contents
    ])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{content.title}</title>
    <style>
        body {{
            font-family: Georgia, 'Times New Roman', serif;
            line-height: 1.7;
            color: #1a1a1a;
            max-width: 720px;
            margin: 0 auto;
            padding: 24px;
            background-color: #fafafa;
        }}
        .container {{
            background-color: #ffffff;
            border-radius: 4px;
            padding: 40px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        }}
        h1 {{
            font-size: 26px;
            margin-bottom: 8px;
            color: #111;
            font-weight: 600;
            line-height: 1.3;
        }}
        h2 {{
            font-size: 20px;
            margin-top: 36px;
            color: #222;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 8px;
            font-weight: 600;
        }}
        h3 {{
            font-size: 17px;
            margin-top: 28px;
            color: #333;
            font-weight: 600;
        }}
        .date {{
            color: #666;
            font-size: 14px;
            margin-bottom: 16px;
        }}
        .stats {{
            background-color: #f5f5f5;
            padding: 16px 20px;
            border-radius: 4px;
            margin: 20px 0;
            border-left: 3px solid #333;
        }}
        .stats-main {{
            font-size: 15px;
            font-weight: 600;
            color: #111;
        }}
        .stats-sources {{
            font-size: 14px;
            color: #555;
            font-style: italic;
            margin-top: 6px;
        }}
        .toc {{
            background-color: #fafafa;
            padding: 16px 20px;
            border-radius: 4px;
            margin: 20px 0;
        }}
        .toc h4 {{
            margin: 0 0 10px 0;
            font-size: 14px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .toc ol {{
            margin: 0;
            padding-left: 20px;
        }}
        .toc li {{
            margin: 4px 0;
        }}
        .toc a {{
            color: #2563eb;
            text-decoration: none;
        }}
        .toc a:hover {{
            text-decoration: underline;
        }}
        .overview {{
            font-size: 16px;
            line-height: 1.8;
        }}
        .video-section {{
            border: 1px solid #e5e5e5;
            border-radius: 4px;
            padding: 24px;
            margin: 20px 0;
            background-color: #fefefe;
        }}
        .video-title {{
            font-size: 17px;
            font-weight: 600;
            color: #2563eb;
            text-decoration: none;
        }}
        .video-title:hover {{
            text-decoration: underline;
        }}
        .video-meta {{
            font-size: 14px;
            color: #666;
            margin: 6px 0;
            font-style: italic;
        }}
        .video-tags {{
            font-size: 13px;
            color: #888;
            margin: 8px 0;
        }}
        .video-summary {{
            margin: 16px 0;
            font-size: 15px;
        }}
        .quote {{
            background-color: #f9f9f9;
            border-left: 3px solid #ccc;
            padding: 12px 16px;
            margin: 12px 0;
            font-style: italic;
            color: #444;
        }}
        .frameworks, .statistics, .analogies {{
            margin: 12px 0;
            font-size: 14px;
        }}
        .deep-dive {{
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid #eee;
        }}
        .deep-dive h4 {{
            font-size: 14px;
            color: #666;
            margin-bottom: 8px;
        }}
        .contrarian {{
            background-color: #fff8f0;
            border: 1px solid #ffe0c0;
            border-radius: 4px;
            padding: 20px;
            margin: 20px 0;
        }}
        .contrarian-insight {{
            font-size: 16px;
            font-weight: 600;
            color: #8b4513;
        }}
        .action-item {{
            padding: 12px 0;
            border-bottom: 1px solid #f0f0f0;
        }}
        .action-item:last-child {{
            border-bottom: none;
        }}
        .action-title {{
            font-weight: 600;
        }}
        .action-context {{
            font-size: 14px;
            color: #666;
            margin-top: 4px;
        }}
        .difficulty {{
            display: inline-block;
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 3px;
            margin-left: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .difficulty-quick {{ background-color: #d4edda; color: #155724; }}
        .difficulty-medium {{ background-color: #fff3cd; color: #856404; }}
        .difficulty-deep-dive {{ background-color: #cce5ff; color: #004085; }}
        .references {{
            font-size: 14px;
        }}
        .ref-category {{
            margin-top: 16px;
        }}
        .ref-category h4 {{
            font-size: 14px;
            color: #666;
            margin-bottom: 8px;
            font-weight: 600;
        }}
        .conclusion {{
            font-style: italic;
            font-size: 17px;
            color: #444;
            text-align: center;
            padding: 28px 20px;
            background-color: #fafafa;
            border-radius: 4px;
            margin: 24px 0;
        }}
        .keywords {{
            text-align: center;
            font-size: 12px;
            color: #888;
            margin-top: 20px;
        }}
        .keyword {{
            display: inline-block;
            background-color: #f0f0f0;
            padding: 3px 10px;
            border-radius: 3px;
            margin: 2px;
        }}
        .footer {{
            text-align: center;
            font-size: 12px;
            color: #999;
            margin-top: 32px;
            padding-top: 16px;
            border-top: 1px solid #eee;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{content.title}</h1>
        <p class="date">{target_date.strftime('%B %d, %Y')}</p>

        <div class="stats">
            <div class="stats-main">{content.stats.video_count} videos | {content.stats.total_duration_minutes} min watch time | {content.stats.estimated_read_minutes} min read</div>
            <div class="stats-sources">Sources: {', '.join([f"{c.channel_name} ({c.video_count})" for c in content.stats.channels])}</div>
        </div>

        <div class="toc">
            <h4>Contents</h4>
            <ol>{toc_items}</ol>
        </div>

        <h2 id="overview">Overview</h2>
        <div class="overview">{_html_paragraphs(content.daily_tldr)}</div>

        <h2 id="video-breakdowns">Video Breakdowns</h2>
        {_format_videos_html_v2(content.video_sections)}

        <h2 id="contrarian-corner">Contrarian Corner</h2>
        {_format_contrarian_html_v2(content.contrarian_corner)}

        <h2 id="actions">Action Items</h2>
        {_format_actions_html_v2(content.action_items)}

        <h2 id="references">References</h2>
        <div class="references">
            {_format_references_html_v2(content.references_index)}
        </div>

        <div class="conclusion">"{content.conclusion}"</div>

        <div class="keywords">
            {' '.join([f'<span class="keyword">{kw}</span>' for kw in content.keywords])}
        </div>

        <div class="footer">
            Generated with AI | Confidence: {content.confidence_score:.0%}
        </div>
    </div>
</body>
</html>"""

    return html
```

---

## Phase 5: Repository Updates

### File: `src/app/repositories/daily_digest_repository.py`

#### 5.1 Update save_digest - Remove Emoji from Title

**Location**: Line 55

**Before:**
```python
"title": f"{content.title_emoji} {content.title}",
```

**After:**
```python
"title": content.title,  # V2: No emoji
```

---

## Phase 6: Load Data Node Updates

### File: `src/app/agents/daily_digest/nodes.py`

#### 6.1 Update load_data_node - Include V2 Fields

**Location**: Around line 100-122

Update the `video_data` dict to include V2 fields:

```python
video_data = {
    # Video metadata
    "video_id": video.id,
    "title": video.title,
    "description": video.description or "",
    "channel_id": video.channel_id,
    "channel_name": channel_name,
    "thumbnail_url": video.thumbnail_url or "",  # Still loaded but not displayed
    "duration_seconds": video.duration_seconds or 0,
    "published_at": video.published_at.isoformat() if video.published_at else "",
    "url": video.url,
    # Core analysis data
    "tldr": analysis.tldr,
    "key_audience": analysis.key_audience,
    "core_topics": analysis.core_topics,
    "lessons_learned": analysis.lessons_learned,
    "detailed_insights": analysis.detailed_insights,
    "sources_referenced": analysis.sources_referenced,
    "concepts_mentioned": analysis.concepts_mentioned,
    "people_mentioned": analysis.people_mentioned,
    "communities_mentioned": analysis.communities_mentioned,
    "confidence_scores": analysis.confidence_scores,
    # V2 extraction fields
    "teaser_hooks": getattr(analysis, 'teaser_hooks', []),
    "keywords": getattr(analysis, 'keywords', []),
    "direct_quotes": getattr(analysis, 'direct_quotes', []),
    "analogies_metaphors": getattr(analysis, 'analogies_metaphors', []),
    "frameworks_shared": getattr(analysis, 'frameworks_shared', []),
    "statistics_data": getattr(analysis, 'statistics_data', []),
    "section_analysis": getattr(analysis, 'section_analysis', []),
}
```

---

## Implementation Checklist

### Phase 1: Models (15 min)
- [ ] Add `estimated_read_minutes` to `DigestStats`
- [ ] Remove `title_emoji` from `DigestContentResponse`
- [ ] Add `table_of_contents` to `DigestContentResponse`
- [ ] Update `VideoSection` with V2 depth fields
- [ ] Update `GoldenNugget` categories (remove emoji association)

### Phase 2: Prompts (20 min)
- [ ] Replace system prompt with V2 clean professional version
- [ ] Replace user prompt with V2 structure
- [ ] Update `format_video_context()` to include V2 fields
- [ ] Update `format_all_videos_context()` to return channel list

### Phase 3: Nodes (15 min)
- [ ] Update `generate_digest_node` to pass channel_list
- [ ] Add `calculate_read_time()` function
- [ ] Update `load_data_node` to include V2 analysis fields

### Phase 4: Formatters (30 min)
- [ ] Rewrite `format_digest_markdown()` - no emojis, add TOC
- [ ] Rewrite `_format_video_section_markdown()` - no thumbnail, add depth
- [ ] Rewrite `_format_contrarian_markdown()` - no emoji
- [ ] Rewrite `_format_references_markdown()` - no emoji headers
- [ ] Rewrite `format_digest_html()` - clean professional styling
- [ ] Add corresponding HTML helper functions

### Phase 5: Repository (5 min)
- [ ] Update `save_digest()` to not include emoji in title

### Phase 6: Testing (30 min)
- [ ] Generate digest for test date
- [ ] Verify no emojis in output
- [ ] Verify no thumbnails displayed
- [ ] Verify TOC links work
- [ ] Verify read time calculated
- [ ] Verify V2 fields (quotes, frameworks, stats) appear
- [ ] Verify deep analysis paragraphs per video

---

## Expected Output Structure

### Markdown Preview

```markdown
# Specialized AI Models Outperform General Reasoners for Niche Tasks

**December 29, 2025**

---
**5 videos** | **334 min watch time** | **12 min read**
*Sources: AI Engineer, a16z, Andrew Huberman, Limitless Podcast, The Mindset Mentor*
---

## Contents

1. [Overview](#overview)
2. [Memory in LLMs](#memory-in-llms)
3. [Consumer AI 2025](#consumer-ai-2025)
...

---

## Overview

*From AI Engineer, a16z, Andrew Huberman, Limitless Podcast, and The Mindset Mentor...*

The dominant theme across today's content is the shift from... [dense paragraphs]

---

## Video Breakdowns

### [Memory in LLMs: Weights and Activations](https://youtube.com/watch?v=...)
*AI Engineer* | 63 min
*Speakers: Jack Morris*
Tags: LLM, memory, weights, activations, RAG

**Summary:** Jack Morris argues that context windows are a computational trap...

**Structure:** Introduction to the problem, Three paradigms, Technical deep dive, Q&A

**Key Quotes:**
> "128k tokens of context slows output from 10,000 to 130 tokens per second"
> "A model that knows nothing is inefficient"

**Frameworks:** Weights vs. Activations, Context Rot

**Key Numbers:**
- 10,000 → 130 tokens/sec slowdown at 128k context
- Quadratic compute cost O(n²) for self-attention

**Deep Dive:**

[2-4 paragraphs of dense analysis...]

---

## Contrarian Corner

> **Massive context windows are architectural laziness, not progress.**

*Why this challenges common wisdom:* The industry celebrates 1M+ token windows...

---

## Action Items

- **Audit your RAG pipeline for context rot** [medium]
  - Review if long contexts are degrading reasoning quality
...

---

## References

### Books
- Us: Getting Past You and Me by Terry Real

### Frameworks
- Feedback Wheel - A 4-step communication framework

...

---

## Final Thought

*Whether building AI systems or human relationships, internalization beats context injection...*

---

**Keywords:** LLM Memory | Relationality | AI ROI | Consumer AI | Accountability
```

---

## Files Summary

### Files to UPDATE

| File | Changes |
|------|---------|
| `src/app/models/daily_digest.py` | Remove title_emoji, add read_time, update VideoSection |
| `src/app/agents/daily_digest/prompts.py` | V2 prompt, format_video_context with V2 fields |
| `src/app/agents/daily_digest/nodes.py` | Channel list, read time calc, V2 field loading |
| `src/app/agents/daily_digest/formatters.py` | Complete rewrite - no emojis, no thumbnails, TOC |
| `src/app/repositories/daily_digest_repository.py` | Remove emoji from title |

### No New Files Required

All changes are updates to existing files.

---

## Dependencies

**Requires Plan 8 (Video Extraction V2) to be implemented first.**

The daily digest V2 depends on:
- `teaser_hooks`
- `keywords`
- `direct_quotes`
- `analogies_metaphors`
- `frameworks_shared`
- `statistics_data`
- `section_analysis`

If Plan 8 is not complete, the V2 fields will be empty arrays (graceful degradation via `getattr(..., [])`).

---

## Success Criteria

- [ ] Zero emojis in generated digest
- [ ] Zero thumbnails displayed
- [ ] Clear, specific title that teaches something
- [ ] Table of contents with working anchor links
- [ ] Estimated read time displayed
- [ ] Sources/channels shown in italics at top
- [ ] Each video has: quotes, frameworks, statistics, analogies
- [ ] Each video has deep analysis paragraphs
- [ ] Professional, clean typography
- [ ] Signal density - every sentence earns its place

