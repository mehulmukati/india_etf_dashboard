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
    NSE_HOLIDAYS_PATH,
    NSE_HOLIDAYS_SEGMENT,
)
from database.client import get_supabase_client


def get_nse_holidays(segment: str = "CM") -> set:
    """
    Load NSE holidays for a given segment from the JSON file.
    Dates are returned as a set of date objects for fast lookup.

    Args:
        segment: Market segment key in the JSON (default 'CM' for the cash
                 market segment, where equity/ETFs trade)

    Returns:
        Set of date objects representing market holidays
    """
    holidays_path = Path(NSE_HOLIDAYS_PATH)
    if not holidays_path.exists():
        return set()

    with open(holidays_path, "r") as f:
        data = json.load(f)

    holidays = set()
    # JSON layout: {segment: {year: [entries]}} — iterate all year buckets.
    segment_data = data.get(segment, {})
    if isinstance(segment_data, dict):
        year_groups = segment_data.values()
    else:  # fallback: legacy flat list layout
        year_groups = [segment_data]
    for entries in year_groups:
        for entry in entries:
            try:
                holidays.add(
                    pd.to_datetime(entry["tradingDate"], format="%d-%b-%Y").date()
                )
            except (KeyError, ValueError):
                continue

    return holidays


def get_last_trading_date(
      segment: str = "CM",
      start_date: date | None = None,
  ) -> date:
    """
    Determine the most recent trading date by stepping back from a start
    date (default: today), skipping weekends and NSE holidays.

    Args:
        segment: Market segment to use for holiday lookup
        start_date: Date to start stepping back from. Callers pass the
            latest trade_date present in the cached OHLC data so the
            anchor never points at a day whose EOD job hasn't landed yet.

    Returns:
        Most recent trading date as a date object
    """
    holidays = get_nse_holidays(segment)
    candidate = start_date if start_date is not None else date.today()

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
        pd.DataFrame with columns: scheme_code, nse_code, scheme_name,
                                   index_tracked, category
    """
    client = get_supabase_client()

    # Single page fetch (no pagination here), but add an explicit deterministic
    # ORDER BY id (the only PK in etf_master) so Postgres never returns rows
    # in a plan-dependent order across calls.
    response = (
        client.table(TABLE_ETF_MASTER)
        .select(",".join(MASTER_COLUMNS + ["id"]))
        .eq("is_active", True)
        .order("id")
        .execute()
    )

    if not response.data:
        return pd.DataFrame(columns=MASTER_COLUMNS)

    df = pd.DataFrame(response.data)

    # Warn loudly about any missing columns instead of silently dropping
    missing = [col for col in MASTER_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"fetch_etf_master: Supabase did not return expected columns: {missing}. "
            f"Check MASTER_COLUMNS in config.py matches the actual table schema."
        )

    # Drop the helper 'id' column before returning to callers
    return df[[col for col in MASTER_COLUMNS if col in df.columns]]



NAV_LOOKBACK_DAYS = 5  # safety window to find each ETF's latest available NAV

@st.cache_data(ttl=NAV_CACHE_TTL)
def fetch_etf_nav() -> pd.DataFrame:
    """
    Fetch each ETF's most recent available NAV record, used for display and
    premium/discount calculation. An ETF missing a record on the last trading
    date (e.g. due to a data feed delay) will still show its latest known NAV
    rather than being dropped.

    Looks back NAV_LOOKBACK_DAYS from the last trading date and keeps, per
    scheme_code, only the row with the most recent trade_date.

    Returns:
        pd.DataFrame with columns: scheme_code, trade_date, nav
    """
    client = get_supabase_client()

    last_trading_date = get_last_trading_date(NSE_HOLIDAYS_SEGMENT)
    cutoff_date = last_trading_date - timedelta(days=NAV_LOOKBACK_DAYS)

    all_data = []
    page = 0
    page_size = 1000  # Supabase max per request

    while True:
        response = (
            client.table(TABLE_ETF_NAV)
            .select(",".join(NAV_COLUMNS))
            .gte("trade_date", cutoff_date.isoformat())
            .lte("trade_date", last_trading_date.isoformat())
            .order("trade_date", desc=True)
            .order("scheme_code")
            .range(page * page_size, (page + 1) * page_size - 1)
            .execute()
        )

        if not response.data:
            break

        all_data.extend(response.data)
        page += 1

        if len(response.data) < page_size:
            break  # last page reached

    if not all_data:
        return pd.DataFrame(columns=NAV_COLUMNS)

    df = pd.DataFrame(all_data)
    df["trade_date"] = pd.to_datetime(df["trade_date"])

    # Keep only the most recent record per ETF (rows already sorted desc)
    df = df.sort_values("trade_date", ascending=False).drop_duplicates(
        subset="scheme_code", keep="first"
    )

    return df[[col for col in NAV_COLUMNS if col in df.columns]].reset_index(drop=True)



@st.cache_data(ttl=OHLC_CACHE_TTL)
def fetch_etf_ohlc() -> pd.DataFrame:
    """
    Fetch rolling OHLC data from Supabase up to the last trading date.
    Uses pagination to retrieve all records.

    Returns:
        pd.DataFrame with columns: nse_code, trade_date,
                                   high, close, volume, turnover
    """
    client = get_supabase_client()

    last_trading_date = get_last_trading_date(NSE_HOLIDAYS_SEGMENT)
    cutoff_date = last_trading_date - timedelta(days=HISTORICAL_DATA_DAYS)

    all_data = []
    page = 0
    page_size = 1000  # Supabase max per request

    while True:
        response = (
            client.table(TABLE_ETF_OHLC)
            .select(",".join(OHLC_COLUMNS))
            .gte("trade_date", cutoff_date.isoformat())
            .lte("trade_date", last_trading_date.isoformat())
            # Deterministic ORDER BY is required for stable pagination:
            # without it Postgres may return rows in a plan-dependent order,
            # so LIMIT/OFFSET pages can drop or duplicate rows. etf_ohlc has
            # no PK, so we sort by the full row identity (nse_code, trade_date)
            # plus close as a tiebreaker for any residual duplicates.
            .order("nse_code")
            .order("trade_date")
            .order("close")
            .range(page * page_size, (page + 1) * page_size - 1)
            .execute()
        )

        if not response.data:
            break

        all_data.extend(response.data)
        page += 1

        if len(response.data) < page_size:
            break  # last page reached

    if not all_data:
        return pd.DataFrame(columns=OHLC_COLUMNS)

    df = pd.DataFrame(all_data)
    df["trade_date"] = pd.to_datetime(df["trade_date"])

    numeric_cols = ["high", "close", "volume", "turnover"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df[[col for col in OHLC_COLUMNS if col in df.columns]]