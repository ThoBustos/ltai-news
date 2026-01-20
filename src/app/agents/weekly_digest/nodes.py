"""Workflow nodes for weekly digest generation."""

import time
import json
from datetime import date

import opik
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.logging import logger
from app.config.settings import settings
from app.core.utils.time_window import parse_date
from app.core.utils.llm_client import calculate_cost, GEMINI_FLASH_PRICING
from app.models.weekly_digest import WeeklyContentResponse
from app.repositories.daily_digest_repository import DailyDigestRepository
from app.repositories.weekly_digest_repository import WeeklyDigestRepository
from app.agents.weekly_digest.state import WeeklyDigestState
from app.agents.weekly_digest.prompts import WeeklyDigestPrompts
from app.agents.weekly_digest.formatters import format_weekly_markdown, format_weekly_html


async def load_week_data_node(state: WeeklyDigestState) -> WeeklyDigestState:
    """Load daily digests and references for the target week.

    This node:
    1. Queries daily_digests for all days in the week range
    2. Gets trending references mentioned during the week
    3. Aggregates social links from speakers
    """
    week_start = parse_date(state["week_start_date"])
    week_end = parse_date(state["week_end_date"])
    logger.info(f"Loading data for weekly digest: {week_start} to {week_end}")

    try:
        digest_repo = DailyDigestRepository()

        # Get all daily digests in the week range
        daily_digests = await digest_repo.get_digests_in_range(week_start, week_end)
        logger.info(f"Found {len(daily_digests)} daily digests in week")

        if not daily_digests:
            logger.warning(f"No daily digests found for week {week_start} to {week_end}")
            state["errors"] = state.get("errors", [])
            state["errors"].append(f"No daily digests found for week")
            state["daily_digests"] = []
            state["is_empty"] = True
            return state

        # Convert to dicts for prompt formatting
        digest_dicts = []
        for d in daily_digests:
            digest_dicts.append({
                "id": str(d.id) if d.id else None,
                "publish_date": d.publish_date.isoformat() if d.publish_date else None,
                "title": d.title,
                "content_json": d.content_json,
                "video_count": d.video_count,
            })

        # Get trending references for the week
        trending_refs = await digest_repo.get_references_in_date_range(
            week_start, week_end, min_mentions=1
        )
        logger.info(f"Found {len(trending_refs)} references in week")

        trending_ref_dicts = [
            {
                "name": r.name,
                "reference_type": r.reference_type,
                "mention_count": r.mention_count,
                "author": r.author,
                "url": r.url,
                "description": r.description,
            }
            for r in trending_refs
        ]

        state["daily_digests"] = digest_dicts
        state["trending_references"] = trending_ref_dicts

        # Count days with actual content
        days_with_content = sum(
            1 for d in digest_dicts
            if d.get("content_json") and not d["content_json"].get("empty")
        )
        state["days_with_content"] = days_with_content

        if days_with_content == 0:
            state["is_empty"] = True

        logger.info(f"Loaded {len(digest_dicts)} digests, {days_with_content} with content")
        return state

    except Exception as e:
        logger.error("Failed to load week data: {}", e, exc_info=True)
        state.setdefault("errors", []).append(f"load_week_data: {e!s}")
        raise


async def generate_weekly_node(state: WeeklyDigestState) -> WeeklyDigestState:
    """Generate weekly digest content using LLM with native structured output.

    This node:
    1. Formats daily digest contexts into prompt
    2. Calls Gemini with native structured output (guaranteed valid JSON)
    3. Validates response as WeeklyContentResponse
    4. Generates markdown and HTML versions
    """
    week_start = parse_date(state["week_start_date"])
    week_end = parse_date(state["week_end_date"])
    logger.info(f"Generating weekly digest content for {week_start} to {week_end}")

    try:
        daily_digests = state.get("daily_digests", [])
        trending_refs = state.get("trending_references", [])

        if not daily_digests or state.get("is_empty"):
            logger.warning("No daily digests available for weekly generation")
            state.setdefault("errors", []).append("No daily digests available")
            return state

        # Format contexts
        (
            daily_context,
            days_with_content,
            total_videos,
            social_links
        ) = WeeklyDigestPrompts.format_all_daily_contexts(daily_digests)

        trending_context = WeeklyDigestPrompts.format_trending_references(trending_refs)
        social_links_context = WeeklyDigestPrompts.format_social_links(social_links)

        state["aggregated_social_links"] = social_links

        # Get prompt
        chat_prompt = WeeklyDigestPrompts.get_weekly_generation_prompt()

        # Format with variables
        formatted_messages = chat_prompt.format(
            variables={
                "week_start": state["week_start_date"],
                "week_end": state["week_end_date"],
                "days_with_content": str(days_with_content),
                "total_videos": str(total_videos),
                "daily_digests_context": daily_context,
                "trending_references": trending_context,
                "social_links_context": social_links_context,
            }
        )

        # Convert Opik messages to LangChain messages
        langchain_messages = []
        for msg in formatted_messages:
            content = str(msg.get("content", ""))
            if msg.get("role") == "system":
                langchain_messages.append(SystemMessage(content=content))
            else:
                langchain_messages.append(HumanMessage(content=content))

        # Initialize LangChain ChatGoogleGenerativeAI
        model_name = settings.analysis_model_name
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0.3,  # Low for structured output consistency
            api_key=settings.google_api_key,
        )

        # Create structured output version using native JSON schema method
        # This guarantees valid JSON matching the schema - no parsing needed!
        structured_llm = llm.with_structured_output(
            schema=WeeklyContentResponse.model_json_schema(),
            method="json_schema"
        )

        # Make LLM call - returns dict directly (validated against schema)
        start_time = time.time()
        structured_response_dict = await structured_llm.ainvoke(langchain_messages)
        processing_time = time.time() - start_time

        # Convert dict to Pydantic model
        if not isinstance(structured_response_dict, dict):
            structured_response_dict = dict(structured_response_dict) if hasattr(structured_response_dict, '__dict__') else {}

        weekly_content = WeeklyContentResponse(**structured_response_dict)

        # Estimate token usage (structured_llm doesn't expose usage_metadata)
        # Using ~4 chars per token approximation
        input_text = "\n".join([
            msg.content if hasattr(msg, 'content') and isinstance(msg.content, str)
            else str(msg.content) if hasattr(msg, 'content')
            else str(msg)
            for msg in langchain_messages
        ])
        output_text = json.dumps(structured_response_dict)
        input_tokens = max(1, len(input_text) // 4)
        output_tokens = max(1, len(output_text) // 4)
        cost = calculate_cost(input_tokens, output_tokens, GEMINI_FLASH_PRICING)

        # Ensure stats are populated
        if not weekly_content.stats.days_covered:
            weekly_content.stats.days_covered = days_with_content
        if not weekly_content.stats.total_videos:
            weekly_content.stats.total_videos = total_videos

        # Calculate read time if not set (V2 fields)
        if not weekly_content.stats.estimated_read_minutes:
            word_count = 0
            # the_one_thing
            word_count += len(weekly_content.the_one_thing.headline.split())
            word_count += len(weekly_content.the_one_thing.subtext.split())
            # quote
            word_count += len(weekly_content.quote_of_the_week.text.split())
            # watch_one
            word_count += len(weekly_content.watch_one.why.split())
            # contrarian_take
            word_count += len(weekly_content.contrarian_take.conventional.split())
            word_count += len(weekly_content.contrarian_take.actual.split())
            # concept_of_the_week
            word_count += len(weekly_content.concept_of_the_week.definition.split())
            # themes
            for theme in weekly_content.themes:
                word_count += len(theme.one_liner.split())
            # videos by category
            for videos in weekly_content.videos_by_category.values():
                for video in videos:
                    word_count += len(video.one_liner.split())
            # weekly_note
            word_count += len(weekly_content.weekly_note.split())
            weekly_content.stats.estimated_read_minutes = max(1, (word_count + 199) // 200)

        # Generate formatted versions
        formatted_markdown = format_weekly_markdown(weekly_content, week_start, week_end)
        formatted_html = format_weekly_html(weekly_content, week_start, week_end)

        # Create metrics dict
        metrics = {
            "workflow_version": "2.1",  # Updated for structured output
            "prompt_version": WeeklyDigestPrompts.CURRENT_VERSION,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_cost": cost,
            "processing_time_seconds": processing_time,
        }

        state["weekly_content"] = weekly_content
        state["formatted_markdown"] = formatted_markdown
        state["formatted_html"] = formatted_html
        state["metrics"] = metrics
        state["days_with_content"] = days_with_content

        # Add metadata to Opik span if available
        try:
            current_span = opik.get_current_span()  # type: ignore[attr-defined]
            if current_span:
                current_span.update(
                    metadata={
                        "prompt_name": "weekly-digest-generation",
                        "confidence_score": weekly_content.confidence_score,
                        "days_with_content": days_with_content,
                        "total_videos": total_videos,
                        "tokens_input": input_tokens,
                        "tokens_output": output_tokens,
                        "cost_usd": cost,
                        "structured_output": True,
                    }
                )
        except (AttributeError, TypeError):
            pass

        logger.info(
            f"Weekly digest generation completed: {input_tokens + output_tokens} tokens, "
            f"${cost:.6f}, {processing_time:.2f}s (structured output)"
        )

        return state

    except Exception as e:
        logger.error("Failed to generate weekly digest: {}", e, exc_info=True)
        state.setdefault("errors", []).append(f"generate_weekly: {e!s}")
        raise


async def save_results_node(state: WeeklyDigestState) -> WeeklyDigestState:
    """Save weekly digest to database.

    This node:
    1. Saves weekly digest content to weekly_digests table
    2. Updates metrics
    """
    week_start = parse_date(state["week_start_date"])
    week_end = parse_date(state["week_end_date"])
    logger.info(f"Saving weekly digest results for {week_start} to {week_end}")

    try:
        weekly_content = state.get("weekly_content")
        metrics = state.get("metrics", {})
        formatted_markdown = state.get("formatted_markdown", "")
        formatted_html = state.get("formatted_html", "")
        daily_digests = state.get("daily_digests", [])

        weekly_repo = WeeklyDigestRepository()

        if not weekly_content or state.get("is_empty"):
            # Save empty weekly digest
            digest_id = await weekly_repo.save_empty_weekly_digest(
                week_start,
                week_end,
                reason="No daily digests with content found for this week"
            )
            state["weekly_digest_id"] = digest_id
            state["is_empty"] = True
            logger.info(f"Saved empty weekly digest {digest_id}")
            return state

        # Extract daily digest IDs
        daily_digest_ids = [
            d["id"] for d in daily_digests
            if d.get("id") and d.get("content_json") and not d["content_json"].get("empty")
        ]

        # Save weekly digest
        digest_id = await weekly_repo.save_weekly_digest(
            week_start=week_start,
            week_end=week_end,
            content=weekly_content,
            formatted_markdown=formatted_markdown,
            formatted_html=formatted_html,
            daily_digest_ids=daily_digest_ids,
            metrics=metrics,
        )

        if not digest_id:
            state.setdefault("errors", []).append("Failed to save weekly digest to database")
            return state

        state["weekly_digest_id"] = digest_id

        logger.info(
            f"Saved weekly digest {digest_id}: "
            f"{state.get('days_with_content', 0)} days, "
            f"{weekly_content.stats.total_videos} videos"
        )

        return state

    except Exception as e:
        logger.error("Failed to save weekly digest results: {}", e, exc_info=True)
        state.setdefault("errors", []).append(f"save_results: {e!s}")
        raise
