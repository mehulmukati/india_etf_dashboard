"""
Supabase client initialization with detailed error diagnostics.
"""

import os
import streamlit as st
from supabase import create_client, Client


def get_supabase_client() -> Client:
    """
    Initialize and return a Supabase client using environment variables.
    Provides detailed error messages to distinguish between URL and Key issues.
    
    Returns:
        Client: Configured Supabase client instance.
    
    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_ANON_KEY is not set or invalid.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    # 1. Check if environment variables are loaded at all
    if not supabase_url and not supabase_key:
        st.error("❌ **Critical Error**: `.env` file not found or not loaded.")
        raise ValueError("Missing .env file or environment variables not loaded.")
    
    # 2. Check specifically for URL
    if not supabase_url:
        st.error("❌ **Missing SUPABASE_URL**: The `SUPABASE_URL` variable is not set in your `.env` file.")
        st.info("Expected format: `https://<your-project-ref>.supabase.co`")
        raise ValueError("Missing SUPABASE_URL")
    
    if supabase_url == "your_supabase_url_here":
        st.error("❌ **Invalid SUPABASE_URL**: You are using the placeholder value. Please replace it with your actual Project URL from Supabase Dashboard > Settings > API.")
        raise ValueError("Placeholder SUPABASE_URL detected")

    # 3. Check specifically for Key
    if not supabase_key:
        st.error("❌ **Missing SUPABASE_ANON_KEY**: The `SUPABASE_ANON_KEY` variable is not set in your `.env` file.")
        st.info("Expected format: Starts with `eyJ...` or `sb_publishable_...`")
        raise ValueError("Missing SUPABASE_ANON_KEY")
    
    if supabase_key == "your_supabase_anon_key_here":
        st.error("❌ **Invalid SUPABASE_ANON_KEY**: You are using the placeholder value. Please replace it with your actual `anon` public key from Supabase Dashboard > Settings > API.")
        raise ValueError("Placeholder SUPABASE_ANON_KEY detected")
    
    # 4. Attempt to create client
    try:
        client = create_client(supabase_url, supabase_key)
        st.success("✅ Successfully connected to Supabase!")
        return client
    except Exception as e:
        error_msg = str(e)
        st.error(f"❌ **Connection Failed**: Unable to initialize Supabase client.")
        
        if "Invalid API key" in error_msg or "JWT" in error_msg or "apikey" in error_msg.lower():
            st.error("🔑 **Key Error**: The provided `SUPABASE_ANON_KEY` is invalid. Check for typos or ensure you copied the 'anon' public key (not service_role).")
        elif "connect" in error_msg.lower() or "network" in error_msg.lower() or "url" in error_msg.lower():
            st.error("🌐 **URL/Network Error**: Cannot reach the Supabase URL. Check your internet connection or verify the `SUPABASE_URL` for typos.")
        else:
            st.error(f"Details: {error_msg}")
            
        raise e
