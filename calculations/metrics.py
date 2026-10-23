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
    VOLUME_LOOKBACK_DEFAULT_DAYS
)


CALCULATION_METHOD_252_DAYS = "252 Trading Days"
CALCULATION_METHOD_EXACT_MONTHS = "Exact 3/6/9/12 Months"
EXACT_MONTH_LOOKBACK_DAYS = 5

# Anchor backfill limits (see align_prices_to_anchor).
ANCHOR_BACKFILL_CALENDAR_DAYS = 7    # calendar days to search back for the
                                     # ETF's nearest actual trade on/before
                                     # the anchor date
ANCHOR_FFILL_TRADING_DAYS = 400      # max trading days a single stale close
                                     # may be forward-filled for (safety cap)


def resolve_month_anchor(
    end_date: pd.Timestamp,
    months: int,
    holidays: Optional[set] = None
) -> pd.Timestamp:
    """
    Resolve the shared calendar-month anchor date for a window ending at
    `end_date`.

    The raw anchor is `end_date - months` calendar months. If that day is a
    weekend or NSE holiday, step BACK one calendar day at a time until a
    trading day is found (industry best practice: always go back, never
    forward, so windows are never shorter than requested and never overshoot
    into extra price moves beyond the bridge gap).

    Args:
        end_date: Anchor end date (the shared last-trading date)
        months: Number of calendar months in the lookback window
        holidays: Set of date objects (NSE holidays); weekends are always skipped

    Returns:
        Timestamp (normalized) of the resolved anchor trading date
    """
    if holidays is None:
        holidays = set()

    target = pd.Timestamp(end_date).normalize() - pd.DateOffset(months=months)
    while target.weekday() >= 5 or target.date() in holidays:
        target -= pd.Timedelta(days=1)
    return target


def align_prices_to_anchor(
    prices: pd.Series,
    anchor_date: pd.Timestamp,
    holidays: Optional[set] = None
) -> pd.Series:
    """
    Align a single ETF's price series to a shared anchor date.

    Rules:
      1. All trades strictly AFTER `anchor_date` are dropped, so every ETF's
         window ends on the same date regardless of its own last row.
      2. If the ETF has no trade exactly ON the anchor date (e.g. it did not
         trade that day), walk back up to ANCHOR_BACKFILL_CALENDAR_DAYS
         calendar days to find its nearest actual trade on/before the anchor.
      3. From that backfilled point, forward-fill through any gap between the
         backfilled trade and the anchor date, but only across trading days
         (weekends/holidays excluded) and capped at
         ANCHOR_FFILL_TRADING_DAYS trading days. Beyond the cap the ETF is
         treated as having insufficient history (empty series returned).

    Args:
        prices: Forward-filled-close series indexed by trade date (ascending)
        anchor_date: Shared anchor trading date to align to
        holidays: Set of date objects (NSE holidays) used to identify
                  non-trading days inside gaps

    Returns:
        Series truncated at the anchor date with the anchor-day price present
        (either actual or carried forward), or an empty float Series if the
        ETF cannot be aligned within the caps.
    """
    if prices.empty:
        return pd.Series(dtype=float)

    anchor = pd.Timestamp(anchor_date).normalize()
    if holidays is None:
        holidays = set()

    # Rule 1: drop everything after the anchor date.
    aligned = prices.loc[:anchor]
    if aligned.empty:
        return pd.Series(dtype=float)

    last_date = pd.Timestamp(aligned.index[-1]).normalize()
    if last_date == anchor:
        return aligned  # ETF actually traded on the anchor date

    # Rule 2: backfill cap - how far back we accept the ETF's last real trade.
    earliest_acceptable = anchor - pd.Timedelta(days=ANCHOR_BACKFILL_CALENDAR_DAYS)
    if last_date < earliest_acceptable:
        return pd.Series(dtype=float)  # too stale to carry to the anchor

    # Rule 3: count trading days strictly between last actual trade and the
    # anchor (i.e. the number of forward-filled values this alignment needs).
    fill_days = 0
    cursor = last_date + pd.Timedelta(days=1)
    while cursor <= anchor:
        if cursor.weekday() < 5 and cursor.date() not in holidays:
            fill_days += 1
            if fill_days > ANCHOR_FFILL_TRADING_DAYS:
                return pd.Series(dtype=float)  # exceeds ffill safety cap
        cursor += pd.Timedelta(days=1)

    # Carry the last actual close forward onto the anchor date.
    filled = aligned.reindex(aligned.index.union([anchor])).sort_index().ffill()
    return filled.loc[filled.index <= anchor]


def has_sufficient_history(prices: pd.Series, days: int) -> bool:
    """
    Strict check for whether a price series has enough history to compute
    a metric over the requested number of trading days.

    Args:
        prices: Series of closing prices indexed by date
        days: Number of trading days required

    Returns:
        True if len(prices) >= days + 1, else False
    """
    return len(prices) >= days + 1


def calculate_returns(prices: pd.Series, days: int) -> float:
    """
    Calculate the return over a specified number of trading days.

    Returns NaN if the series does not have at least `days + 1` data points
    (i.e. no partial-period fallback - the requested period must be fully
    covered by available history).

    Args:
        prices: Series of closing prices indexed by date
        days: Number of trading days to look back

    Returns:
        Return as a decimal (e.g., 0.05 for 5%), or NaN if insufficient data
    """
    if not has_sufficient_history(prices, days):
        return np.nan

    start_price = prices.iloc[-(days + 1)]
    end_price = prices.iloc[-1]

    if pd.isna(start_price) or pd.isna(end_price) or start_price == 0:
        return np.nan

    return (end_price - start_price) / start_price


def calculate_annualized_return(prices: pd.Series, days: int) -> float:
    """
    Calculate annualized return over a specified period.

    Returns NaN if the underlying period return cannot be computed due to
    insufficient history.

    Args:
        prices: Series of closing prices indexed by date
        days: Number of trading days in the period

    Returns:
        Annualized return as a decimal, or NaN if insufficient data
    """
    raw_return = calculate_returns(prices, days)
    if np.isnan(raw_return):
        return np.nan

    # Annualize: (1 + r)^(252/days) - 1
    years = days / 252
    if years <= 0:
        return np.nan

    return ((1 + raw_return) ** (1 / years)) - 1


def calculate_annualized_return_from_months(prices: pd.Series, months: int) -> float:
    """Calculate an annualized return using an exact calendar-month window."""
    raw_return = calculate_returns_from_exact_months(prices, months)
    if np.isnan(raw_return) or months <= 0:
        return np.nan

    return (1 + raw_return) ** (12 / months) - 1


def calculate_volatility(prices: pd.Series, days: int, annualize: bool = True) -> float:
    """
    Calculate volatility (standard deviation of returns) over a specified period.

    Returns NaN if the series does not have at least `days + 1` data points
    (no shrinking the window to whatever is available).

    Args:
        prices: Series of closing prices indexed by date
        days: Number of trading days to consider
        annualize: Whether to annualize the volatility

    Returns:
        Volatility as a decimal, or NaN if insufficient data
    """
    if not has_sufficient_history(prices, days):
        return np.nan

    # Calculate daily returns
    returns = prices.pct_change().dropna()

    if len(returns) < days:
        return np.nan

    vol = returns.iloc[-days:].std()

    if pd.isna(vol) or vol == 0:
        return np.nan

    if annualize:
        vol *= np.sqrt(252)

    return vol


def calculate_sharpe_ratio(prices: pd.Series, days: int, risk_free_rate: float = DEFAULT_RISK_FREE_RATE) -> float:
    """
    Calculate Sharpe ratio over a specified period.

    Returns NaN if the series does not have at least `days + 1` data points
    (no shrinking the window to whatever is available).

    Args:
        prices: Series of closing prices indexed by date
        days: Number of trading days to consider
        risk_free_rate: Annual risk-free rate (as decimal)

    Returns:
        Sharpe ratio, or NaN if insufficient data
    """
    if not has_sufficient_history(prices, days):
        return np.nan

    # Calculate daily returns
    returns = prices.pct_change().dropna()

    if len(returns) < days:
        return np.nan

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


def find_exact_month_start(
    prices: pd.Series,
    months: int,
    holidays: Optional[set] = None
) -> Optional[pd.Timestamp]:
    """
    Find the exact calendar-month window start for a series already aligned
    to the shared anchor (its last row is the anchor trading date).

    The anchor is resolved purely from the calendar (end date minus N months,
    stepping back over weekends/holidays - see resolve_month_anchor), then we
    locate that date in the ETF's own trade history. If the ETF did not trade
    exactly on the anchor date, walk back day by day (never forward) until one
    of its actual trades is found; that price is used as the window start.
    """
    if prices.empty or months <= 0:
        return None

    end_date = pd.Timestamp(prices.index[-1]).normalize()
    anchor = resolve_month_anchor(end_date, months, holidays)

    available_dates = {pd.Timestamp(value).normalize(): value for value in prices.index}

    candidate = anchor
    while candidate >= pd.Timestamp(prices.index[0]).normalize():
        if candidate in available_dates:
            return available_dates[candidate]
        candidate -= pd.Timedelta(days=1)

    return None


def get_exact_month_prices(
    prices: pd.Series,
    months: int,
    holidays: Optional[set] = None
) -> pd.Series:
    """Return prices from the resolved exact-month boundary through the end."""
    start_date = find_exact_month_start(prices, months, holidays)
    if start_date is None:
        return pd.Series(dtype=float)

    return prices.loc[start_date:]


def calculate_returns_from_exact_months(
    prices: pd.Series,
    months: int,
    holidays: Optional[set] = None
) -> float:
    """Calculate return between the resolved exact-month boundary and the end."""
    period_prices = get_exact_month_prices(prices, months, holidays)
    if len(period_prices) < 2:
        return np.nan

    start_price = period_prices.iloc[0]
    end_price = period_prices.iloc[-1]
    if pd.isna(start_price) or pd.isna(end_price) or start_price == 0:
        return np.nan

    return (end_price - start_price) / start_price


def calculate_volatility_from_exact_months(
    prices: pd.Series,
    months: int,
    annualize: bool = True,
    holidays: Optional[set] = None
) -> float:
    """Calculate volatility over the resolved exact-month window."""
    period_prices = get_exact_month_prices(prices, months, holidays)
    if len(period_prices) < 2:
        return np.nan

    returns = period_prices.pct_change().dropna()
    if returns.empty:
        return np.nan

    volatility = returns.std()
    if pd.isna(volatility) or volatility == 0:
        return np.nan

    return volatility * np.sqrt(252) if annualize else volatility


def calculate_sharpe_ratio_from_exact_months(
    prices: pd.Series,
    months: int,
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
    holidays: Optional[set] = None
) -> float:
    """Calculate annualized Sharpe ratio over the exact-month window."""
    period_prices = get_exact_month_prices(prices, months, holidays)
    if len(period_prices) < 2:
        return np.nan

    returns = period_prices.pct_change().dropna()
    if returns.empty or returns.std() == 0:
        return np.nan

    annualized_return = returns.mean() * 252
    annualized_volatility = returns.std() * np.sqrt(252)
    if pd.isna(annualized_volatility) or annualized_volatility == 0:
        return np.nan

    return (annualized_return - risk_free_rate) / annualized_volatility


def calculate_dma(prices: pd.Series, period: int) -> float:
    """
    Calculate Dynamic Moving Average for a given period.

    Returns NaN if the series has fewer than `period` data points (no
    shrinking the window to whatever is available).

    Args:
        prices: Series of closing prices indexed by date
        period: Number of days for the moving average

    Returns:
        DMA value, or NaN if insufficient data
    """
    if len(prices) < period:
        return np.nan

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
    scheme_code: str,
    ohlc_df: pd.DataFrame,
    nav_df: pd.DataFrame,
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
    calculation_method: str = CALCULATION_METHOD_252_DAYS,
    volume_lookback_days: int = VOLUME_LOOKBACK_DEFAULT_DAYS,
    anchor_date: Optional[pd.Timestamp] = None,
    holidays: Optional[set] = None
) -> Dict:
    """
    Calculate all metrics for a single ETF.

    Metrics for any period (return, annualized return, volatility, Sharpe,
    DMA) whose required lookback window exceeds the available price history
    are returned as NaN rather than computed over a shrunken window.

    Args:
        nse_code: NSE code of the ETF
        scheme_code: Scheme code of the ETF (for NAV lookup)
        ohlc_df: DataFrame with OHLC data
        nav_df: DataFrame with NAV data
        risk_free_rate: Annual risk-free rate
        calculation_method: Either the existing 252-trading-day method or
            exact calendar-month periods
        volume_lookback_days: Window (in rows) for volume/turnover stats
        anchor_date: Shared last-trading date every ETF's price series is
            aligned to before any metric is computed (see
            align_prices_to_anchor). When None, each ETF is measured from
            its own last row (legacy behaviour).
        holidays: Set of date objects (NSE holidays) used for trading-day
            gap checks during anchor alignment and month-anchor resolution

    Returns:
        Dictionary containing all calculated metrics
    """
    # Prepare series
    prices = prepare_price_series(ohlc_df, nse_code)
    volumes = prepare_volume_series(ohlc_df, nse_code)
    turnovers = prepare_turnover_series(ohlc_df, nse_code)

    if prices.empty or len(prices) < 2:
        return {}

    # Align this ETF's price series to the shared anchor date so that all
    # ETFs' windows end on the same day. If the ETF cannot be aligned
    # within the backfill caps (stale/delisted feed), report it via
    # close_date = NaT with no metrics rather than silently using a
    # different as-of date.
    if anchor_date is not None:
        prices = align_prices_to_anchor(prices, anchor_date, holidays)
        if prices.empty or len(prices) < 2:
            return {
                'nse_code': nse_code,
                'last_close': np.nan,
                'close_date': pd.NaT,
            }

    # Get latest values
    last_close = prices.iloc[-1] if len(prices) > 0 else np.nan

    # Use scheme_code to look up NAV (not nse_code)
    last_nav_row = nav_df[nav_df['scheme_code'].astype(str) == str(scheme_code)]
    if not last_nav_row.empty:
        last_nav_row = last_nav_row.sort_values('trade_date', ascending=False).iloc[0]
        last_nav = last_nav_row['nav']
    else:
        last_nav = np.nan

    # Calculate returns for different periods. Data ingress is shared; only
    # the lookback methodology changes here.
    returns = {}
    if calculation_method == CALCULATION_METHOD_EXACT_MONTHS:
        for period_name in RETURN_PERIODS_DAYS:
            returns[f'{period_name}m_return'] = calculate_returns_from_exact_months(
                prices, period_name, holidays
            )
            returns[f'{period_name}m_annualized'] = calculate_annualized_return_from_months(
                prices, period_name
            )
    else:
        for period_name, days in RETURN_PERIODS_DAYS.items():
            returns[f'{period_name}m_return'] = calculate_returns(prices, days)
            returns[f'{period_name}m_annualized'] = calculate_annualized_return(prices, days)

    # Calculate Sharpe ratios
    sharpe = {}
    if calculation_method == CALCULATION_METHOD_EXACT_MONTHS:
        for period_name in RETURN_PERIODS_DAYS:
            sharpe[f'{period_name}m_sharpe'] = calculate_sharpe_ratio_from_exact_months(
                prices, period_name, risk_free_rate, holidays
            )
    else:
        for period_name, days in RETURN_PERIODS_DAYS.items():
            sharpe[f'{period_name}m_sharpe'] = calculate_sharpe_ratio(
                prices, days, risk_free_rate
            )

    # Calculate volatility (1 year)
    volatility = (
        calculate_volatility_from_exact_months(prices, 12, holidays=holidays)
        if calculation_method == CALCULATION_METHOD_EXACT_MONTHS
        else calculate_volatility(prices, 252)
    )

    nav_date = pd.NaT
    if not last_nav_row.empty:
        nav_date = last_nav_row['trade_date']

    # Calculate DMAs
    dmas = {}
    for period in DMA_PERIODS:
        dmas[f'dma_{period}'] = calculate_dma(prices, period)

    # Calculate premium/discount
    prem_dis = calculate_premium_discount(last_close, last_nav)

    # Calculate volume metrics
    median_volume_1m = calculate_median_volume(volumes, VOLUME_MEDIAN_1M_WINDOW)
    median_volume = calculate_median_volume(volumes, volume_lookback_days)
    avg_turnover = calculate_avg_turnover(turnovers, volume_lookback_days)

    # Calculate 52-week high: max close over the last 252 trading days
    # (days method) or the last 12 exact calendar months (months method).
    # If less history is available, fall back to the max over whatever
    # data exists.
    if calculation_method == CALCULATION_METHOD_EXACT_MONTHS:
        high_52w_prices = get_exact_month_prices(prices, 12, holidays)
    else:
        high_52w_prices = prices.iloc[-252:]
    high_52w = (
        high_52w_prices.max()
        if not high_52w_prices.empty
        else prices.max()
    )

    return {
        'nse_code': nse_code,
        'last_close': last_close,
        'close_date': prices.index[-1],
        'last_nav': last_nav,
        'nav_date': nav_date,
        'premium_discount_pct': prem_dis,
        'volatility': volatility,
        'high_52w': high_52w,
        'median_volume_1m': median_volume_1m,
        'median_volume': median_volume,
        'avg_turnover': avg_turnover,
        **returns,
        **sharpe,
        **dmas
    }
