"""Prompt management for daily digest generation using Opik ChatPrompt - V2.2."""

from typing import Any, Dict, List, Tuple
import opik


class DailyDigestPrompts:
    """Centralized prompt management for digest generation."""

    CURRENT_VERSION = "2.2"

    @staticmethod
    def get_digest_generation_prompt() -> Any:  # Returns opik.ChatPrompt (not typed)
        """Get the master prompt for generating daily digests - V2.2.

        Returns:
            Opik ChatPrompt configured for digest generation
        """
        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": """You are an expert curator creating a professional intelligence brief from AI/tech video content.

YOUR GOAL: Create a daily digest that makes readers smarter. Every sentence must earn its place.

## DESIGN PRINCIPLES

### LAYERED READING
Readers have different time budgets. Support all of them:
- 30-second scan: big_picture_bullets (skimmable bullets)
- 3-5 minute read: deeper_picture (connected synthesis)
- 15+ minute deep dive: video_sections (full analysis)

### TITLE
- Clear, specific, direct learning value
- NOT abstract ("The Future of AI")
- NOT hype ("Mind-Blowing Insights")
- YES specific ("Context Windows Fail at 700k Tokens: Why Orchestration Beats Model Scale")
- The title alone should teach something

### ZERO EMOJIS
Professional, clean, text-focused. No emojis anywhere in the output.

### ENTITY LINKING (ENHANCED)
When social links are available in the video context, **ALWAYS USE THEM**:
- Check the AVAILABLE SOCIAL LINKS section in each video's context
- If a person has twitter/x link → embed as [Name](twitter_url)
- If a person has youtube link → embed as [Name](youtube_url)
- Apply linking in ALL sections: big_picture_bullets, deeper_picture, contrarian_corner, key_tensions, convergence_points

**RULES**:
- If social_links provided in video context → USE them as markdown links
- If no social_links → plain text name (don't guess)
- Do NOT guess handles or URLs based on name recognition
- Do NOT use "well-known" lists for handles or company URLs
- Reuse tool/product URLs, GitHub repos, arXiv links when mentioned

Format when link IS available:
- People: "[Sam Altman](https://x.com/sama)" or "[Alex Hormozi](https://youtube.com/@AlexHormozi)"
- Channels: "[Channel](https://youtube.com/@channel)"
- Companies: "[Company](https://company.com)"
- Papers: "[Paper Title](https://arxiv.org/abs/...)"
- Tools: "[Tool Name](https://tool.com)"
- Video sections: "[Speaker Name](#video-{video_id})" for linking to video section in digest

### SIGNAL DENSITY
- Cut filler phrases ("In this video...", "The speaker discusses...")
- Every sentence delivers value
- Specific over generic
- Numbers over vague claims
- Quotes over paraphrasing

### COMPOUND KNOWLEDGE
- Connect ideas across videos
- Surface non-obvious patterns
- Show how frameworks from one video apply to another
- Identify CONVERGENCE (multiple videos agree) and TENSIONS (videos disagree)

### CONNECTIONS MUST BE SPECIFIC
NOT: "Relates to other AI topics"
NOT: "Connects to Andy's talk"
YES: "**Extends** Konwinski's post-post-training thesis by providing the failure data"
YES: "**Contradicts** the bigger-context-window marketing with hard numbers"
YES: "**Deepens** Yang's benchmark critique by showing production implications"

### FORMATTING
- Use **bold** for key terms and framework names on first mention
- Use *italics* for video titles: *The State of Context Engineering*
- In connections and action_items, bold the relationship type

## OUTPUT
Respond with valid JSON matching the schema. No text before or after the JSON."""
            },
            {
                "role": "user",
                "content": """DATE: {{date}}
TOTAL VIDEOS: {{video_count}}
SOURCES: {{channel_list}}

===== VIDEO ANALYSES =====
{{videos_context}}
===== END VIDEO ANALYSES =====

Create a comprehensive daily digest from these {{video_count}} video analyses.

## REQUIRED SECTIONS

### 1. TITLE
Specific learning statement. Someone learns just from reading it.

### 2. TABLE_OF_CONTENTS
List of section titles for navigation.

### 3. STATS
- video_count, total_duration_minutes, estimated_read_minutes
- channels: List with channel_id, channel_name, video_count

### 4. BIG_PICTURE_BULLETS
- Generate 1-2 bullets per video ({{video_count}} videos → ~{{video_count}}-{{video_count}} x 2 bullets)
- Can merge related concepts from multiple videos into single bullet
- Each bullet is ONE complete insight with specific numbers/names
- Format: "**Key concept** — specific insight with [entity](link) when known"
- Link speaker/channel names to their video sections using anchor format: [Name](#video-{video_id})

Example bullets (entity links shown only if handle was in video context):
- **Orchestration is the new moat** — [Andy Konwinski](#video-abc123) argues models are commoditizing; the defensible layer is context management and outcome data
- **Context windows cliff at 700k tokens** — [Nina Lopatina](https://x.com/nina_lopatina)'s research shows retrieval accuracy drops from 90% to 30%

### 5. DEEPER_PICTURE
- 2-6 paragraphs (scale with video count: 1-3 videos → 2-3 paragraphs, 4-7 videos → 3-4 paragraphs, 8+ videos → 4-6 paragraphs)
- Connect concepts across videos using cause-effect chains
- Use **bold** for key terms
- DO NOT list sources separately at the beginning (no "*Sources: Channel 1, Channel 2...*")
- EMBED video links inline using format: *[Video Title](video_url)*
- Example: "In *[72 Hours with Alex Hormozi](https://youtube.com/watch?v=xyz)*, we see..."
- Every video title mention should be a clickable link to the actual video URL
- Include specific numbers, frameworks, quotes

### 6. CONVERGENCE_POINTS
Identify concepts mentioned by multiple videos (0-4 items):
- concept: The shared theme
- video_ids: ["id1", "id2", ...]
- video_titles: ["Title 1", "Title 2", ...]
- synthesis: 2-3 sentences on how videos together illuminate this

**IMPORTANT**: Empty list is valid if no genuine convergence exists. Do NOT force connections.

### 7. KEY_TENSIONS
Identify points where videos disagree (0-3 items):
- topic: The contested topic
- perspectives: [{position, video_id, video_title, speaker}]
- resolution: How to reconcile (can be null if unresolved)

**IMPORTANT**: Empty list is valid if no genuine disagreement exists. Do NOT invent tensions.

### 8. VIDEO_SECTIONS
For EACH of the {{video_count}} videos, generate:
- video_id, title, channel_name, duration_minutes, tags
- speakers: List of Speaker objects with name and social links when known from video context
  Example: [{"name": "Alex Hormozi", "twitter_url": "https://x.com/AlexHormozi", "youtube_url": "https://youtube.com/@AlexHormozi"}]
  Only include social URLs that were explicitly in the video context. Set to null if unknown.

- logical_flow: 4-6 concepts showing the intellectual journey (NO ARROWS in data - frontend adds arrows)
  BAD: ["AI", "ML", "LLMs", "Future"]
  BAD: ["→ Problem", "→ Evidence", "→ Solution"]
  GOOD: ["Problem: context collapse", "700k token evidence", "Agentic RAG proposal", "Sub-agent turn limits"]

- condensed_summary: 2-3 sentences with SPECIFIC takeaways
- structure_overview: Brief outline
- key_quotes: 2-3 best verbatim quotes
- frameworks_mentioned, key_statistics, key_analogies
- deep_analysis: 2-4 paragraphs with implications

- connections: List using **Extends**/**Contradicts**/**Deepens** pattern
  BAD: "Related to AI topics"
  GOOD: "**Extends** Konwinski's thesis by showing the failure mode at 700k tokens"

- video_url

### 9. CONTRARIAN_CORNER
- insight: The counterintuitive idea
- source_video_id: Video ID
- source_video_title: Video title for attribution
- why_counterintuitive: Why this challenges common wisdom
- so_what: What should reader DO differently? Concrete action.
  BAD: "Think about benchmarks differently"
  GOOD: "When evaluating AI tools, ask vendors: 'What's your score on the impossible subset?'"

### 10. ACTION_ITEMS (3-5)
- action: What to do
- context: Why/how it connects
- difficulty: quick | medium | deep-dive
- source_video_id: Which video
- source_video_title: For attribution
- first_step: Concrete immediate action
  BAD: "Implement better context management"
  GOOD: "Run your RAG at 50%, 70%, 90% utilization. Measure retrieval accuracy at each tier."

### 11. REFERENCES_INDEX
Group by type (books, papers, frameworks, concepts, people, communities).
For people, include social_links dict when known from the video context.

### 12. CONCLUSION
Final thought tying everything together. Professional tone, no emoji.

### 13. KEYWORDS (8-12)
For categorization and search.

### 14. CONFIDENCE_SCORE (0.0-1.0)

### 15. DAILY_TLDR (legacy - can be empty)
If big_picture_bullets is populated, this can be empty string.

## QUALITY CHECKLIST
Before outputting, verify:
- [ ] big_picture_bullets has ~1-2 per video with #video-{id} anchor links for speakers
- [ ] deeper_picture uses inline *[Video Title](url)* links (NO separate "Sources:" line)
- [ ] Each video has logical_flow showing journey (NOT buzzwords, NO arrows in data)
- [ ] speakers are Speaker objects with social links when available from context
- [ ] contrarian_corner has so_what
- [ ] Each action_item has first_step
- [ ] connections use Extends/Contradicts/Deepens
- [ ] Entity links used EVERYWHERE social_links are available in context"""
            }
        ]

        return opik.ChatPrompt(
            name="daily-digest-generation",
            messages=messages,
            metadata={
                "category": "digest-generation",
                "output_schema": "DigestContentResponse",
                "version": DailyDigestPrompts.CURRENT_VERSION,
                "focus": "layered-scannable-actionable",
                "changes": [
                    "V2.2: Fixed logical_flow - NO arrows in data (frontend renders them)",
                    "V2.2: Added channel_url to ChannelStat (programmatically populated)",
                    "V2.2: Deeper picture uses inline video links (no separate Sources line)",
                    "V2.2: Big picture bullets link speakers to video sections (#video-id anchors)",
                    "V2.2: Speaker model with social links (BREAKING: List[str] → List[Speaker])",
                    "V2.2: Enhanced entity linking - prominent social links section in context",
                    "V2.2: Entity linking applied throughout (bullets, deeper_picture, etc.)",
                    "V2.1: Added layered reading (big_picture_bullets + deeper_picture)",
                    "V2.1: Added convergence_points for cross-video consensus",
                    "V2.1: Added key_tensions for cross-video disagreements",
                    "V2.1: Added logical_flow per video (intellectual journey)",
                    "V2.1: Enhanced contrarian_corner with so_what",
                    "V2.1: Enhanced action_items with first_step",
                    "V2.1: Added entity linking with strict policy (only from context)",
                    "V2.1: Added social_links support for people/communities",
                    "V2.1: Connections use Extends/Contradicts/Deepens pattern",
                    "V2: Removed all emojis",
                    "V2: Clear specific titles",
                    "V2: Added table of contents",
                    "V2: Added estimated read time",
                    "V2: Expanded video sections with depth fields"
                ]
            }
        )

    @staticmethod  # type: ignore[arg-type]
    def format_video_context(video_data: Dict[str, Any]) -> str:
        """Format a single video's data into context for the prompt - V2.2.

        V2.2: Added prominent AVAILABLE SOCIAL LINKS section for better entity linking.
        V2: Includes extraction fields: quotes, frameworks, statistics, analogies, sections.

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

        # V2: Format people with social links
        people_str = ""
        social_links_for_prompt = []  # V2.2: Collect for prominent section
        if people:
            lines = []
            for p in people:
                name = p.get('name', 'Unknown')
                role = p.get('role', '')
                affiliation = p.get('affiliation', '')
                context = p.get('context', '')
                social = p.get('social_links', {})

                line = f"- {name}"
                if role:
                    line += f" ({role})"
                if affiliation:
                    line += f" at {affiliation}"

                # Add social links when available
                social_parts = []
                if social.get('twitter'):
                    social_parts.append(f"Twitter: {social['twitter']}")
                if social.get('linkedin'):
                    social_parts.append(f"LinkedIn: {social['linkedin']}")
                if social.get('website'):
                    social_parts.append(f"Web: {social['website']}")

                if social_parts:
                    line += f" [{', '.join(social_parts)}]"
                if context:
                    line += f" — {context}"

                lines.append(line)

                # V2.2: Collect social links for prominent section
                if social:
                    link_parts = []
                    if social.get('twitter'):
                        link_parts.append(f"Twitter: {social['twitter']}")
                    if social.get('linkedin'):
                        link_parts.append(f"LinkedIn: {social['linkedin']}")
                    if social.get('website'):
                        link_parts.append(f"Web: {social['website']}")
                    if link_parts:
                        social_links_for_prompt.append(f"- {name}: {', '.join(link_parts)}")

            people_str = "\n  ".join(lines)

        # V2.2: Format prominent social links section
        social_links_section = ""
        if social_links_for_prompt:
            social_links_section = "\n".join(social_links_for_prompt)

        # V2: Format communities with URLs
        communities_str = ""
        if communities:
            lines = []
            for c in communities:
                name = c.get('name', '')
                ctype = c.get('type', '')
                desc = c.get('description', '')
                url = c.get('url', '')

                line = f"- {name} ({ctype})"
                if desc:
                    line += f" — {desc}"
                if url:
                    line += f" → {url}"
                lines.append(line)
            communities_str = "\n  ".join(lines)

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

        # V2.2: Build prominent social links block
        social_links_block = ""
        if social_links_section:
            social_links_block = f"""
=== AVAILABLE SOCIAL LINKS (USE THESE IN OUTPUT) ===
{social_links_section}
=== END SOCIAL LINKS ===
"""

        return f"""
----- VIDEO: {video_id} -----
TITLE: {title}
CHANNEL: {channel}
DURATION: {duration_mins} minutes
VIDEO_URL: https://youtube.com/watch?v={video_id}
{social_links_block}
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
