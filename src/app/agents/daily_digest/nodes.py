"""Workflow nodes for daily digest generation."""

import time
from datetime import datetime, timezone, date

import opik

from app.core.logging import logger
from app.config.settings import settings
from app.core.utils.time_window import get_window, parse_date
from app.core.utils.llm_client import get_genai_client, extract_token_usage, generate_structured
from app.models.daily_digest import DigestContentResponse, DigestContentResponseV3, DigestMetrics, DigestSynthesisResponse, ReferencesV3
from app.repositories.video_repository import VideoRepository
from app.repositories.video_analysis_repository import VideoAnalysisRepository
from app.repositories.channel_repository import ChannelRepository
from app.repositories.daily_digest_repository import DailyDigestRepository
from app.agents.daily_digest.state import DailyDigestState
from app.agents.daily_digest.prompts import DailyDigestPrompts
from app.agents.daily_digest.formatters import format_digest_markdown, format_digest_html, format_digest_html_v3


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
        logger.error("Failed to load data for digest: {}", e, exc_info=True)
        state.setdefault("errors", []).append(f"load_data: {e!s}")
        raise


async def compress_videos_node(state: DailyDigestState) -> DailyDigestState:
    """Compress full video analyses into compact summaries (~400 tokens each).

    This node runs before write_digest_node and distills each video's full
    analysis (3,000-5,000 tokens) into an essential summary (~400 tokens).
    This reduces digest generation context by ~10x — no LLM call needed.

    With 9 videos: ~36,000 tokens → ~3,600 tokens into write_digest_node.
    """
    video_analyses = state.get("video_analyses", [])

    if not video_analyses:
        state["video_summaries"] = []
        return state

    summaries = [DailyDigestPrompts.format_compact_video(video) for video in video_analyses]
    state["video_summaries"] = summaries
    logger.info(f"Compressed {len(summaries)} video analyses ({len(video_analyses)} → compact)")
    return state


_CHUNK_SIZE = 10


async def _generate_chunk_digest(
    chunk_summaries: list,
    target_date: str,
    client,
    model_name: str,
    chunk_idx: int,
    total_chunks: int,
) -> tuple:
    """Generate a DigestContentResponseV3 for a single chunk of video summaries."""
    videos_context, channel_list = DailyDigestPrompts.format_compact_videos_context(chunk_summaries)
    chat_prompt = DailyDigestPrompts.get_digest_generation_prompt_v3()

    formatted_messages = chat_prompt.format(
        variables={
            "date": target_date,
            "video_count": str(len(chunk_summaries)),
            "channel_list": channel_list,
            "videos_context": videos_context,
        }
    )

    system_content = ""
    user_content = ""
    for msg in formatted_messages:
        if msg is None:
            continue
        content = str(msg.get("content", ""))
        if msg.get("role") == "system":
            system_content = content
        else:
            user_content = content

    user_content = f"[BATCH {chunk_idx + 1} of {total_chunks}]\n\n" + user_content

    digest_chunk, usage = await generate_structured(
        contents=user_content,
        response_model=DigestContentResponseV3,
        system_instruction=system_content,
        temperature=0.2,
        model_name=model_name,
        client=client,
        max_output_tokens=65536,
    )
    logger.info(f"Chunk {chunk_idx + 1}/{total_chunks}: {len(digest_chunk.video_sections)} sections generated")
    return digest_chunk, usage


async def _synthesize_digest_header(
    chunk_digests: list,
    target_date: str,
    client,
    model_name: str,
) -> tuple:
    """Synthesize title, intro, pull_quote from multiple chunk digests via a small LLM call."""
    batch_lines = []
    for i, chunk in enumerate(chunk_digests):
        batch_lines.append(
            f"[Batch {i + 1}]\n"
            f"Title: {chunk.title}\n"
            f"Intro: {chunk.intro}\n"
            f"Pull quote: {chunk.pull_quote or 'none'}"
        )
    batches_text = "\n\n".join(batch_lines)

    system_instruction = (
        "You are synthesizing multiple partial AI newsletter digest batches into unified header fields. "
        "Rules: No em dashes. No emojis. Staccato intro sentences, each on its own line."
    )
    user_content = (
        f"DATE: {target_date}\n"
        f"BATCH COUNT: {len(chunk_digests)}\n\n"
        f"{batches_text}\n\n"
        "Synthesize ONE title, ONE intro, and ONE pull_quote that best represents ALL videos combined today."
    )

    result, usage = await generate_structured(
        contents=user_content,
        response_model=DigestSynthesisResponse,
        system_instruction=system_instruction,
        temperature=0.2,
        model_name=model_name,
        client=client,
        max_output_tokens=2048,
    )
    return result.title, result.intro, result.pull_quote, usage


async def _merge_chunk_digests(
    chunk_digests: list,
    target_date: str,
    client,
    model_name: str,
) -> tuple:
    """Merge multiple chunk DigestContentResponseV3 objects into one unified digest."""
    all_video_sections = [section for chunk in chunk_digests for section in chunk.video_sections]

    all_people = list(dict.fromkeys(p for chunk in chunk_digests for p in chunk.references.people))
    all_tools = list(dict.fromkeys(t for chunk in chunk_digests for t in chunk.references.tools))
    all_papers = list(dict.fromkeys(p for chunk in chunk_digests for p in chunk.references.papers))
    all_keywords = list(dict.fromkeys(kw for chunk in chunk_digests for kw in chunk.keywords))[:10]

    avg_confidence = sum(c.confidence_score for c in chunk_digests) / len(chunk_digests)

    title, intro, pull_quote, synthesis_usage = await _synthesize_digest_header(
        chunk_digests, target_date, client, model_name
    )

    parsed = datetime.strptime(target_date, "%Y-%m-%d")
    meta = f"{parsed.strftime('%B')} {parsed.day} · {len(all_video_sections)} videos"

    merged = DigestContentResponseV3(
        title=title,
        meta=meta,
        intro=intro,
        pull_quote=pull_quote,
        video_sections=all_video_sections,
        references=ReferencesV3(people=all_people, tools=all_tools, papers=all_papers),
        keywords=all_keywords,
        confidence_score=avg_confidence,
    )
    return merged, synthesis_usage


async def write_digest_node(state: DailyDigestState) -> DailyDigestState:
    """Generate digest content using LLM from compressed video summaries.

    This node:
    1. Uses compact summaries from compress_videos_node (not raw analyses)
    2. Calls Gemini with structured output
    3. Parses JSON response into DigestContentResponse
    4. Generates markdown and HTML versions
    """
    logger.info(f"Generating digest content for {state['target_date']}")

    try:
        video_summaries = state.get("video_summaries", [])
        video_analyses = state.get("video_analyses", [])
        channel_stats = state.get("channel_stats", {})

        if not video_summaries:
            logger.warning("No video summaries available for digest generation")
            state.setdefault("errors", []).append("No video analyses available")
            return state

        # Format compact video contexts — replaces format_all_videos_context
        videos_context, channel_list = DailyDigestPrompts.format_compact_videos_context(video_summaries)

        # Choose schema version based on env var (default: v3)
        schema_version = settings.digest_schema_version
        if schema_version == "v3":
            chat_prompt = DailyDigestPrompts.get_digest_generation_prompt_v3()
            response_schema = DigestContentResponseV3
        else:
            chat_prompt = DailyDigestPrompts.get_digest_generation_prompt_v2()
            response_schema = DigestContentResponse

        # Format with variables
        formatted_messages = chat_prompt.format(
            variables={
                "date": state["target_date"],
                "video_count": str(len(video_summaries)),
                "channel_list": channel_list,
                "videos_context": videos_context,
            }
        )

        # Build prompt content for Google GenAI
        system_content = ""
        user_content = ""
        for msg in formatted_messages:
            if msg is None:
                continue
            content = str(msg.get("content", ""))
            if msg.get("role") == "system":
                system_content = content
            else:
                user_content = content

        # Get GenAI client and model name
        client = get_genai_client()
        model_name = settings.analysis_model_name

        start_time = time.time()

        chunked_threshold = settings.digest_chunked_threshold
        if schema_version == "v3" and len(video_summaries) > chunked_threshold:
            logger.info(
                f"{len(video_summaries)} videos exceeds threshold {chunked_threshold} — using chunked digest generation"
            )
            chunks = [
                video_summaries[i:i + _CHUNK_SIZE]
                for i in range(0, len(video_summaries), _CHUNK_SIZE)
            ]
            chunk_digests = []
            total_input_tokens = 0
            total_output_tokens = 0
            total_cost = 0.0
            for idx, chunk in enumerate(chunks):
                chunk_digest, chunk_usage = await _generate_chunk_digest(
                    chunk, state["target_date"], client, model_name, idx, len(chunks)
                )
                chunk_digests.append(chunk_digest)
                total_input_tokens += chunk_usage.input_tokens
                total_output_tokens += chunk_usage.output_tokens
                total_cost += chunk_usage.cost_usd

            digest_content, synthesis_usage = await _merge_chunk_digests(
                chunk_digests, state["target_date"], client, model_name
            )
            total_input_tokens += synthesis_usage.input_tokens
            total_output_tokens += synthesis_usage.output_tokens
            total_cost += synthesis_usage.cost_usd

            from app.core.utils.llm_client import TokenUsage
            usage = TokenUsage(
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                total_tokens=total_input_tokens + total_output_tokens,
                cost_usd=total_cost,
            )
            logger.info(
                f"Chunked digest complete: {len(chunks)} chunks + synthesis, "
                f"{total_input_tokens + total_output_tokens} tokens, ${total_cost:.6f}"
            )
        else:
            # Use hybrid approach - tries structured, falls back to parsing
            digest_content, usage = await generate_structured(
                contents=user_content,
                response_model=response_schema,
                system_instruction=system_content,
                temperature=0.2,
                model_name=model_name,
                client=client,
                max_output_tokens=65536,  # Model ceiling for gemini-3-flash-preview
            )

        processing_time = time.time() - start_time

        if isinstance(digest_content, DigestContentResponseV3):
            formatted_markdown = ""
            target_date = parse_date(state["target_date"])
            issue_url = f"{settings.site_url}/ainews/{target_date.isoformat()}"
            formatted_html = format_digest_html_v3(digest_content, target_date, issue_url=issue_url)
        else:
            # V2: Ensure stats are populated correctly
            if not digest_content.stats.channels and channel_stats:
                from app.models.daily_digest import ChannelStat
                digest_content.stats.channels = [
                    ChannelStat(
                        channel_id=cs["channel_id"],
                        channel_name=cs["channel_name"],
                        video_count=cs["video_count"],
                        thumbnail_url=cs.get("thumbnail_url"),
                        channel_url=f"https://youtube.com/channel/{cs['channel_id']}",
                    )
                    for cs in channel_stats.values()
                ]
                digest_content.stats.video_count = len(video_analyses)
                total_duration = sum(cs.get("total_duration_seconds", 0) for cs in channel_stats.values())
                digest_content.stats.total_duration_minutes = total_duration // 60

            # V2.2: Ensure channel_url is always populated (even if LLM generated stats)
            for channel in digest_content.stats.channels:
                if not channel.channel_url and channel.channel_id:
                    channel.channel_url = f"https://youtube.com/channel/{channel.channel_id}"

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
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_cost=usage.cost_usd,
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
                        "prompt_name": chat_prompt.name,
                        "schema_version": schema_version,
                        "confidence_score": digest_content.confidence_score,
                        "videos_count": len(video_analyses),
                        "tokens_input": usage.input_tokens,
                        "tokens_output": usage.output_tokens,
                        "cost_usd": usage.cost_usd,
                        "processing_time_seconds": processing_time,
                    }
                )
        except (AttributeError, TypeError):
            pass

        logger.info(
            f"Digest generation completed: {usage.total_tokens} tokens, ${usage.cost_usd:.6f}, {processing_time:.2f}s"
        )

        return state

    except Exception as e:
        logger.error("Failed to generate digest: {}", e, exc_info=True)
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

        target_date = parse_date(state["target_date"])
        digest_repo = DailyDigestRepository()

        if not digest_content or not metrics:
            # Save empty digest so frontend knows we processed this date
            digest_id = await digest_repo.save_empty_digest(
                target_date,
                reason="No video analyses available for this date"
            )
            state["digest_id"] = digest_id
            state["is_empty"] = True
            logger.info(f"Saved empty digest {digest_id} for {state['target_date']}")
            return state

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

        # Extract and upsert references (V2 only — V3 uses flat string lists)
        refs_count = 0
        if not isinstance(digest_content, DigestContentResponseV3):
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
        logger.error("Failed to save digest results: {}", e, exc_info=True)
        state.setdefault("errors", []).append(f"save_results: {e!s}")
        raise
