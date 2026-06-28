"""
Global constants, cache TTLs, and default configuration values.
"""

# Cache TTLs (in seconds)
NAV_CACHE_TTL = 43200  # 12 hours
OHLC_CACHE_TTL = 86400  # 24 hours
MASTER_CACHE_TTL = 86400  # 24 hours

# Default risk-free rate (annualized, in percentage)
DEFAULT_RISK_FREE_RATE = 0.065

# Rolling window for historical data (in days)
HISTORICAL_DATA_DAYS = 365

# DMA periods
DMA_PERIODS = [50, 100, 200]

# Volume calculation windows
VOLUME_MEDIAN_1M_WINDOW = 21  # ~1 trading month
VOLUME_MEDIAN_5D_WINDOW = 5
VOLUME_AVG_5D_WINDOW = 5

# Return calculation periods (in months)
RETURN_PERIODS = [3, 6, 9, 12]
# Convert to approximate number of trading days (assuming ~22 trading days per month)
RETURN_PERIODS_DAYS = {3: 66, 6: 132, 9: 198, 12: 264}

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
MASTER_COLUMNS = ["id", "scheme_code", "nse_code", "is_active", "index_tracked", "category"]
NAV_COLUMNS = ["id", "scheme_code", "trade_date", "nav"]
OHLC_COLUMNS = ["id", "nse_code", "trade_date", "open", "high", "low", "close", "volume", "turnover"]
