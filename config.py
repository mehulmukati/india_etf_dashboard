"""
Global constants, cache TTLs, and default configuration values.
"""

# NSE Holidays
NSE_HOLIDAYS_PATH = "nse_holidays.json"   # adjust path if file is in a subdirectory
NSE_HOLIDAYS_SEGMENT = "CBM"              # CBM = equity/ETF segment

# Cache TTLs (in seconds)
NAV_CACHE_TTL = 43200  # 12 hours
OHLC_CACHE_TTL = 86400  # 24 hours
MASTER_CACHE_TTL = 86400  # 24 hours

# Default risk-free rate (annualized, in percentage)
DEFAULT_RISK_FREE_RATE = 0.065

# Rolling window for historical data (in calendar days).
# Must comfortably exceed the longest trading-day lookback used anywhere in
# calculations.py (252 trading days for 12m return/Sharpe/volatility), with
# a buffer for weekends and NSE holidays. ~365 calendar days only yields
# ~246-251 actual trading days, which is NOT enough to ever satisfy the
# strict 252-trading-day requirement - hence 400 days here for margin.
HISTORICAL_DATA_DAYS = 400

# DMA periods
DMA_PERIODS = [50, 100, 200]

# Volume calculation windows
VOLUME_MEDIAN_1M_WINDOW = 21  # ~1 trading month
VOLUME_MEDIAN_5D_WINDOW = 5
VOLUME_AVG_5D_WINDOW = 5

# Return calculation periods (in months)
RETURN_PERIODS = [3, 6, 9, 12]
# Convert to approximate number of trading days, using 21 trading days/month
# (252 / 12 = 21), consistent with the 252-trading-day/year convention used
# for annualization and volatility elsewhere in calculations.py
RETURN_PERIODS_DAYS = {3: 63, 6: 126, 9: 189, 12: 252}

# Average return period configurations
AVERAGE_RETURN_PERIODS = [
    {'name': 'Avg 3/6/9/12m', 'periods': [3, 6, 9, 12]},
    {'name': 'Avg 3/6m', 'periods': [3, 6]},
    {'name': 'Avg 6/9/12m', 'periods': [6, 9, 12]},
    {'name': 'Avg 9/12m', 'periods': [9, 12]}
]

# Database table names
TABLE_ETF_MASTER = "etf_master"
TABLE_ETF_NAV = "etf_nav"
TABLE_ETF_OHLC = "etf_ohlc"

# Column name mappings
MASTER_COLUMNS = ["id", "scheme_code", "nse_code", "scheme_name", "is_active", "index_tracked", "category"]
NAV_COLUMNS = ["id", "scheme_code", "trade_date", "nav"]
OHLC_COLUMNS = ["id", "nse_code", "trade_date", "open", "high", "low", "close", "volume", "turnover"]