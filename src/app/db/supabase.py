"""Supabase client singleton."""

from supabase import Client, create_client

from app.config.settings import settings

# Create singleton Supabase client instance
supabase: Client = create_client(
    settings.supabase_url,
    settings.supabase_key
)