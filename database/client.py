import os
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv

def get_supabase_client() -> Client:
    """
    Initialize and return a Supabase client instance.
    Dynamically locates .env in the project root.
    """
    # 1. Dynamically find the project root directory
    # __file__ is .../database/client.py
    # .parent is .../database
    # .parent.parent is .../ (project root where .env lives)
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent
    env_path = project_root / ".env"

    # 2. Load .env explicitly from the resolved path
    if not env_path.exists():
        raise FileNotFoundError(
            f".env file not found at {env_path}. "
            "Please ensure .env exists in the project root."
        )
    
    load_dotenv(dotenv_path=env_path)

    # 3. Retrieve credentials
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")
    
    # 4. Detailed Validation
    if not url:
        raise ValueError("SUPABASE_URL is missing in .env")
    if "your_supabase_url_here" in url:
        raise ValueError("SUPABASE_URL still contains placeholder text. Please update it.")
        
    if not key:
        raise ValueError("SUPABASE_ANON_KEY is missing in .env")
    if "your_supabase_anon_key_here" in key:
        raise ValueError("SUPABASE_ANON_KEY still contains placeholder text. Please update it.")

    # 5. Initialize Client
    try:
        return create_client(url, key)
    except Exception as e:
        # Catch specific Supabase/Postgrest errors if possible, otherwise generic
        error_msg = str(e)
        if "JWT" in error_msg or "apikey" in error_msg.lower():
            raise ValueError(f"Invalid Supabase Key provided. Error: {error_msg}")
        if "connect" in error_msg.lower() or "timeout" in error_msg.lower():
            raise ValueError(f"Cannot connect to Supabase URL '{url}'. Check your internet or URL. Error: {error_msg}")
        raise ValueError(f"Failed to initialize Supabase client: {error_msg}")
