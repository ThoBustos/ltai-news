"""Token management utilities for persistent OAuth token storage."""

import os
from pathlib import Path
from typing import Dict
import re

from app.core.logging import logger


class TokenManager:
    """Manages OAuth token persistence to .env file."""

    @staticmethod
    def update_env_tokens(access_token: str, refresh_token: str) -> bool:
        """Update Twitter OAuth2 tokens in .env file.

        Args:
            access_token: New access token
            refresh_token: New refresh token

        Returns:
            True if successful, False otherwise
        """
        try:
            # Find .env file in project root
            project_root = Path(__file__).parent.parent.parent.parent
            env_path = project_root / ".env"

            if not env_path.exists():
                logger.error(f".env file not found at {env_path}")
                return False

            # Read current .env content
            with open(env_path, 'r') as f:
                content = f.read()

            # Update tokens using regex replacement
            # Match lines starting with TWITTER_OAUTH2_ACCESS_TOKEN= or TWITTER_OAUTH2_REFRESH_TOKEN=
            content = re.sub(
                r'^TWITTER_OAUTH2_ACCESS_TOKEN=.*$',
                f'TWITTER_OAUTH2_ACCESS_TOKEN={access_token}',
                content,
                flags=re.MULTILINE
            )
            content = re.sub(
                r'^TWITTER_OAUTH2_REFRESH_TOKEN=.*$',
                f'TWITTER_OAUTH2_REFRESH_TOKEN={refresh_token}',
                content,
                flags=re.MULTILINE
            )

            # Write back to .env
            with open(env_path, 'w') as f:
                f.write(content)

            logger.info("✅ Successfully updated OAuth tokens in .env file")
            logger.warning("⚠️  Restart application for new tokens to take effect")
            return True

        except Exception as e:
            logger.error(f"Failed to update .env tokens: {e}")
            return False
