"""Prompt management for daily digest generation using Opik ChatPrompt - V2.2."""

from typing import Any, Dict, List, Tuple
import opik


class DailyDigestPrompts:
    """Centralized prompt management for digest generation."""

    @staticmethod
    def get_digest_generation_prompt_v2() -> Any:  # Returns opik.ChatPrompt (not typed)
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
IMPORTANT: Each item must be an object with "name" and optional fields, NOT a plain string.

Example format:
```json
{
  "books": [{"name": "Thinking Fast and Slow", "author": "Daniel Kahneman", "description": "Cognitive biases"}],
  "papers": [{"name": "Attention Is All You Need", "author": "Vaswani et al.", "url": "https://arxiv.org/..."}],
  "frameworks": [{"name": "RAG", "description": "Retrieval-augmented generation"}],
  "concepts": [{"name": "Continuous Pre-training", "description": "Training on new data without forgetting"}],
  "people": [{"name": "Andrej Karpathy", "description": "AI researcher", "social_links": {"twitter": "https://x.com/karpathy"}}],
  "communities": [{"name": "Hacker News", "url": "https://news.ycombinator.com"}]
}
```
BAD: "concepts": ["Concept1", "Concept2"]  ← plain strings will fail validation
GOOD: "concepts": [{"name": "Concept1", "description": "..."}, {"name": "Concept2"}]

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
            name="daily-digest-generation-v2.2",
            messages=messages,
            metadata={
                "category": "digest-generation",
                "output_schema": "DigestContentResponse",
                "version": "2.2",
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

    @staticmethod
    def get_digest_generation_prompt_v3() -> Any:  # Returns opik.ChatPrompt (not typed)
        """Get the master prompt for generating daily digests - V3.0 minimalist format."""
        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": """You are an expert curator creating a minimalist intelligence brief from AI/tech video content.

YOUR GOAL: Distill what actually mattered today. Short, specific, no filler. Every sentence earns its place.

## RULES

### ZERO EM DASHES
This is a hard rule. No em dashes (—) anywhere in the output. Not in title, not in intro, not in framing, not in bullets. Use a colon, comma, or new line instead.

### ZERO EMOJIS
Professional, clean, text-focused.

### INTRO STYLE
Staccato short sentences. Each on its own line. Not paragraphs. Name specific people, products, numbers.
Bad: "Today's videos covered a range of important AI developments."
Good:
Three channels said it today.
None of them coordinated.
That's the signal.

Gemini Flash pricing dropped again.
Cursor hit $500M ARR.
Karpathy was right about pipelines.

### ENTITY LINKING
Only use URLs that are explicitly present in the video context. Do not guess handles or domains. If a URL is available, include it in parentheses after the name: "Andrej Karpathy (x.com/karpathy)". If not available, plain text name only.

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

Create a minimalist daily digest from these {{video_count}} video analyses.

## REQUIRED FIELDS

### title
One punchy sentence. The most important thing today. No em dashes. Not abstract.

### meta
Format exactly: "Month D · N videos" — e.g. "March 4 · 6 videos"

### intro
Staccato short sentences, each on its own line (use \\n). Name specific people, products, numbers. No em dashes. No "In this issue..." opener.

### pull_quote
One verbatim quote from the day that genuinely stands out. Null if none qualifies. Do not force.

### video_sections
For EACH of the {{video_count}} videos:
- video_id, title, channel_name, duration_minutes, video_url
- speaker: primary speaker name (single string, e.g. "Andrej Karpathy")
- framing: 1-2 sentences. What the video is about. Who is speaking. Why it matters today. No em dashes.
- bullets: 4-8 points. Each is one complete thought with specific names, numbers, or claims. No em dashes.

### references
Three flat lists:
- people: names mentioned, with URL in parens if available from context
- tools: tools/products/frameworks mentioned, with URL in parens if available
- papers: papers mentioned

### keywords
6-10 keywords for search.

### confidence_score
0.0-1.0"""
            }
        ]

        return opik.ChatPrompt(
            name="daily-digest-generation-v3.0",
            messages=messages,
            metadata={
                "category": "digest-generation",
                "output_schema": "DigestContentResponseV3",
                "version": "3.0",
                "focus": "minimalist-staccato",
                "changes": [
                    "V3: Minimalist format — title, meta, intro, pull_quote, video_sections, references",
                    "V3: No em dashes enforced hard",
                    "V3: Staccato intro (each sentence on own line)",
                    "V3: Per-video: framing + bullets only (no deep_analysis, key_quotes, etc.)",
                    "V3: References are flat string lists (people, tools, papers)",
                    "V3: No stats, no action_items, no contrarian_corner, no convergence",
                ]
            }
        )

    @staticmethod
    def format_compact_video(video_data: Dict[str, Any]) -> str:
        """Format a single video analysis into a compact summary (~400 tokens).

        Used by compress_videos_node to reduce context before digest generation.
        Extracts essential fields only — ~10x smaller than format_video_context.

        Args:
            video_data: Full video analysis dict from load_data_node

        Returns:
            Compact formatted string for use as digest generation context
        """
        video_id = video_data.get("video_id", "")
        title = video_data.get("title", "")
        channel = video_data.get("channel_name", "")
        duration = (video_data.get("duration_seconds", 0) or 0) // 60
        url = f"https://youtube.com/watch?v={video_id}"
        tldr = video_data.get("tldr", "")

        # Top 5 key points from lessons_learned
        lessons = video_data.get("lessons_learned", {}) or {}
        key_points: List[str] = []
        for items in lessons.values():
            if isinstance(items, list):
                key_points.extend(str(i) for i in items)
        key_points = key_points[:5]

        # Best direct quote
        quotes = video_data.get("direct_quotes", []) or []
        best_quote = ""
        if quotes:
            q = quotes[0]
            if isinstance(q, dict):
                best_quote = f'"{q.get("quote", "")}" — {q.get("speaker", "")}'

        # Framework names
        frameworks = video_data.get("frameworks_shared", []) or []
        fw_names = [f.get("name", "") for f in frameworks if isinstance(f, dict) and f.get("name")]

        # Key stats (top 3)
        stats = video_data.get("statistics_data", []) or []
        stat_strs = [
            f"{s.get('value', '')}: {s.get('context', '')}"
            for s in stats[:3] if isinstance(s, dict)
        ]

        # People with social URLs when available
        people = video_data.get("people_mentioned", []) or []
        people_strs = []
        for p in people[:5]:
            if not isinstance(p, dict):
                continue
            name = p.get("name", "")
            social = p.get("social_links") or {}
            url_part = social.get("twitter") or social.get("website") or ""
            people_strs.append(f"{name} ({url_part})" if url_part else name)

        lines = [f"--- VIDEO: {video_id} ---"]
        lines.append(f"TITLE: {title}")
        lines.append(f"CHANNEL: {channel} | DURATION: {duration}m | URL: {url}")
        lines.append(f"TLDR: {tldr}")
        if key_points:
            lines.append("KEY POINTS:")
            lines.extend(f"  - {p}" for p in key_points)
        if best_quote:
            lines.append(f"QUOTE: {best_quote}")
        if fw_names:
            lines.append(f"FRAMEWORKS: {', '.join(fw_names)}")
        if stat_strs:
            lines.append("STATS:")
            lines.extend(f"  - {s}" for s in stat_strs)
        if people_strs:
            lines.append(f"PEOPLE: {', '.join(people_strs)}")
        lines.append("--- END VIDEO ---")
        return "\n".join(lines)

    @staticmethod
    def format_compact_videos_context(video_summaries: List[str]) -> Tuple[str, str]:
        """Join compact video summaries and extract channel list.

        Drop-in replacement for format_all_videos_context used by write_digest_node.
        The channel list is derived from the summaries (CHANNEL: field).

        NOTE: Tightly coupled to the text layout produced by format_compact_video().
        Parses lines starting with "CHANNEL:" and splits on "|".
        If format_compact_video() changes its output format, update this parser too.

        Args:
            video_summaries: List of compact strings from compress_videos_node

        Returns:
            Tuple of (combined context string, comma-separated channel list)
        """
        channels_seen: set = set()
        for summary in video_summaries:
            for line in summary.splitlines():
                if line.startswith("CHANNEL:"):
                    # "CHANNEL: ChannelName | DURATION: ..."
                    channel_part = line.split("|")[0].replace("CHANNEL:", "").strip()
                    if channel_part:
                        channels_seen.add(channel_part)
        channel_list = ", ".join(sorted(channels_seen))
        return "\n\n".join(video_summaries), channel_list

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
                for t in core_topics if t
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
                for s in sources if s
            ])

        concepts_str = ""
        if concepts:
            concepts_str = "\n  ".join([
                f"- {c.get('concept', '')}: {c.get('description', '')}"
                for c in concepts if c
            ])

        # V2: Format people with social links
        people_str = ""
        social_links_for_prompt = []  # V2.2: Collect for prominent section
        if people:
            lines = []
            for p in people:
                if not p:
                    continue
                name = p.get('name', 'Unknown')
                role = p.get('role', '')
                affiliation = p.get('affiliation', '')
                context = p.get('context', '')
                social = p.get('social_links') or {}

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
                if not c:
                    continue
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
