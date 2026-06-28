"""
Calculation module for ETF metrics including Returns, Sharpe Ratio, Volatility, DMAs, and Premium/Discount.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from config import (
    DEFAULT_RISK_FREE_RATE,
    DMA_PERIODS,
    RETURN_PERIODS_DAYS,
    VOLUME_MEDIAN_1M_WINDOW,
    VOLUME_MEDIAN_5D_WINDOW,
    VOLUME_AVG_5D_WINDOW
)


def calculate_returns(prices: pd.Series, days: int) -> float:
    """
    Calculate the return over a specified number of trading days.
    
    Args:
        prices: Series of closing prices indexed by date
        days: Number of trading days to look back
        
    Returns:
        Return as a decimal (e.g., 0.05 for 5%)
    """
    if len(prices) < days + 1:
        # Not enough data - calculate based on available data
        if len(prices) < 2:
            return np.nan
        days = len(prices) - 1
    
    start_price = prices.iloc[-(days + 1)]
    end_price = prices.iloc[-1]
    
    if pd.isna(start_price) or pd.isna(end_price) or start_price == 0:
        return np.nan
    
    return (end_price - start_price) / start_price


def calculate_annualized_return(prices: pd.Series, days: int) -> float:
    """
    Calculate annualized return over a specified period.
    
    Args:
        prices: Series of closing prices indexed by date
        days: Number of trading days in the period
        
    Returns:
        Annualized return as a decimal
    """
    raw_return = calculate_returns(prices, days)
    if np.isnan(raw_return):
        return np.nan
    
    # Annualize: (1 + r)^(252/days) - 1
    years = days / 252
    if years <= 0:
        return np.nan
    
    return ((1 + raw_return) ** (1 / years)) - 1


def calculate_volatility(prices: pd.Series, days: int, annualize: bool = True) -> float:
    """
    Calculate volatility (standard deviation of returns) over a specified period.
    
    Args:
        prices: Series of closing prices indexed by date
        days: Number of trading days to consider
        annualize: Whether to annualize the volatility
        
    Returns:
        Volatility as a decimal
    """
    if len(prices) < days + 1:
        days = max(len(prices) - 1, 1)
    
    if len(prices) < 2:
        return np.nan
    
    # Calculate daily returns
    returns = prices.pct_change().dropna()
    
    if len(returns) < days:
        vol = returns.std()
    else:
        vol = returns.iloc[-days:].std()
    
    if pd.isna(vol) or vol == 0:
        return np.nan
    
    if annualize:
        vol *= np.sqrt(252)
    
    return vol


def calculate_sharpe_ratio(prices: pd.Series, days: int, risk_free_rate: float = DEFAULT_RISK_FREE_RATE) -> float:
    """
    Calculate Sharpe ratio over a specified period.
    
    Args:
        prices: Series of closing prices indexed by date
        days: Number of trading days to consider
        risk_free_rate: Annual risk-free rate (as decimal)
        
    Returns:
        Sharpe ratio
    """
    if len(prices) < days + 1:
        days = max(len(prices) - 1, 1)
    
    if len(prices) < 2:
        return np.nan
    
    # Calculate daily returns
    returns = prices.pct_change().dropna()
    
    if len(returns) < days:
        period_returns = returns
    else:
        period_returns = returns.iloc[-days:]
    
    if len(period_returns) == 0 or period_returns.std() == 0:
        return np.nan
    
    # Annualized return
    mean_daily_return = period_returns.mean()
    annualized_return = mean_daily_return * 252
    
    # Annualized volatility
    annualized_vol = period_returns.std() * np.sqrt(252)
    
    if annualized_vol == 0 or pd.isna(annualized_vol):
        return np.nan
    
    sharpe = (annualized_return - risk_free_rate) / annualized_vol
    return sharpe


def calculate_dma(prices: pd.Series, period: int) -> float:
    """
    Calculate Dynamic Moving Average for a given period.
    
    Args:
        prices: Series of closing prices indexed by date
        period: Number of days for the moving average
        
    Returns:
        DMA value
    """
    if len(prices) < period:
        # Use available data if not enough history
        period = len(prices)
    
    if period == 0:
        return np.nan
    
    dma = prices.iloc[-period:].mean()
    return dma


def calculate_premium_discount(last_close: float, last_nav: float) -> float:
    """
    Calculate premium/discount percentage of close price relative to NAV.
    
    Args:
        last_close: Last closing price
        last_nav: Last NAV
        
    Returns:
        Premium/Discount as a percentage (positive = premium, negative = discount)
    """
    if pd.isna(last_nav) or last_nav == 0:
        return np.nan
    
    return ((last_close - last_nav) / last_nav) * 100


def calculate_median_volume(volumes: pd.Series, window: int) -> float:
    """
    Calculate median volume over a specified window.
    
    Args:
        volumes: Series of volumes indexed by date
        window: Number of days to consider
        
    Returns:
        Median volume
    """
    if len(volumes) < window:
        window = len(volumes)
    
    if window == 0:
        return np.nan
    
    return volumes.iloc[-window:].median()


def calculate_avg_turnover(turnovers: pd.Series, window: int) -> float:
    """
    Calculate average turnover over a specified window.
    
    Args:
        turnovers: Series of turnovers indexed by date
        window: Number of days to consider
        
    Returns:
        Average turnover
    """
    if len(turnovers) < window:
        window = len(turnovers)
    
    if window == 0:
        return np.nan
    
    return turnovers.iloc[-window:].mean()


def prepare_price_series(ohlc_df: pd.DataFrame, nse_code: str) -> pd.Series:
    """
    Prepare a forward-filled price series for an ETF.
    
    Args:
        ohlc_df: DataFrame with OHLC data
        nse_code: NSE code of the ETF
        
    Returns:
        Forward-filled Series of closing prices indexed by date
    """
    etf_data = ohlc_df[ohlc_df['nse_code'] == nse_code].copy()
    
    if etf_data.empty:
        return pd.Series(dtype=float)
    
    # Sort by date
    etf_data = etf_data.sort_values('trade_date')
    
    # Set date as index
    etf_data['trade_date'] = pd.to_datetime(etf_data['trade_date'])
    etf_data = etf_data.set_index('trade_date')
    
    # Forward-fill close prices (for missing trading days)
    etf_data['close'] = etf_data['close'].ffill()
    
    return etf_data['close']


def prepare_volume_series(ohlc_df: pd.DataFrame, nse_code: str) -> pd.Series:
    """
    Prepare a volume series for an ETF (no forward-fill).
    
    Args:
        ohlc_df: DataFrame with OHLC data
        nse_code: NSE code of the ETF
        
    Returns:
        Series of volumes indexed by date
    """
    etf_data = ohlc_df[ohlc_df['nse_code'] == nse_code].copy()
    
    if etf_data.empty:
        return pd.Series(dtype=float)
    
    # Sort by date
    etf_data = etf_data.sort_values('trade_date')
    
    # Set date as index
    etf_data['trade_date'] = pd.to_datetime(etf_data['trade_date'])
    etf_data = etf_data.set_index('trade_date')
    
    return etf_data['volume']


def prepare_turnover_series(ohlc_df: pd.DataFrame, nse_code: str) -> pd.Series:
    """
    Prepare a turnover series for an ETF (no forward-fill).
    
    Args:
        ohlc_df: DataFrame with OHLC data
        nse_code: NSE code of the ETF
        
    Returns:
        Series of turnovers indexed by date
    """
    etf_data = ohlc_df[ohlc_df['nse_code'] == nse_code].copy()
    
    if etf_data.empty:
        return pd.Series(dtype=float)
    
    # Sort by date
    etf_data = etf_data.sort_values('trade_date')
    
    # Set date as index
    etf_data['trade_date'] = pd.to_datetime(etf_data['trade_date'])
    etf_data = etf_data.set_index('trade_date')
    
    return etf_data['turnover']


def calculate_all_metrics_for_etf(
    nse_code: str,
    ohlc_df: pd.DataFrame,
    nav_df: pd.DataFrame,
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE
) -> Dict:
    """
    Calculate all metrics for a single ETF.
    
    Args:
        nse_code: NSE code of the ETF
        ohlc_df: DataFrame with OHLC data
        nav_df: DataFrame with NAV data
        risk_free_rate: Annual risk-free rate
        
    Returns:
        Dictionary containing all calculated metrics
    """
    # Prepare series
    prices = prepare_price_series(ohlc_df, nse_code)
    volumes = prepare_volume_series(ohlc_df, nse_code)
    turnovers = prepare_turnover_series(ohlc_df, nse_code)
    
    if prices.empty or len(prices) < 2:
        return {}
    
    # Get latest values
    last_close = prices.iloc[-1] if len(prices) > 0 else np.nan
    last_nav_row = nav_df[nav_df['scheme_code'].astype(str) == str(nse_code)]
    if not last_nav_row.empty:
        last_nav_row = last_nav_row.sort_values('trade_date', ascending=False).iloc[0]
        last_nav = last_nav_row['nav']
    else:
        last_nav = np.nan
    
    # Calculate returns for different periods
    returns = {}
    for period_name, days in RETURN_PERIODS_DAYS.items():
        returns[f'{period_name}m_return'] = calculate_returns(prices, days)
        returns[f'{period_name}m_annualized'] = calculate_annualized_return(prices, days)
    
    # Calculate Sharpe ratios
    sharpe = {}
    for period_name, days in RETURN_PERIODS_DAYS.items():
        sharpe[f'{period_name}m_sharpe'] = calculate_sharpe_ratio(prices, days, risk_free_rate)
    
    # Calculate volatility (1 year)
    volatility = calculate_volatility(prices, 252)
    
    # Calculate DMAs
    dmas = {}
    for period in DMA_PERIODS:
        dmas[f'dma_{period}'] = calculate_dma(prices, period)
    
    # Calculate premium/discount
    prem_dis = calculate_premium_discount(last_close, last_nav)
    
    # Calculate volume metrics
    median_volume_1m = calculate_median_volume(volumes, VOLUME_MEDIAN_1M_WINDOW)
    median_volume_5d = calculate_median_volume(volumes, VOLUME_MEDIAN_5D_WINDOW)
    avg_turnover_5d = calculate_avg_turnover(turnovers, VOLUME_AVG_5D_WINDOW)
    
    # Calculate 52-week high
    high_52w = prices.max() if len(prices) >= 252 else prices.max()
    
    return {
        'nse_code': nse_code,
        'last_close': last_close,
        'last_nav': last_nav,
        'premium_discount_pct': prem_dis,
        'volatility': volatility,
        'high_52w': high_52w,
        'median_volume_1m': median_volume_1m,
        'median_volume_5d': median_volume_5d,
        'avg_turnover_5d': avg_turnover_5d,
        **returns,
        **sharpe,
        **dmas
    }
