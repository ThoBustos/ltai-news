"""Repository for channel database operations."""

from typing import List, Optional
from datetime import datetime

from app.core.logging import logger
from app.db.supabase import supabase
from app.models.channel import Channel


class ChannelRepository:
    """Repository for channel database operations."""

    def __init__(self):
        self.client = supabase
        self.table = "channels"

    def upsert_channel(self, channel: Channel) -> Channel:
        """
        Insert or update a channel.

        If channel exists, updates metadata and last_synced_at.
        If channel doesn't exist, creates new record.

        Args:
            channel: Channel model to upsert

        Returns:
            Upserted channel (same object)

        Raises:
            Exception: If database operation fails
        """
        try:
            # Convert channel to dict, excluding None values for cleaner updates
            channel_data = channel.model_dump(exclude_none=True, exclude={"raw_metadata"})

            # Handle raw_metadata separately (JSONB)
            if channel.raw_metadata:
                channel_data["raw_metadata"] = channel.raw_metadata

            # Convert datetime fields to ISO strings
            if channel.published_at:
                channel_data["published_at"] = channel.published_at.isoformat()
            if channel.last_synced_at:
                channel_data["last_synced_at"] = channel.last_synced_at.isoformat()

            # Upsert (insert or update on conflict)
            result = (
                self.client.table(self.table)
                .upsert(
                    channel_data,
                    on_conflict="id",  # Conflict on primary key
                )
                .execute()
            )

            if result.data:
                logger.debug(f"Upserted channel: {channel.id} - {channel.name}")
            else:
                logger.warning(f"No data returned from channel upsert: {channel.id}")

            return channel

        except Exception as e:
            logger.error(f"Failed to upsert channel {channel.id}: {e}")
            raise

    def get_channel_by_id(self, channel_id: str) -> Optional[Channel]:
        """
        Get channel by YouTube channel ID.

        Args:
            channel_id: YouTube channel ID

        Returns:
            Channel model or None if not found
        """
        try:
            result = (
                self.client.table(self.table)
                .select("*")
                .eq("id", channel_id)
                .single()
                .execute()
            )

            if result.data:
                return Channel(**result.data)
            return None

        except Exception as e:
            # Supabase returns error when not found, which is expected
            error_str = str(e)
            if "PGRST116" in error_str or "No rows" in error_str or "not found" in error_str.lower():
                return None
            logger.error(f"Failed to get channel {channel_id}: {e}")
            raise

    def get_any_match(self, identifier: str) -> Optional[Channel]:
        """
        Robustly find a channel by ID, handle, or name.
        
        Matches in order:
        1. Exact ID (UC...)
        2. Handle (with or without @)
        3. Exact Name (case-insensitive)
        """
        try:
            # 1. Try Exact ID
            if identifier.startswith("UC"):
                return self.get_channel_by_id(identifier)

            # 2. Try Handle
            clean_handle = identifier.lower()
            # Ensure it starts with @ for handle matching if it doesn't already
            if not clean_handle.startswith('@') and len(clean_handle) > 3:
                # We'll check both with and without @ in the DB
                search_handle = f"@{clean_handle}"
            else:
                search_handle = clean_handle
            
            result = (
                self.client.table(self.table)
                .select("*")
                .or_(f"handle.ilike.{search_handle},handle.ilike.{clean_handle},custom_url.ilike.{search_handle}")
                .limit(1)
                .execute()
            )
            if result.data:
                return Channel(**result.data[0])

            # 3. Try Case-Insensitive Name
            result = (
                self.client.table(self.table)
                .select("*")
                .ilike("name", identifier)
                .limit(1)
                .execute()
            )
            if result.data:
                return Channel(**result.data[0])
            
            return None
        except Exception as e:
            logger.error(f"Error in get_any_match for '{identifier}': {e}")
            return None

    def get_active_channels(self) -> List[Channel]:
        """
        Get all active channels.

        Returns:
            List of active Channel models

        Raises:
            Exception: If database operation fails
        """
        try:
            result = (
                self.client.table(self.table)
                .select("*")
                .eq("is_active", True)
                .order("name")
                .execute()
            )

            return [Channel(**row) for row in result.data]

        except Exception as e:
            logger.error(f"Failed to get active channels: {e}")
            raise

    def update_last_synced(self, channel_id: str) -> None:
        """
        Update last_synced_at timestamp for a channel.

        Args:
            channel_id: YouTube channel ID

        Raises:
            Exception: If database operation fails
        """
        try:
            self.client.table(self.table).update({
                "last_synced_at": datetime.utcnow().isoformat()
            }).eq("id", channel_id).execute()

            logger.debug(f"Updated last_synced_at for channel: {channel_id}")

        except Exception as e:
            logger.error(f"Failed to update last_synced_at for channel {channel_id}: {e}")
            raise




