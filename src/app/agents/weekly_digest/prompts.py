"""Prompt management for weekly digest generation.

V2.0 - High-signal, minimalist weekly digest format.
"""

from typing import Any, Dict, List, Tuple
import opik


class WeeklyDigestPrompts:
    """Centralized prompt management for weekly digest generation."""

    CURRENT_VERSION = "2.0"

    @staticmethod
    def get_weekly_generation_prompt() -> Any:
        """Get the V2 prompt for generating weekly digests.

        Returns:
            Opik ChatPrompt configured for weekly digest generation
        """
        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": """You are synthesizing a week of daily AI/tech digests into a high-signal weekly newsletter.

## DESIGN PHILOSOPHY

### HIGH SIGNAL, NO HOMEWORK
- Extract the week's signal from the daily noise
- NO action items - readers want insight, not todos
- Every section must earn its place

### MINIMALIST STRUCTURE
- One key insight (the_one_thing)
- One essential quote
- One must-watch video
- 3 key numbers
- 1 contrarian perspective
- 1 concept worth knowing
- 2-4 themes (simplified)
- All videos grouped by category

### ZERO EMOJIS
Professional, clean, text-focused throughout.

### VIDEO CATEGORIZATION
You determine the categories based on content. Group ALL videos into 3-5 logical categories.
Examples: "AI Infrastructure", "Developer Tools", "Research & Papers", "Industry News", "Tutorials"
Each video appears in exactly one category.

## OUTPUT
Respond with valid JSON matching the schema. No text before or after the JSON."""
            },
            {
                "role": "user",
                "content": """WEEK: {{week_start}} to {{week_end}}
DAYS WITH CONTENT: {{days_with_content}}/7
TOTAL VIDEOS: {{total_videos}}

===== DAILY DIGESTS =====
{{daily_digests_context}}
===== END DAILY DIGESTS =====

===== TRENDING REFERENCES =====
{{trending_references}}
===== END TRENDING REFERENCES =====

===== AVAILABLE SOCIAL LINKS =====
{{social_links_context}}
===== END SOCIAL LINKS =====

Create a V2 weekly digest synthesizing these {{days_with_content}} days of content.

## REQUIRED SECTIONS

### 1. STATS
- total_videos, total_watch_time_minutes, estimated_read_minutes
- days_covered (how many of 7 days had content)
- channels (unique list)

### 2. TITLE & DESCRIPTION
- title: Newsletter title that captures the week's essence. Clear, specific, not generic.
  Example: "The Week AI Engineering Got Serious" or "From Vibe Coding to Spec-Driven Development"
- description: One-sentence summary for previews/SEO. What was THIS week about?
  Example: "A week dominated by the shift from ad-hoc prompting to structured AI development frameworks."

### 3. THE_ONE_THING
Pick the week's single most important insight.
- headline: Punchy, specific statement (not generic like "AI is changing")
- subtext: One sentence expanding on why this matters NOW

Example:
- headline: "The 'vibe coding' era is officially over"
- subtext: "Cursor and Windsurf proved that AI-assisted coding needs human oversight, not replacement"

### 4. QUOTE_OF_THE_WEEK
Select the most memorable verbatim quote from any video.
- text: The actual quote (must be from the content)
- speaker: Who said it
- source_video_id: Video ID where this appears

### 5. WATCH_ONE
If someone only watches ONE video this week, which one?
- video_id, title, channel, duration_minutes
- why: What makes this the essential watch (signal density, not length)

### 6. NUMBERS_THAT_MATTER (exactly 3)
Extract 3 striking statistics/numbers from the week.
- number: Formatted with unit ($100B, 75%, 45x, 10M users)
- context: The "so what" in <5 words

### 7. CONTRARIAN_TAKE
Find the most counterintuitive insight from the week.
- conventional: What most people believe
- actual: What the evidence/experts say

Example:
- conventional: "AI will replace programmers"
- actual: "AI is creating a new role: Agent Managers who orchestrate AI workflows"

### 8. CONCEPT_OF_THE_WEEK
One framework/concept worth knowing.
- term: Short name or acronym
- full_name: Expanded version (optional, if applicable)
- definition: Clear explanation in 1-2 sentences

### 9. THEMES (2-4)
Simplified themes that appeared across multiple videos:
- name: Theme label
- one_liner: Single sentence summary
- mention_count: How many videos touched this
- video_ids: Which videos (for linking)

### 10. VIDEOS_BY_CATEGORY
Group ALL videos into 3-5 categories YOU determine based on content.
Each category is a key, value is list of videos.
Each video must include: video_id, title, channel, day (Monday/Tuesday/etc), duration_minutes, one_liner

Example categories: "Agent Development", "Model Releases", "Infrastructure", "Tutorials", "Industry Analysis"

### 11. WEEKLY_NOTE
Editorial wrap-up. Personal voice, 2-3 sentences.
Tie together the week's themes. Sign off as "-- LTAI"

### 12. WEEKLY_REFERENCES
For backend/search only (not displayed in newsletter):
- name, reference_type, mention_count
- author, url, description (when available)

### 13. KEYWORDS (8-12)

### 14. CONFIDENCE_SCORE (0.0-1.0)

## QUALITY CHECKLIST
- [ ] title captures the week's essence, not generic
- [ ] description is a clear one-sentence summary
- [ ] the_one_thing is specific, not generic
- [ ] quote_of_the_week is an actual verbatim quote
- [ ] watch_one has compelling "why"
- [ ] numbers_that_matter are exactly 3 items
- [ ] contrarian_take challenges conventional wisdom
- [ ] concept_of_the_week is useful and clear
- [ ] themes are 2-4 items with video_ids populated
- [ ] videos_by_category includes ALL videos, each in exactly one category
- [ ] weekly_note has personal voice and "-- LTAI" sign-off
- [ ] Zero emojis anywhere"""
            }
        ]

        return opik.ChatPrompt(
            name="weekly-digest-generation-v2",
            messages=messages,
            metadata={
                "category": "digest-generation",
                "output_schema": "WeeklyContentResponse",
                "version": WeeklyDigestPrompts.CURRENT_VERSION,
                "focus": "high-signal-minimalist",
            }
        )

    @staticmethod
    def format_daily_digest_context(digest_data: Dict[str, Any], day_of_week: str) -> str:
        """Format a single daily digest into context for weekly prompt.

        Args:
            digest_data: Dict containing daily digest content_json
            day_of_week: Day name like "Monday", "Tuesday"

        Returns:
            Formatted string for prompt context
        """
        content = digest_data.get("content_json", {})
        if not content or content.get("empty"):
            return f"\n----- {day_of_week.upper()} -----\n[No content this day]\n"

        title = content.get("title", "Untitled")
        stats = content.get("stats", {})
        video_count = stats.get("video_count", 0)
        duration = stats.get("total_duration_minutes", 0)

        # Get bullets and deeper picture for synthesis
        big_picture = content.get("big_picture_bullets", [])
        bullets_str = "\n".join([f"  - {b}" for b in big_picture[:5]]) if big_picture else ""

        deeper = content.get("deeper_picture", "")[:500] if content.get("deeper_picture") else ""

        # Get video sections for episode snapshots
        videos = content.get("video_sections", [])
        videos_str = ""
        for v in videos:
            vid_id = v.get("video_id", "")
            vid_title = v.get("title", "")
            channel = v.get("channel_name", "")
            duration_min = v.get("duration_minutes", 0)
            summary = v.get("condensed_summary", "")[:200]
            flow = v.get("logical_flow", [])[:4]
            speakers = v.get("speakers", [])

            speakers_str = ""
            if speakers:
                speaker_parts = []
                for s in speakers:
                    if isinstance(s, dict):
                        name = s.get("name", "")
                        twitter = s.get("twitter_url", "")
                        youtube = s.get("youtube_url", "")
                        if twitter:
                            speaker_parts.append(f"{name} (Twitter: {twitter})")
                        elif youtube:
                            speaker_parts.append(f"{name} (YouTube: {youtube})")
                        else:
                            speaker_parts.append(name)
                    else:
                        speaker_parts.append(str(s))
                speakers_str = f"Speakers: {', '.join(speaker_parts)}"

            videos_str += f"""
    VIDEO: {vid_id}
    Title: {vid_title}
    Channel: {channel}
    Duration: {duration_min} min
    {speakers_str}
    Flow: {' -> '.join(flow)}
    Summary: {summary}
"""

        # Get action items
        actions = content.get("action_items", [])
        actions_str = ""
        for a in actions:
            action_text = a.get("action", "")
            difficulty = a.get("difficulty", "")
            first_step = a.get("first_step", "")
            actions_str += f"\n    - [{difficulty}] {action_text}"
            if first_step:
                actions_str += f" (First: {first_step})"

        # Get references
        refs = content.get("references_index", {})
        refs_str = ""
        for ref_type, ref_list in refs.items():
            if ref_list:
                refs_str += f"\n    {ref_type}: {', '.join([r.get('name', '') for r in ref_list[:5]])}"

        return f"""
----- {day_of_week.upper()} ({video_count} videos, {duration} min) -----
TITLE: {title}

BIG PICTURE:
{bullets_str}

DEEPER PICTURE:
{deeper}

VIDEOS:{videos_str}

ACTION ITEMS:{actions_str}

REFERENCES:{refs_str}
----- END {day_of_week.upper()} -----
"""

    @staticmethod
    def format_all_daily_contexts(
        digests: List[Dict[str, Any]]
    ) -> Tuple[str, int, int, Dict[str, Dict[str, str]]]:
        """Format all daily digests into context.

        Args:
            digests: List of daily digest data dicts ordered by date

        Returns:
            Tuple of (combined context, days_with_content, total_videos, social_links_map)
        """
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        contexts = []
        days_with_content = 0
        total_videos = 0
        social_links = {}  # name -> {twitter: url, linkedin: url}

        for i, digest in enumerate(digests):
            day_name = day_names[i % 7]
            content = digest.get("content_json", {})

            if content and not content.get("empty"):
                days_with_content += 1
                stats = content.get("stats", {})
                total_videos += stats.get("video_count", 0)

                # Aggregate social links from speakers
                for video in content.get("video_sections", []):
                    for speaker in video.get("speakers", []):
                        if isinstance(speaker, dict):
                            name = speaker.get("name", "")
                            if name:
                                if name not in social_links:
                                    social_links[name] = {}
                                if speaker.get("twitter_url"):
                                    social_links[name]["twitter"] = speaker["twitter_url"]
                                if speaker.get("youtube_url"):
                                    social_links[name]["youtube"] = speaker["youtube_url"]
                                if speaker.get("linkedin_url"):
                                    social_links[name]["linkedin"] = speaker["linkedin_url"]

            ctx = WeeklyDigestPrompts.format_daily_digest_context(digest, day_name)
            contexts.append(ctx)

        return "\n".join(contexts), days_with_content, total_videos, social_links

    @staticmethod
    def format_trending_references(references: List[Dict[str, Any]]) -> str:
        """Format trending references for prompt context.

        Args:
            references: List of reference dicts with mention counts

        Returns:
            Formatted string for prompt
        """
        if not references:
            return "No trending references this week."

        lines = []
        for ref in references[:15]:
            name = ref.get("name", "")
            ref_type = ref.get("reference_type", "")
            mentions = ref.get("mention_count", 1)
            author = ref.get("author", "")
            url = ref.get("url", "")

            line = f"- {name} ({ref_type}, {mentions}x)"
            if author:
                line += f" by {author}"
            if url:
                line += f" [{url}]"
            lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def format_social_links(social_links: Dict[str, Dict[str, str]]) -> str:
        """Format aggregated social links for prompt context.

        Args:
            social_links: Dict of name -> {platform: url}

        Returns:
            Formatted string for prompt
        """
        if not social_links:
            return "No social links available."

        lines = []
        for name, links in social_links.items():
            parts = []
            if links.get("twitter"):
                parts.append(f"Twitter: {links['twitter']}")
            if links.get("youtube"):
                parts.append(f"YouTube: {links['youtube']}")
            if links.get("linkedin"):
                parts.append(f"LinkedIn: {links['linkedin']}")
            if parts:
                lines.append(f"- {name}: {', '.join(parts)}")

        return "\n".join(lines) if lines else "No social links available."
