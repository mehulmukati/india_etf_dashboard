"""
Filter module for ETF screening logic including user filters and Top Performer grouping.
"""
import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Tuple
from config import (
    DMA_PERIODS,
    RETURN_PERIODS_DAYS,
    AVERAGE_RETURN_PERIODS
)


def get_available_metric_options() -> List[Dict]:
    """
    Get all available metric options for the main dropdown.
    
    Returns:
        List of dictionaries with 'name' and 'key' for each metric option
    """
    options = []
    
    # Return metrics
    for period_name in RETURN_PERIODS_DAYS.keys():
        options.append({
            'name': f'{period_name}m Return',
            'key': f'{period_name}m_return',
            'group': 'Returns'
        })
    
    # Average return metrics
    for avg_config in AVERAGE_RETURN_PERIODS:
        key = f"avg_{'_'.join([str(p) for p in avg_config['periods']])}m_return"
        name = avg_config['name']
        options.append({
            'name': name,
            'key': key,
            'group': 'Returns'
        })
    
    # Sharpe metrics
    for period_name in RETURN_PERIODS_DAYS.keys():
        options.append({
            'name': f'{period_name}m Sharpe',
            'key': f'{period_name}m_sharpe',
            'group': 'Sharpe'
        })
    
    # Average Sharpe metrics
    for avg_config in AVERAGE_RETURN_PERIODS:
        key = f"avg_{'_'.join([str(p) for p in avg_config['periods']])}m_sharpe"
        name = avg_config['name'].replace('Avg ', 'Avg ') + ' Sharpe'
        options.append({
            'name': name,
            'key': key,
            'group': 'Sharpe'
        })
    
    return options


def calculate_average_metrics(df: pd.DataFrame, metric_type: str = 'return') -> pd.DataFrame:
    """
    Calculate average metrics across multiple periods.
    
    Args:
        df: DataFrame with individual period metrics
        metric_type: Either 'return' or 'sharpe'
        
    Returns:
        DataFrame with additional average metric columns
    """
    df = df.copy()
    
    for avg_config in AVERAGE_RETURN_PERIODS:
        periods = avg_config['periods']
        suffix = '_'.join([str(p) for p in periods])
        
        if metric_type == 'return':
            col_key = f'avg_{suffix}m_return'
            source_cols = [f'{p}m_return' for p in periods]
        else:  # sharpe
            col_key = f'avg_{suffix}m_sharpe'
            source_cols = [f'{p}m_sharpe' for p in periods]
        
        # Calculate mean of available values
        available_cols = [col for col in source_cols if col in df.columns]
        if available_cols:
            df[col_key] = df[available_cols].mean(axis=1, skipna=True)
    
    return df


def apply_top_performer_filter(
    df: pd.DataFrame,
    metric_column: str
) -> pd.DataFrame:
    """
    Apply "Top Performer" logic: keep only the best ETF per index_tracked.

    Args:
        df: DataFrame with ETF data including metrics
        metric_column: Column name to use for ranking

    Returns:
        Filtered DataFrame with only top performers per index
    """
    if df.empty:
        return df

    if metric_column not in df.columns:
        return df

    # Work on a copy to avoid modifying original
    result = df.copy()

    # Drop rows where index_tracked is missing (optional but recommended)
    result = result.dropna(subset=['index_tracked'])

    # Keep only rows where the metric is not NaN
    valid = result[result[metric_column].notna()]

    if valid.empty:
        # No valid data -> return empty DataFrame with same columns
        return pd.DataFrame(columns=result.columns)

    # For each index_tracked, find the row index with the maximum metric value
    idx = valid.groupby('index_tracked')[metric_column].idxmax()

    # Select those rows from the original DataFrame (preserves all columns)
    top_performers = result.loc[idx].reset_index(drop=True)

    return top_performers



def apply_dma_filter(
    df: pd.DataFrame,
    above_50_dma: bool = False,
    above_100_dma: bool = False,
    above_200_dma: bool = False
) -> pd.DataFrame:
    """
    Apply DMA filters based on user selections.
    
    Args:
        df: DataFrame with ETF data including DMA columns
        above_50_dma: Whether to filter for price > 50 DMA
        above_100_dma: Whether to filter for price > 100 DMA
        above_200_dma: Whether to filter for price > 200 DMA
        
    Returns:
        Filtered DataFrame
    """
    result = df.copy()
    
    if above_50_dma:
        result = result[result['last_close'] > result['dma_50']]
    
    if above_100_dma:
        result = result[result['last_close'] > result['dma_100']]
    
    if above_200_dma:
        result = result[result['last_close'] > result['dma_200']]
    
    return result


def apply_min_annual_return_filter(
    df: pd.DataFrame,
    min_annual_return: float
) -> pd.DataFrame:
    """
    Apply minimum annual return filter.
    
    Args:
        df: DataFrame with ETF data
        min_annual_return: Minimum 12-month annualized return (as decimal, e.g., 0.10 for 10%)
        
    Returns:
        Filtered DataFrame
    """
    if min_annual_return is None or min_annual_return == 0:
        return df
    
    result = df.copy()
    result = result[result['12m_return'] >= min_annual_return]
    
    return result


def apply_category_filter(
    df: pd.DataFrame,
    category: str
) -> pd.DataFrame:
    """
    Apply category filter.
    
    Args:
        df: DataFrame with ETF data including category column
        category: Category selection ('All', 'Broad Based', 'Thematic/Sectoral', 
                  'Foreign', 'All except Foreign')
                  
    Returns:
        Filtered DataFrame
    """
    if category == 'All':
        return df
    
    result = df.copy()
    
    if category == 'Broad Based':
        result = result[result['category'] == 'Broad Based']
    elif category == 'Thematic/Sectoral':
        result = result[result['category'] == 'Thematic/Sectoral']
    elif category == 'Foreign':
        result = result[result['category'] == 'Foreign']
    elif category == 'All except Foreign':
        result = result[result['category'] != 'Foreign']
    
    return result


def apply_min_traded_value_filter(
    df: pd.DataFrame,
    min_traded_value: float
) -> pd.DataFrame:
    """
    Apply minimum 5-day average traded value filter.
    
    Args:
        df: DataFrame with ETF data including avg_turnover_5d column
        min_traded_value: Minimum average turnover (in INR)
        
    Returns:
        Filtered DataFrame
    """
    if min_traded_value is None or min_traded_value == 0:
        return df
    
    result = df.copy()
    result = result[result['avg_turnover_5d'] >= min_traded_value]
    
    return result


def apply_all_filters(
    df: pd.DataFrame,
    selected_metric: str,
    above_50_dma: bool = False,
    above_100_dma: bool = False,
    above_200_dma: bool = False,
    min_annual_return: float = 0,
    category: str = 'All',
    min_traded_value: float = 0
) -> pd.DataFrame:
    """
    Apply all filters in sequence.
    
    Args:
        df: DataFrame with ETF data and calculated metrics
        selected_metric: Metric column for top performer selection
        above_50_dma: Filter for price > 50 DMA
        above_100_dma: Filter for price > 100 DMA
        above_200_dma: Filter for price > 200 DMA
        min_annual_return: Minimum 12-month annualized return
        category: Category filter selection
        min_traded_value: Minimum 5-day average turnover
        
    Returns:
        Fully filtered DataFrame
    """
    result = df.copy()
    
    # Apply DMA filters
    result = apply_dma_filter(result, above_50_dma, above_100_dma, above_200_dma)
    
    # Apply minimum annual return filter
    if min_annual_return > 0:
        result = apply_min_annual_return_filter(result, min_annual_return)
    
    # Apply category filter
    result = apply_category_filter(result, category)
    
    # Apply minimum traded value filter
    if min_traded_value > 0:
        result = apply_min_traded_value_filter(result, min_traded_value)
    
    # Apply top performer filter LAST (after other filters narrow down the pool)
    result = apply_top_performer_filter(result, selected_metric)
    
    return result


def sort_by_selected_metric(
    df: pd.DataFrame,
    metric_column: str,
    ascending: bool = False
) -> pd.DataFrame:
    """
    Sort DataFrame by the selected metric.
    
    Args:
        df: DataFrame to sort
        metric_column: Column to sort by
        ascending: Sort order
        
    Returns:
        Sorted DataFrame
    """
    if df.empty:
        return df
    
    result = df.copy()
    
    # Handle NaN values - put them at the end
    result = result.sort_values(
        by=metric_column,
        ascending=ascending,
        na_position='last'
    )
    
    return result.reset_index(drop=True)
