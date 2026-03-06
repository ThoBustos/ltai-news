"""Workflow nodes for X thread generation and posting."""

import time
from datetime import datetime, timezone
from typing import Dict, List, Any

import opik
from google.genai.types import GenerateContentConfig

from app.core.logging import logger
from app.core.utils.llm_client import get_genai_client, extract_token_usage
from app.config.settings import settings
from app.repositories.daily_digest_repository import DailyDigestRepository
from app.repositories.channel_repository import ChannelRepository
from app.client.twitter_client import TwitterClient, TwitterApiError
from app.agents.x_thread.state import XThreadState, XThreadMetrics
from app.agents.x_thread.prompts import XThreadPrompts
from app.models.daily_digest import DigestContentResponse
from app.models.x_thread import XThreadResponse


async def load_digest_node(state: XThreadState) -> XThreadState:
    """Load digest data and channel metadata.

    This node:
    1. Loads the digest content from database
    2. Loads channel data with X handles
    3. Prepares context for thread generation
    """
    logger.info(f"Loading digest for X thread: {state['target_date']}")

    try:
        digest_repo = DailyDigestRepository()
        channel_repo = ChannelRepository()

        # Load digest by date
        digest = await digest_repo.get_digest_by_date(state['target_date'])

        if not digest:
            state["errors"] = state.get("errors", [])
            state["errors"].append(f"No digest found for {state['target_date']}")
            return state

        # Load digest content from content_json
        if not digest.content_json:
            state["errors"] = state.get("errors", [])
            state["errors"].append(f"Digest content is empty for {state['target_date']}")
            return state

        # Deserialize to DigestContentResponse for type safety
        digest_content = DigestContentResponse(**digest.content_json)

        # Store digest content
        state["digest_content"] = digest_content
        state["digest_id"] = str(digest.id)

        # Load channels with X handles
        all_channels = channel_repo.get_active_channels()
        channels_data = []
        for channel in all_channels:
            channels_data.append({
                "id": channel.id,
                "name": channel.name,
                "x_handle": channel.x_handle if hasattr(channel, 'x_handle') else None
            })

        state["channels"] = channels_data

        logger.info(f"Loaded digest with {digest_content.stats.video_count} videos")
        return state

    except Exception as e:
        logger.error(f"Error loading digest: {e}")
        state["errors"] = state.get("errors", [])
        state["errors"].append(f"Failed to load digest: {str(e)}")
        return state


@opik.track(name="x_thread.generate_thread")
async def generate_thread_node(state: XThreadState) -> XThreadState:
    """Generate X thread using LLM.

    This node:
    1. Formats digest data for prompt
    2. Calls LLM to generate thread
    3. Validates tweet lengths
    4. Stores thread tweets in state
    """
    logger.info(f"Generating X thread for {state['target_date']}")

    start_time = time.time()

    try:
        digest_content = state.get("digest_content")
        channels = state.get("channels", [])

        if not digest_content:
            raise ValueError("No digest content available")

        # Build channel handle mapping for X/Twitter
        channel_handles = {}
        for channel_data in channels:
            # Use x_handle (X/Twitter) not handle (YouTube)
            if channel_data.get("x_handle"):
                channel_handles[channel_data["name"]] = channel_data["x_handle"]

        # Group videos by channel
        videos_by_channel: Dict[str, List[Dict[str, str]]] = {}
        for video_section in digest_content.video_sections:
            channel_name = video_section.channel_name
            if channel_name not in videos_by_channel:
                videos_by_channel[channel_name] = []

            videos_by_channel[channel_name].append({
                "title": video_section.title,
                "url": video_section.video_url,
                "duration_minutes": str(video_section.duration_minutes),
                "key_quotes": video_section.key_quotes,
                "logical_flow": video_section.logical_flow
            })

        # Format prompt context
        prompt_context = XThreadPrompts.format_video_context(
            date=state['target_date'],
            title=digest_content.title,
            video_count=digest_content.stats.video_count,
            big_picture_bullets=digest_content.big_picture_bullets,
            videos_by_channel=videos_by_channel,
            contrarian_corner=digest_content.contrarian_corner.insight
                if digest_content.contrarian_corner else "",
            channel_handles=channel_handles
        )

        # Get prompt
        prompt = XThreadPrompts.get_thread_prompt()

        # Create LLM request
        client = get_genai_client()

        # Format messages using ChatPrompt.format() - handles substitution automatically
        formatted_messages = prompt.format(variables=prompt_context)

        # Build prompt content for Google GenAI (same pattern as other agents)
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

        # Log input sizes for debugging
        logger.info(f"System instruction length: {len(system_content)} chars")
        logger.info(f"User content length: {len(user_content)} chars")
        logger.info(f"Total input length: {len(system_content) + len(user_content)} chars")

        # Make LLM call with TRUE structured output (pass class, not schema dict)
        response = client.models.generate_content(
            model=settings.analysis_model_name,
            contents=user_content,
            config=GenerateContentConfig(
                system_instruction=system_content,
                response_mime_type="application/json",
                response_schema=XThreadResponse,  # Pass Pydantic class directly
                temperature=0.2,
                max_output_tokens=8192,  # Increased from 4096 to handle longer context
            )
        )

        # Extract token usage (real counts from Gemini)
        token_usage = extract_token_usage(response)

        # Log raw response for debugging truncation issues
        raw_text = response.text or ""
        logger.info(f"Raw LLM response length: {len(raw_text)} chars")
        logger.info(f"Output tokens used: {token_usage.output_tokens}")
        logger.debug(f"Raw LLM response: {raw_text[:1000]}...")  # First 1000 chars

        # Check if response looks truncated
        if raw_text and not raw_text.rstrip().endswith('}'):
            logger.warning(f"Response may be truncated - doesn't end with '}}': ...{raw_text[-100:]}")
            logger.warning(f"Consider increasing max_output_tokens further or reducing input context")

        # Check if we hit the token limit
        if token_usage.output_tokens >= 8000:  # Close to our 8192 limit
            logger.warning(f"Output tokens ({token_usage.output_tokens}) near limit (8192) - response likely truncated")

        # Direct validation - Gemini guarantees valid JSON matching schema
        result = XThreadResponse.model_validate_json(raw_text)

        # Type-safe access (Pydantic validated)
        thread_tweets = result.thread_tweets

        # Validate tweet lengths
        for i, tweet in enumerate(thread_tweets):
            if len(tweet) > 280:
                logger.warning(f"Tweet {i+1} exceeds 280 chars: {len(tweet)} chars")
                # Truncate with ellipsis
                thread_tweets[i] = tweet[:277] + "..."

        state["thread_tweets"] = thread_tweets

        # Create typed metrics object (matches Video Analyzer pattern)
        metrics = XThreadMetrics(
            workflow_version="1.0",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            input_tokens=token_usage.input_tokens,  # Direct attribute access (not .get())
            output_tokens=token_usage.output_tokens,
            total_tokens=token_usage.total_tokens,
            total_cost=token_usage.cost_usd,  # Add cost tracking
            processing_time_seconds=time.time() - start_time,
            tweet_count=len(thread_tweets)
        )
        state["metrics"] = metrics

        logger.info(f"Generated thread with {len(thread_tweets)} tweets")
        return state

    except Exception as e:
        logger.error(f"Error generating thread: {e}")
        state["errors"] = state.get("errors", [])
        state["errors"].append(f"Failed to generate thread: {str(e)}")

        # Use typed metrics even in error case
        state["metrics"] = XThreadMetrics(
            workflow_version="1.0",
            processing_time_seconds=time.time() - start_time,
        )
        return state


async def post_to_x_node(state: XThreadState) -> XThreadState:
    """Post thread to X via API.

    This node:
    1. Initializes TwitterClient
    2. Posts thread sequentially
    3. Stores tweet IDs and thread URL
    4. Updates digest record with tweet IDs
    """
    logger.info(f"Posting thread to X for {state['target_date']}")

    try:
        thread_tweets = state.get("thread_tweets", [])

        if not thread_tweets:
            state["errors"] = state.get("errors", [])
            state["errors"].append("No thread tweets to post")
            return state

        # Initialize Twitter client with OAuth 2.0 PKCE
        twitter_client = TwitterClient(
            oauth2_client_id=settings.twitter_oauth2_client_id,
            oauth2_client_secret=settings.twitter_oauth2_client_secret,
            oauth2_access_token=settings.twitter_oauth2_access_token,
            oauth2_refresh_token=settings.twitter_oauth2_refresh_token,
        )

        # Post thread
        result = twitter_client.post_thread(
            tweets=thread_tweets,
            reply_settings="mentionedUsers"
        )

        state["tweet_ids"] = result["tweet_ids"]
        state["thread_url"] = result["thread_url"]

        # Update digest record with tweet IDs
        digest_repo = DailyDigestRepository()
        await digest_repo.update_tweet_ids(
            digest_id=state["digest_id"],
            tweet_ids=result["tweet_ids"]
        )

        logger.info(f"Thread posted successfully: {result['thread_url']}")
        return state

    except TwitterApiError as e:
        logger.error(f"Twitter API error: {e}")
        state["errors"] = state.get("errors", [])
        state["errors"].append(f"Twitter API error: {str(e)}")
        return state

    except Exception as e:
        logger.error(f"Error posting thread: {e}")
        state["errors"] = state.get("errors", [])
        state["errors"].append(f"Failed to post thread: {str(e)}")
        return state
