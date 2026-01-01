"""Workflow nodes for daily digest generation."""

import time
import json
from datetime import datetime, timezone, date

import opik
from google import genai
from google.genai.types import GenerateContentConfig

from app.core.logging import logger
from app.config.settings import settings
from app.core.utils.time_window import get_window, parse_date
from app.models.daily_digest import DigestContentResponse, DigestMetrics
from app.repositories.video_repository import VideoRepository
from app.repositories.video_analysis_repository import VideoAnalysisRepository
from app.repositories.channel_repository import ChannelRepository
from app.repositories.daily_digest_repository import DailyDigestRepository
from app.agents.daily_digest.state import DailyDigestState
from app.agents.daily_digest.prompts import DailyDigestPrompts
from app.agents.daily_digest.formatters import format_digest_markdown, format_digest_html

# Gemini Flash pricing (same as video_analyzer)
GEMINI_FLASH_INPUT_PRICE_PER_1M = 0.075   # $0.075 per 1M input tokens
GEMINI_FLASH_OUTPUT_PRICE_PER_1M = 0.30    # $0.30 per 1M output tokens


def _get_genai_client():
    """Get Google GenAI client for LLM calls."""
    return genai.Client(api_key=settings.google_api_key)


def _calculate_cost(input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD from token counts using Gemini Flash pricing."""
    input_cost = (input_tokens / 1_000_000) * GEMINI_FLASH_INPUT_PRICE_PER_1M
    output_cost = (output_tokens / 1_000_000) * GEMINI_FLASH_OUTPUT_PRICE_PER_1M
    return input_cost + output_cost


def _calculate_read_time(content: DigestContentResponse) -> int:
    """Calculate estimated read time at 200 WPM.

    Args:
        content: The digest content response

    Returns:
        Estimated read time in minutes (minimum 1)
    """
    word_count = 0

    # Count words in main sections
    word_count += len(content.daily_tldr.split())
    word_count += len(content.conclusion.split())

    # Count words in video sections
    for video in content.video_sections:
        word_count += len(video.condensed_summary.split())
        word_count += len(video.deep_analysis.split())
        word_count += len(video.structure_overview.split())
        for quote in video.key_quotes:
            word_count += len(quote.split())

    # Count words in action items
    for action in content.action_items:
        word_count += len(action.action.split())
        word_count += len(action.context.split())

    # 200 words per minute, round up, minimum 1
    return max(1, (word_count + 199) // 200)


async def load_data_node(state: DailyDigestState) -> DailyDigestState:
    """Load video analyses and metadata for the target date.

    This node:
    1. Queries video_processed_data for all analyses on target_date
    2. Joins with videos table for metadata (title, thumbnail, etc.)
    3. Joins with channels table for channel info
    4. Builds rich context for each video
    """
    logger.info(f"Loading data for digest: {state['target_date']}")

    try:
        target_date = parse_date(state["target_date"])
        window = get_window(target_date)

        video_repo = VideoRepository()
        channel_repo = ChannelRepository()
        analysis_repo = VideoAnalysisRepository()

        # Get all videos in the target date window
        videos = video_repo.get_videos_in_window(window)
        logger.info(f"Found {len(videos)} videos in window for {state['target_date']}")

        if not videos:
            state["errors"] = state.get("errors", [])
            state["errors"].append(f"No videos found for {state['target_date']}")
            state["video_analyses"] = []
            state["video_metadata"] = []
            return state

        # Load analyses and build rich context for each video
        video_analyses = []
        video_metadata = []
        channel_stats = {}

        for video in videos:
            # Get analysis for this video
            analysis = await analysis_repo.get_analysis(video.id)
            if not analysis:
                logger.debug(f"No analysis found for video {video.id}, skipping")
                continue

            # Get channel info
            channel = channel_repo.get_channel_by_id(video.channel_id) if video.channel_id else None
            channel_name = channel.name if channel else "Unknown Channel"
            channel_thumbnail = channel.thumbnail_url if channel else None

            # Track channel stats
            if video.channel_id not in channel_stats:
                channel_stats[video.channel_id] = {
                    "channel_id": video.channel_id,
                    "channel_name": channel_name,
                    "video_count": 0,
                    "thumbnail_url": channel_thumbnail,
                    "total_duration_seconds": 0,
                }
            channel_stats[video.channel_id]["video_count"] += 1
            channel_stats[video.channel_id]["total_duration_seconds"] += video.duration_seconds or 0

            # Build combined data structure
            video_data = {
                # Video metadata
                "video_id": video.id,
                "title": video.title,
                "description": video.description or "",
                "channel_id": video.channel_id,
                "channel_name": channel_name,
                "thumbnail_url": video.thumbnail_url or "",
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
                # V2 extraction fields (graceful degradation if not present)
                "teaser_hooks": getattr(analysis, 'teaser_hooks', []) or [],
                "keywords": getattr(analysis, 'keywords', []) or [],
                "direct_quotes": getattr(analysis, 'direct_quotes', []) or [],
                "analogies_metaphors": getattr(analysis, 'analogies_metaphors', []) or [],
                "frameworks_shared": getattr(analysis, 'frameworks_shared', []) or [],
                "statistics_data": getattr(analysis, 'statistics_data', []) or [],
                "section_analysis": getattr(analysis, 'section_analysis', []) or [],
            }

            video_analyses.append(video_data)
            video_metadata.append({
                "video_id": video.id,
                "title": video.title,
                "channel_name": channel_name,
                "thumbnail_url": video.thumbnail_url,
                "duration_seconds": video.duration_seconds,
            })

        state["video_analyses"] = video_analyses
        state["video_metadata"] = video_metadata
        state["channel_stats"] = channel_stats

        logger.info(f"Loaded {len(video_analyses)} video analyses for digest")
        return state

    except Exception as e:
        logger.error(f"Failed to load data for digest: {e}", exc_info=True)
        state.setdefault("errors", []).append(f"load_data: {e}")
        raise


async def generate_digest_node(state: DailyDigestState) -> DailyDigestState:
    """Generate digest content using LLM.

    This node:
    1. Formats all video contexts into prompt
    2. Calls Gemini Flash with structured output
    3. Parses JSON response into DigestContentResponse
    4. Generates markdown and HTML versions
    """
    logger.info(f"Generating digest content for {state['target_date']}")

    try:
        video_analyses = state.get("video_analyses", [])
        channel_stats = state.get("channel_stats", {})

        if not video_analyses:
            logger.warning("No video analyses available for digest generation")
            state.setdefault("errors", []).append("No video analyses available")
            return state

        # Format video contexts - V2 returns tuple (context, channel_list)
        videos_context, channel_list = DailyDigestPrompts.format_all_videos_context(video_analyses)

        # Get prompt
        chat_prompt = DailyDigestPrompts.get_digest_generation_prompt()

        # Format with variables
        formatted_messages = chat_prompt.format(
            variables={
                "date": state["target_date"],
                "video_count": str(len(video_analyses)),
                "channel_list": channel_list,
                "videos_context": videos_context,
            }
        )

        # Build prompt content for Google GenAI
        system_content = ""
        user_content = ""
        for msg in formatted_messages:
            content = str(msg.get("content", ""))
            if msg.get("role") == "system":
                system_content = content
            else:
                user_content = content

        # Add JSON schema instruction
        # NOTE: Using compact JSON (no indent) to avoid brace patterns like "{\n  " that
        # can be misinterpreted as format placeholders by Opik's tracing
        schema_instruction = f"""

Respond with valid JSON matching this exact schema:
{json.dumps(DigestContentResponse.model_json_schema())}

IMPORTANT: Populate the stats.channels array with actual channel data from the videos.
Your response must be valid JSON only, no additional text."""

        user_content += schema_instruction

        # Get GenAI client
        client = _get_genai_client()
        model_name = settings.analysis_model_name

        # Make LLM call
        start_time = time.time()
        response = client.models.generate_content(
            model=model_name,
            contents=user_content,
            config=GenerateContentConfig(
                systemInstruction=system_content,
                temperature=1.0,
            )
        )
        processing_time = time.time() - start_time

        # Extract token counts
        usage = response.usage_metadata
        input_tokens = (usage.prompt_token_count or 0) if usage else 0
        output_tokens = (usage.candidates_token_count or 0) if usage else 0
        total_tokens = (usage.total_token_count or 0) if usage else (input_tokens + output_tokens)

        # Calculate cost
        cost = _calculate_cost(input_tokens, output_tokens)

        # Parse JSON response
        response_text = (response.text or "").strip()
        if response_text.startswith('```json'):
            response_text = response_text.replace('```json', '').replace('```', '').strip()
        elif response_text.startswith('```'):
            response_text = response_text.replace('```', '').strip()

        if '{' in response_text:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            response_text = response_text[start_idx:end_idx]

        digest_content = DigestContentResponse.model_validate_json(response_text)

        # Ensure stats are populated correctly
        if not digest_content.stats.channels and channel_stats:
            from app.models.daily_digest import ChannelStat
            digest_content.stats.channels = [
                ChannelStat(
                    channel_id=cs["channel_id"],
                    channel_name=cs["channel_name"],
                    video_count=cs["video_count"],
                    thumbnail_url=cs.get("thumbnail_url"),
                )
                for cs in channel_stats.values()
            ]
            digest_content.stats.video_count = len(video_analyses)
            total_duration = sum(cs.get("total_duration_seconds", 0) for cs in channel_stats.values())
            digest_content.stats.total_duration_minutes = total_duration // 60

        # V2: Calculate read time if not set
        if not digest_content.stats.estimated_read_minutes:
            digest_content.stats.estimated_read_minutes = _calculate_read_time(digest_content)

        # Generate formatted versions
        target_date = parse_date(state["target_date"])
        formatted_markdown = format_digest_markdown(digest_content, target_date)
        formatted_html = format_digest_html(digest_content, target_date)

        # Create metrics
        metrics = DigestMetrics(
            workflow_version="2.0",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_cost=cost,
            processing_time_seconds=processing_time,
            videos_analyzed=len(video_analyses),
            references_extracted=0,  # Will be set in save_results
        )

        state["digest_content"] = digest_content
        state["formatted_markdown"] = formatted_markdown
        state["formatted_html"] = formatted_html
        state["metrics"] = metrics

        # Add metadata to Opik span if available
        try:
            current_span = opik.get_current_span()  # type: ignore[attr-defined]
            if current_span:
                current_span.update(
                    metadata={
                        "prompt_name": "daily-digest-generation",
                        "confidence_score": digest_content.confidence_score,
                        "videos_count": len(video_analyses),
                        "tokens_input": input_tokens,
                        "tokens_output": output_tokens,
                        "cost_usd": cost,
                        "processing_time_seconds": processing_time,
                    }
                )
        except (AttributeError, TypeError):
            pass

        logger.info(
            f"Digest generation completed: {total_tokens} tokens, ${cost:.6f}, {processing_time:.2f}s"
        )

        return state

    except Exception as e:
        logger.error(f"Failed to generate digest: {e}", exc_info=True)
        state.setdefault("errors", []).append(f"generate_digest: {e}")
        raise


async def save_results_node(state: DailyDigestState) -> DailyDigestState:
    """Save digest to database and extract references.

    This node:
    1. Saves digest content to daily_digests table
    2. Extracts and upserts references to digest_references table
    3. Updates metrics with reference count
    """
    logger.info(f"Saving digest results for {state['target_date']}")

    try:
        digest_content = state.get("digest_content")
        metrics = state.get("metrics")
        formatted_markdown = state.get("formatted_markdown", "")
        formatted_html = state.get("formatted_html", "")
        video_analyses = state.get("video_analyses", [])

        if not digest_content or not metrics:
            logger.warning("No digest content to save")
            state.setdefault("errors", []).append("No digest content to save")
            return state

        target_date = parse_date(state["target_date"])
        digest_repo = DailyDigestRepository()

        # Extract source video IDs and channel IDs
        source_video_ids = [v["video_id"] for v in video_analyses]
        channels_included = list(set(v.get("channel_id", "") for v in video_analyses if v.get("channel_id")))

        # Save digest to database
        digest_id = await digest_repo.save_digest(
            publish_date=target_date,
            content=digest_content,
            metrics=metrics,
            formatted_markdown=formatted_markdown,
            formatted_html=formatted_html,
            source_video_ids=source_video_ids,
            channels_included=channels_included,
        )

        if not digest_id:
            state.setdefault("errors", []).append("Failed to save digest to database")
            return state

        state["digest_id"] = digest_id

        # Extract and upsert references
        references = []

        # Books
        for ref in digest_content.references_index.books:
            references.append({
                "reference_type": "book",
                "name": ref.name,
                "author": ref.author,
                "url": ref.url,
                "description": ref.description,
            })

        # Papers
        for ref in digest_content.references_index.papers:
            references.append({
                "reference_type": "paper",
                "name": ref.name,
                "author": ref.author,
                "url": ref.url,
                "description": ref.description,
            })

        # Frameworks
        for ref in digest_content.references_index.frameworks:
            references.append({
                "reference_type": "framework",
                "name": ref.name,
                "url": ref.url,
                "description": ref.description,
            })

        # Concepts
        for ref in digest_content.references_index.concepts:
            references.append({
                "reference_type": "concept",
                "name": ref.name,
                "description": ref.description,
            })

        # People
        for ref in digest_content.references_index.people:
            references.append({
                "reference_type": "person",
                "name": ref.name,
                "description": ref.description,
            })

        # Communities
        for ref in digest_content.references_index.communities:
            references.append({
                "reference_type": "community",
                "name": ref.name,
                "url": ref.url,
                "description": ref.description,
            })

        # Upsert references
        refs_count = await digest_repo.upsert_references(
            references=references,
            digest_id=digest_id,
            video_ids=source_video_ids,
            target_date=target_date,
        )

        state["references_extracted"] = refs_count

        # Update metrics
        if metrics:
            metrics.references_extracted = refs_count

        logger.info(f"Saved digest {digest_id} with {refs_count} references")
        return state

    except Exception as e:
        logger.error(f"Failed to save digest results: {e}", exc_info=True)
        state.setdefault("errors", []).append(f"save_results: {e}")
        raise
