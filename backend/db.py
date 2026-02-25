"""
Supabase client for database operations (feedback, analytics, subscriptions).
Uses service role key for server-side operations, anon key as fallback.
"""
from __future__ import annotations
from backend.config import SUPABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_ANON_KEY

_client = None


def get_supabase():
    """Get or create Supabase client (lazy singleton)."""
    global _client
    if _client is not None:
        return _client

    key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
    if not SUPABASE_URL or not key:
        return None  # Supabase not configured — features gracefully disabled

    try:
        from supabase import create_client
        _client = create_client(SUPABASE_URL, key)
        return _client
    except Exception as e:
        print(f"Warning: Could not create Supabase client: {e}")
        return None


def is_supabase_available() -> bool:
    """Check if Supabase is configured and available."""
    return get_supabase() is not None
