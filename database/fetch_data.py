"""
Data fetching functions with Streamlit caching.
Fetches Master, NAV, and OHLC data from Supabase.
"""
import json
import streamlit as st
import pandas as pd
from datetime import timedelta, date
from pathlib import Path
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
    NSE_HOLIDAYS_PATH,       # ← add this to config.py (see note below)
    NSE_HOLIDAYS_SEGMENT,    # ← add this to config.py (see note below)
)
from database.client import get_supabase_client


def get_nse_holidays(segment: str = "CBM") -> set:
    """
    Load NSE holidays for a given segment from the JSON file.
    Dates are returned as a set of date objects for fast lookup.

    Args:
        segment: Market segment key in the JSON (default 'CBM' for equity/ETF)

    Returns:
        Set of date objects representing market holidays
    """
    holidays_path = Path(NSE_HOLIDAYS_PATH)
    if not holidays_path.exists():
        return set()

    with open(holidays_path, "r") as f:
        data = json.load(f)

    holidays = set()
    for entry in data.get(segment, []):
        try:
            holidays.add(
                pd.to_datetime(entry["tradingDate"], format="%d-%b-%Y").date()
            )
        except (KeyError, ValueError):
            continue

    return holidays


def get_last_trading_date(segment: str = "CBM") -> date:
    """
    Determine the most recent trading date by stepping back from today,
    skipping weekends and NSE holidays.

    Args:
        segment: Market segment to use for holiday lookup

    Returns:
        Most recent trading date as a date object
    """
    holidays = get_nse_holidays(segment)
    candidate = date.today()

    while True:
        # Skip weekends (Mon=0 ... Sun=6)
        if candidate.weekday() >= 5:
            candidate -= timedelta(days=1)
            continue
        # Skip NSE holidays
        if candidate in holidays:
            candidate -= timedelta(days=1)
            continue
        break

    return candidate


@st.cache_data(ttl=MASTER_CACHE_TTL)
def fetch_etf_master() -> pd.DataFrame:
    """
    Fetch ETF master data from Supabase.
    Only fetches active ETFs.

    Returns:
        pd.DataFrame with columns: id, scheme_code, nse_code, scheme_name,
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
    # return df[MASTER_COLUMNS]
    

    # Warn loudly about any missing columns instead of silently dropping
    missing = [col for col in MASTER_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"fetch_etf_master: Supabase did not return expected columns: {missing}. "
            f"Check MASTER_COLUMNS in config.py matches the actual table schema."
        )

    return df[[col for col in MASTER_COLUMNS if col in df.columns]]


@st.cache_data(ttl=NAV_CACHE_TTL)
def fetch_etf_nav() -> pd.DataFrame:
    """
    Fetch rolling NAV data from Supabase up to the last trading date.

    Returns:
        pd.DataFrame with columns: id, scheme_code, trade_date, nav
    """
    client = get_supabase_client()

    last_trading_date = get_last_trading_date(NSE_HOLIDAYS_SEGMENT)
    cutoff_date = last_trading_date - timedelta(days=HISTORICAL_DATA_DAYS)

    all_data = []
       page = 0
       page_size = 1000  # max per request

    while True:
    response = (
        client.table(TABLE_ETF_NAV)
        .select(",".join(NAV_COLUMNS))
        .gte("trade_date", cutoff_date.isoformat())
        .lte("trade_date", last_trading_date.isoformat())   # ← key fix
        .range(page * page_size, (page + 1) * page_size - 1)  # pagination
        .execute()
    )

    if not response.data:
        return pd.DataFrame(columns=NAV_COLUMNS)

    df = pd.DataFrame(response.data)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
#    return df[NAV_COLUMNS]
    return df[[col for col in NAV_COLUMNS if col in df.columns]]


@st.cache_data(ttl=OHLC_CACHE_TTL)
def fetch_etf_ohlc() -> pd.DataFrame:
    """
    Fetch rolling OHLC data from Supabase up to the last trading date.

    Returns:
        pd.DataFrame with columns: id, nse_code, trade_date,
                                   open, high, low, close, volume, turnover
    """
    client = get_supabase_client()

    last_trading_date = get_last_trading_date(NSE_HOLIDAYS_SEGMENT)
    cutoff_date = last_trading_date - timedelta(days=HISTORICAL_DATA_DAYS)

    all_data = []
       page = 0
       page_size = 1000  # max per request

    while True:
    response = (
        client.table(TABLE_ETF_OHLC)
        .select(",".join(OHLC_COLUMNS))
        .gte("trade_date", cutoff_date.isoformat())
        .lte("trade_date", last_trading_date.isoformat())   # ← key fix
        .range(page * page_size, (page + 1) * page_size - 1)  # pagination
        .execute()
    )

    if not response.data:
        return pd.DataFrame(columns=OHLC_COLUMNS)

    df = pd.DataFrame(response.data)
    df["trade_date"] = pd.to_datetime(df["trade_date"])

    numeric_cols = ["open", "high", "low", "close", "volume", "turnover"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

#    return df[OHLC_COLUMNS]
    return df[[col for col in OHLC_COLUMNS if col in df.columns]]