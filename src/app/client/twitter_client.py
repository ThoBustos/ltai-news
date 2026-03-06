"""Client for X/Twitter API v2 integration."""

from typing import List, Optional, Dict, Any
import tweepy

from app.core.logging import logger
from app.core.token_manager import TokenManager


class TwitterApiError(Exception):
    """Base exception for Twitter API errors."""
    pass


class TwitterAuthError(TwitterApiError):
    """Raised when authentication fails."""
    pass


class TwitterRateLimitError(TwitterApiError):
    """Raised when rate limit is exceeded."""
    pass


class TwitterClient:
    """Client for interacting with X/Twitter API v2 for posting threads."""

    def __init__(
        self,
        oauth2_client_id: str,
        oauth2_client_secret: str,
        oauth2_access_token: str,
        oauth2_refresh_token: str,
    ):
        """Initialize client with OAuth 2.0 PKCE.

        Uses OAuth 2.0 User Context with PKCE for secure authentication:
            - Modern security standard (no static secrets)
            - Supports read+write operations with granular scopes
            - Auto-refreshes expired access tokens
            - Required scopes: tweet.read, tweet.write, users.read, offline.access

        Args:
            oauth2_client_id: Twitter OAuth 2.0 Client ID
            oauth2_client_secret: Twitter OAuth 2.0 Client Secret
            oauth2_access_token: Twitter OAuth 2.0 Access Token (generated via PKCE)
            oauth2_refresh_token: Twitter OAuth 2.0 Refresh Token (for auto-refresh)

        Raises:
            TwitterAuthError: If authentication fails or credentials are invalid
        """
        try:
            # Create OAuth2UserHandler for token refresh support
            # Note: redirect_uri is only needed during authorization flow, not for API calls
            oauth2_user_handler = tweepy.OAuth2UserHandler(
                client_id=oauth2_client_id,
                redirect_uri="http://127.0.0.1:8080/callback",  # Used during token generation
                scope=["tweet.read", "tweet.write", "users.read", "offline.access"],
                client_secret=oauth2_client_secret,
            )

            # Set existing tokens
            oauth2_user_handler.token = {
                "access_token": oauth2_access_token,
                "refresh_token": oauth2_refresh_token,
            }

            # Initialize client with OAuth 2.0 User Context
            # Use bearer_token for User Context authentication
            self.client = tweepy.Client(bearer_token=oauth2_access_token)

            # Store handler for token refresh
            self.oauth2_handler = oauth2_user_handler

            logger.info("Twitter API client initialized with OAuth 2.0 PKCE")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter client: {e}")
            raise TwitterAuthError(f"Twitter authentication failed: {e}")

    def _refresh_access_token(self) -> str:
        """Refresh expired access token using refresh token.

        Returns:
            New access token

        Raises:
            TwitterAuthError: If token refresh fails
        """
        logger.info("Refreshing Twitter access token...")

        try:
            # Refresh the token using OAuth2UserHandler
            token_url = "https://api.twitter.com/2/oauth2/token"
            new_token = self.oauth2_handler.refresh_token(token_url)

            # Update handler with new tokens
            self.oauth2_handler.token = new_token

            # Recreate client with new access token
            self.client = tweepy.Client(bearer_token=new_token["access_token"])

            logger.info("Access token refreshed successfully")

            # Save new tokens to .env for persistence
            TokenManager.update_env_tokens(
                access_token=new_token["access_token"],
                refresh_token=new_token.get("refresh_token", self.oauth2_handler.token.get("refresh_token"))
            )

            return new_token["access_token"]

        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
            raise TwitterAuthError(f"Token refresh failed: {e}")

    def create_tweet(
        self,
        text: str,
        in_reply_to_tweet_id: Optional[str] = None,
        reply_settings: Optional[str] = "mentionedUsers"
    ) -> tweepy.Response:
        """Create a single tweet, optionally as thread reply.

        Args:
            text: Tweet content (max 280 chars)
            in_reply_to_tweet_id: Parent tweet ID for threading
            reply_settings: Who can reply to this tweet. Only valid for root tweets (not replies).
                          Options: "mentionedUsers", "following", None (everyone).
                          Automatically set to None for reply tweets.

        Returns:
            tweepy.Response with data.id and data.text

        Raises:
            TwitterApiError: If tweet creation fails
            ValueError: If text exceeds 280 characters
        """
        if len(text) > 280:
            raise ValueError(f"Tweet exceeds 280 chars: {len(text)} chars")

        # X API constraint: reply_settings is invalid on reply tweets
        if in_reply_to_tweet_id is not None:
            reply_settings = None

        try:
            # OAuth 2.0 User Context requires user_auth=False
            response = self.client.create_tweet(
                text=text,
                reply_settings=reply_settings,
                in_reply_to_tweet_id=in_reply_to_tweet_id,
                user_auth=False,
            )

            tweet_id = response.data['id']
            logger.info(f"Posted tweet: {tweet_id}")
            return response

        except tweepy.errors.TooManyRequests as e:
            error_msg = "Twitter rate limit exceeded"
            logger.error(f"{error_msg}: {e}")
            raise TwitterRateLimitError(error_msg)

        except tweepy.errors.Unauthorized as e:
            # Token likely expired, try refresh and retry once
            logger.warning("Twitter authentication failed (likely expired token), attempting refresh...")

            try:
                self._refresh_access_token()

                # Retry the request with refreshed token
                response = self.client.create_tweet(
                    text=text,
                    reply_settings=reply_settings,
                    in_reply_to_tweet_id=in_reply_to_tweet_id,
                    user_auth=False,
                )

                tweet_id = response.data['id']
                logger.info(f"Posted tweet after token refresh: {tweet_id}")
                return response

            except Exception as refresh_error:
                error_msg = f"Twitter authentication failed: {e}. Token refresh also failed: {refresh_error}"
                logger.error(error_msg)
                raise TwitterAuthError(error_msg)

        except Exception as e:
            error_msg = f"Failed to create tweet: {str(e)}"
            logger.error(error_msg)
            raise TwitterApiError(error_msg)

    def post_thread(
        self,
        tweets: List[str],
        reply_settings: str = "mentionedUsers"
    ) -> Dict[str, Any]:
        """Post a thread of tweets.

        Args:
            tweets: List of tweet texts (each max 280 chars)
            reply_settings: Who can reply - "everyone" | "mentionedUsers" | "following"

        Returns:
            Dict with tweet_ids (list) and thread_url (str)

        Raises:
            TwitterApiError: If thread posting fails
            ValueError: If any tweet exceeds 280 characters
        """
        if not tweets:
            raise ValueError("Cannot post empty thread")

        # Validate all tweets before posting
        for i, text in enumerate(tweets):
            if len(text) > 280:
                raise ValueError(f"Tweet {i+1} exceeds 280 chars: {len(text)} chars")

        tweet_ids = []
        reply_to = None

        try:
            for i, text in enumerate(tweets):
                logger.debug(f"Posting tweet {i+1}/{len(tweets)}")
                # Only set reply_settings on the first tweet (root of thread)
                settings = reply_settings if i == 0 else None
                response = self.create_tweet(
                    text=text,
                    in_reply_to_tweet_id=reply_to,
                    reply_settings=settings
                )
                tweet_id = response.data['id']
                tweet_ids.append(tweet_id)
                reply_to = tweet_id

            # Construct thread URL (points to first tweet)
            # Note: Twitter username will need to be passed or configured
            thread_url = f"https://x.com/i/status/{tweet_ids[0]}"

            logger.info(f"Thread posted successfully: {len(tweets)} tweets, URL: {thread_url}")

            return {
                "tweet_ids": tweet_ids,
                "thread_url": thread_url,
                "tweet_count": len(tweets)
            }

        except TwitterApiError:
            # If we posted some tweets before failing, log them
            if tweet_ids:
                logger.warning(f"Thread partially posted: {len(tweet_ids)}/{len(tweets)} tweets")
                logger.warning(f"Posted tweet IDs: {tweet_ids}")
            raise

    def get_client_info(self) -> Dict[str, Any]:
        """Get client configuration information."""
        return {
            "service": "X (Twitter) API v2",
            "authenticated": self.client is not None,
            "api_version": "v2"
        }
