"""Prompt management for X thread generation using Opik ChatPrompt."""

from typing import Any, Dict, List
import opik


class XThreadPrompts:
    """Centralized prompt management for X thread generation."""

    CURRENT_VERSION = "1.0"

    @staticmethod
    def get_thread_prompt() -> Any:  # Returns opik.ChatPrompt
        """Get the master prompt for generating X threads from digest.

        Returns:
            Opik ChatPrompt configured for thread generation
        """
        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": """Generate an X thread for Thomas Bustos's AI newsletter digest.

GOAL: Scannable thread with all video links. Drive traffic to digest.
AUDIENCE: CTOs, AI engineers, technical founders
VOICE: Authentic, simple. Sound like Thomas sharing cool stuff.

FORMAT:

Tweet 1 - Stats + Pattern:
Last 24h
{count} videos | {channels} channels | ~{hours}h
Core pattern: {pattern}
Thread 👇

Tweets 2-N - Videos by channel:
📺 @handle
"Quote" OR Concept → Concept → Concept
{title}: {url}

(Multi-video channels: bullet list with quotes)

Final Tweet:
Full digest: thomasbustos.com/ltai-news/{date}
Thoughts?

RULES:
- Each tweet ≤280 chars
- Include ALL video links
- Use provided key_quotes and logical_flow context when available
- Core pattern: ONE simple insight if genuine, else skip
- Truncate quotes/flows to fit 280 char limit
- Tag @handles when available
- Sound human, not AI

CONTEXT USAGE:
- Single video: Use quote OR flow OR both (if space)
- Multi-video: One short quote per video, skip flows
- Truncate with "..." if needed

OUTPUT: Valid JSON with thread_tweets array.
Tweet 1: Stats + pattern + "Thread 👇"
Tweets 2-N: Videos by channel
Final: Digest link + question"""
            },
            {
                "role": "user",
                "content": """DATE: {{date}}
DIGEST TITLE: {{title}}
VIDEO COUNT: {{video_count}}

===== TOP INSIGHTS =====
{{big_picture_bullets}}

===== VIDEOS BY CHANNEL =====
{{videos_by_channel}}

===== AVAILABLE X HANDLES =====
{{channel_handles}}

Generate a light, scannable X thread that:
1. Opens with stats (video count, channels, duration estimate) + core pattern if genuine
2. Lists all videos grouped by channel with all links visible
3. Ends with digest link + simple question

Keep it authentic and light - this is a daily update, not a major announcement.

Return JSON:
{
  "thread_tweets": [
    "1/ Last 24h\\n\\n9 videos | 3 channels | ~4.5 hours content\\n\\nCore pattern: Orchestration > scale\\n\\nThread 👇",
    "2/ 📺 @latentspacepod\\nYi Tay: Why RL beats imitation\\nhttps://youtube.com/watch?v=...",
    "3/ 📺 @wandb (3 videos)\\n• Finance doc workflows: https://...\\n• Eval systems: https://...\\n• Support AI: https://...",
    "4/ Full digest: thomasbustos.com/ltai-news/{{date}}\\n\\nThoughts?"
  ]
}"""
            }
        ]

        prompt = opik.ChatPrompt(
            name="x-thread-generation",
            messages=messages,
            metadata={
                "category": "thread-generation",
                "version": XThreadPrompts.CURRENT_VERSION,
                "output_schema": "XThreadResponse",
            }
        )

        return prompt

    @staticmethod
    def format_video_context(
        date: str,
        title: str,
        video_count: int,
        big_picture_bullets: List[str],
        videos_by_channel: Dict[str, List[Dict[str, str]]],
        contrarian_corner: str,
        channel_handles: Dict[str, str]
    ) -> Dict[str, str]:
        """Format context for thread generation prompt.

        Args:
            date: Digest date (YYYY-MM-DD)
            title: Digest title
            video_count: Number of videos in digest
            big_picture_bullets: Top insights from digest
            videos_by_channel: Dict mapping channel name to list of videos
            contrarian_corner: Contrarian take from digest
            channel_handles: Dict mapping channel name to X handle

        Returns:
            Dict with formatted template variables
        """
        # Format big picture bullets
        bullets_text = "\n".join(f"- {bullet}" for bullet in big_picture_bullets)

        # Format videos by channel
        videos_text = []
        for channel_name, videos in videos_by_channel.items():
            handle = channel_handles.get(channel_name, channel_name)
            videos_text.append(f"\n{handle}:")
            for video in videos:
                videos_text.append(f"  • {video['title']}")
                videos_text.append(f"    {video['url']}")

                # Add quotes if available (limit to first 2 and truncate long quotes)
                if video.get('key_quotes'):
                    quotes_to_show = video['key_quotes'][:2]  # Only first 2 quotes
                    videos_text.append(f"    Quotes:")
                    for quote in quotes_to_show:
                        # Truncate very long quotes to 150 chars
                        truncated_quote = quote[:150] + "..." if len(quote) > 150 else quote
                        videos_text.append(f"      - \"{truncated_quote}\"")

                # Add logical flow if available (limit to first 4 concepts)
                if video.get('logical_flow'):
                    flow_items = video['logical_flow'][:4]  # Only first 4 concepts
                    flow_text = " → ".join(flow_items)
                    videos_text.append(f"    Logical flow: {flow_text}")
        videos_formatted = "\n".join(videos_text)

        # Format channel handles
        handles_text = "\n".join(
            f"{channel}: {handle}"
            for channel, handle in channel_handles.items()
        )

        return {
            "date": date,
            "title": title,
            "video_count": str(video_count),
            "big_picture_bullets": bullets_text,
            "videos_by_channel": videos_formatted,
            "contrarian_corner": contrarian_corner or "N/A",
            "channel_handles": handles_text or "None available"
        }
