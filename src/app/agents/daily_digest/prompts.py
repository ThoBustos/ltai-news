"""Prompt management for daily digest generation using Opik ChatPrompt - V2.0."""

from typing import Any, Dict, List, Tuple
import opik


class DailyDigestPrompts:
    """Centralized prompt management for digest generation."""

    CURRENT_VERSION = "2.0"

    @staticmethod
    def get_digest_generation_prompt() -> Any:  # Returns opik.ChatPrompt (not typed)
        """Get the master prompt for generating daily digests - V2.

        Returns:
            Opik ChatPrompt configured for digest generation
        """
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
- Connections to other videos in this digest

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
   - connections: How this video relates to others in this digest
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
                "version": DailyDigestPrompts.CURRENT_VERSION,
                "focus": "clean-professional-high-signal",
                "changes": [
                    "Removed all emojis",
                    "Clear specific titles over catchy",
                    "Added table of contents",
                    "Added estimated read time",
                    "Expanded video sections with V2 depth fields",
                    "Added key_quotes, frameworks, statistics, analogies per video",
                    "Added deep_analysis paragraphs per video",
                    "Added cross-video connections",
                    "Removed thumbnails",
                    "Sources in italics at intro start"
                ]
            }
        )

    @staticmethod  # type: ignore[arg-type]
    def format_video_context(video_data: Dict[str, Any]) -> str:
        """Format a single video's data into context for the prompt - V2.

        Now includes V2 extraction fields: quotes, frameworks, statistics, analogies, sections.

        Args:
            video_data: Dict containing video metadata and analysis

        Returns:
            Formatted string for prompt context
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

    @staticmethod  # type: ignore[arg-type]
    def format_all_videos_context(videos: List[Dict[str, Any]]) -> Tuple[str, str]:
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
