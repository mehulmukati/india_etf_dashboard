"""
Service layer for orchestrating data processing pipeline.
Keeps app.py lean by encapsulating the main workflow logic.
"""
import pandas as pd
from typing import Dict, List
from database.fetch_data import fetch_etf_master, fetch_etf_nav, fetch_etf_ohlc
from calculations.metrics import calculate_all_metrics_for_etf
from calculations.filters import apply_all_filters, sort_by_selected_metric, calculate_average_metrics


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
    risk_free_rate: float
) -> pd.DataFrame:
    """
    Calculate metrics for all ETFs in the master list.
    
    Args:
        master_df: ETF master data
        nav_df: NAV data
        ohlc_df: OHLC data
        risk_free_rate: Risk-free rate for Sharpe calculation
        
    Returns:
        DataFrame with all calculated metrics
    """
    metrics_list = []
    
    for _, row in master_df.iterrows():
        nse_code = row['nse_code']
        metrics = calculate_all_metrics_for_etf(
            nse_code=nse_code,
            ohlc_df=ohlc_df,
            nav_df=nav_df,
            risk_free_rate=risk_free_rate
        )
        
        if metrics:
            metrics['scheme_name'] = row.get('scheme_name', '')
            metrics['index_tracked'] = row.get('index_tracked', '')
            metrics['category'] = row.get('category', '')
            metrics_list.append(metrics)
    
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
