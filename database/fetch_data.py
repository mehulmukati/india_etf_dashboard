"""
Data fetching functions with Streamlit caching.
Fetches Master, NAV, and OHLC data from Supabase.
"""

import streamlit as st
import pandas as pd
from datetime import timedelta, date

import sys
sys.path.append("/workspace")

from config import (
    NAV_CACHE_TTL,
    OHLC_CACHE_TTL,
    MASTER_CACHE_TTL,
    HISTORICAL_DATA_DAYS,
    TABLE_ETF_MASTER,
    TABLE_ETF_NAV,
    TABLE_ETF_OHLC,
    MASTER_COLUMNS,
    NAV_COLUMNS,
    OHLC_COLUMNS,
)
from database.client import get_supabase_client


@st.cache_data(ttl=MASTER_CACHE_TTL)
def fetch_etf_master() -> pd.DataFrame:
    """
    Fetch ETF master data from Supabase.
    Only fetches active ETFs.
    
    Returns:
        pd.DataFrame: ETF master data with columns: id, scheme_code, nse_code, 
                      is_active, index_tracked, category
    """
    client = get_supabase_client()
    
    response = (
        client.table(TABLE_ETF_MASTER)
        .select(",".join(MASTER_COLUMNS))
        .eq("is_active", True)
        .execute()
    )
    
    if not response.data:
        return pd.DataFrame(columns=MASTER_COLUMNS)
    
    df = pd.DataFrame(response.data)
    return df[MASTER_COLUMNS]


@st.cache_data(ttl=NAV_CACHE_TTL)
def fetch_etf_nav() -> pd.DataFrame:
    """
    Fetch rolling 1-year NAV data from Supabase.
    
    Returns:
        pd.DataFrame: NAV data with columns: id, scheme_code, trade_date, nav
    """
    client = get_supabase_client()
    
    # Calculate the date 1 year ago
    cutoff_date = date.today() - timedelta(days=HISTORICAL_DATA_DAYS)
    
    response = (
        client.table(TABLE_ETF_NAV)
        .select(",".join(NAV_COLUMNS))
        .gte("trade_date", cutoff_date.isoformat())
        .execute()
    )
    
    if not response.data:
        return pd.DataFrame(columns=NAV_COLUMNS)
    
    df = pd.DataFrame(response.data)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df[NAV_COLUMNS]


@st.cache_data(ttl=OHLC_CACHE_TTL)
def fetch_etf_ohlc() -> pd.DataFrame:
    """
    Fetch rolling 1-year OHLC data from Supabase.
    
    Returns:
        pd.DataFrame: OHLC data with columns: id, nse_code, trade_date, 
                      open, high, low, close, volume, turnover
    """
    client = get_supabase_client()
    
    # Calculate the date 1 year ago
    cutoff_date = date.today() - timedelta(days=HISTORICAL_DATA_DAYS)
    
    response = (
        client.table(TABLE_ETF_OHLC)
        .select(",".join(OHLC_COLUMNS))
        .gte("trade_date", cutoff_date.isoformat())
        .execute()
    )
    
    if not response.data:
        return pd.DataFrame(columns=OHLC_COLUMNS)
    
    df = pd.DataFrame(response.data)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    
    # Ensure numeric columns are properly typed
    numeric_cols = ["open", "high", "low", "close", "volume", "turnover"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    
    return df[OHLC_COLUMNS]
