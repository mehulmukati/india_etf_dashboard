"""
Supabase client initialization.
"""

import os
from supabase import create_client, Client


def get_supabase_client() -> Client:
    """
    Initialize and return a Supabase client using environment variables.
    
    Returns:
        Client: Configured Supabase client instance.
    
    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_ANON_KEY is not set.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError(
            "Missing Supabase credentials. Ensure SUPABASE_URL and SUPABASE_ANON_KEY are set in .env"
        )
    
    return create_client(supabase_url, supabase_key)
