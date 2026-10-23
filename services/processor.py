"""
Service layer for orchestrating data processing pipeline.
Keeps app.py lean by encapsulating the main workflow logic.
"""
import pandas as pd
from typing import Dict, List
from database.fetch_data import (
    fetch_etf_master,
    fetch_etf_nav,
    fetch_etf_ohlc,
    get_last_trading_date,
    get_nse_holidays,
)
from calculations.metrics import calculate_all_metrics_for_etf
from calculations.filters import apply_all_filters, sort_by_selected_metric, calculate_average_metrics
from config import NSE_HOLIDAYS_SEGMENT


def load_all_data():
    """
    Load all required data from the database.
    
    Returns:
        Tuple of (master_df, nav_df, ohlc_df)
    """
    master_df = fetch_etf_master()
    nav_df = fetch_etf_nav()
    ohlc_df = fetch_etf_ohlc()
    return master_df, nav_df, ohlc_df


def calculate_all_etf_metrics(
    master_df: pd.DataFrame,
    nav_df: pd.DataFrame,
    ohlc_df: pd.DataFrame,
    risk_free_rate: float,
    calculation_method: str,
    volume_lookback_days: int
) -> pd.DataFrame:
    """
    Calculate metrics for all ETFs in the master list.

    All ETFs are aligned to a single shared anchor date (the last trading
    date derived from the calendar + NSE holiday list) before any metric is
    computed, so every momentum window across every ETF ends on the same day.
    An ETF whose feed is too stale to align within the backfill caps is
    excluded with a visible warning rather than being measured as-of a
    different date.

    Args:
        master_df: ETF master data
        nav_df: NAV data
        ohlc_df: OHLC data
        risk_free_rate: Risk-free rate for Sharpe calculation
        calculation_method: Period lookback methodology selected by the user
        
    Returns:
        DataFrame with all calculated metrics
    """
    # Anchor is derived from the data we actually have, not from the
    # calendar. The Supabase EOD job may not have landed today's close
    # yet, so using date.today() would put every window one day ahead of
    # the DB (and shift all lookback anchors by a day). Take the latest
    # trade_date present in the cached OHLC frame and step back from it
    # over weekends/holidays; this costs no extra Supabase call since the
    # OHLC frame is already cached.
    if ohlc_df.empty or "trade_date" not in ohlc_df.columns:
        data_max_date = None
    else:
        max_ts = pd.to_datetime(ohlc_df["trade_date"]).max()
        data_max_date = max_ts.date() if pd.notna(max_ts) else None

    anchor_date = pd.Timestamp(
        get_last_trading_date(NSE_HOLIDAYS_SEGMENT, start_date=data_max_date)
    )

    holidays = get_nse_holidays(NSE_HOLIDAYS_SEGMENT)

    metrics_list = []
    stale_etfs = []

    for _, row in master_df.iterrows():
        nse_code = row['nse_code']
        scheme_code = row['scheme_code']
        metrics = calculate_all_metrics_for_etf(
            nse_code=nse_code,
            scheme_code=scheme_code,
            ohlc_df=ohlc_df,
            nav_df=nav_df,
            risk_free_rate=risk_free_rate,
            calculation_method=calculation_method,
            volume_lookback_days=volume_lookback_days,
            anchor_date=anchor_date,
            holidays=holidays
        )

        if metrics:
            # ETF could not be aligned to the shared anchor (stale/delisted
            # price feed): keep it out of the rankings, but report it
            # instead of silently dropping it.
            if pd.isna(metrics.get('close_date', pd.NaT)):
                stale_etfs.append(nse_code)
                continue
            metrics['scheme_name'] = row.get('scheme_name', '')
            metrics['index_tracked'] = row.get('index_tracked', '')
            metrics['category'] = row.get('category', '')
            metrics_list.append(metrics)

    if stale_etfs:
        import streamlit as st
        st.warning(
            f"{len(stale_etfs)} ETF(s) had no price data near the anchor date "
            f"({anchor_date.date()}) and were excluded: {', '.join(sorted(stale_etfs))}"
        )


    if not metrics_list:
        return pd.DataFrame()
    
    results_df = pd.DataFrame(metrics_list)
    results_df = calculate_average_metrics(results_df, 'return')
    results_df = calculate_average_metrics(results_df, 'sharpe')
    
    return results_df


def process_screener(
    results_df: pd.DataFrame,
    filters: Dict
) -> pd.DataFrame:
    """
    Apply all filters and sorting to the results.
    
    Args:
        results_df: DataFrame with calculated metrics
        filters: Dictionary of filter values from sidebar
        
    Returns:
        Filtered and sorted DataFrame
    """
    filtered_df = apply_all_filters(
        df=results_df,
        selected_metric=filters['selected_metric'],
        above_50_dma=filters['above_50_dma'],
        above_100_dma=filters['above_100_dma'],
        above_200_dma=filters['above_200_dma'],
        min_annual_return=filters['min_annual_return'],
        category=filters['category'],
        min_traded_value=filters['min_traded_value']
    )
    
    sorted_df = sort_by_selected_metric(filtered_df, filters['selected_metric'])
    return sorted_df
