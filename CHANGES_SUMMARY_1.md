# ETF Screener Refactoring Summary

## Issues Fixed

### 1. NAV and Premium/Discount Not Displaying
**Root Cause:** The NAV table uses `scheme_code` for identification, while OHLC data uses `nse_code`. The code was incorrectly trying to look up NAV using `nse_code`.

**Solution:** 
- Modified `calculate_all_metrics_for_etf()` in `/workspace/calculations/metrics.py` to accept both `nse_code` (for OHLC lookup) and `scheme_code` (for NAV lookup)
- Updated `calculate_all_etf_metrics()` in `/workspace/services/processor.py` to pass both codes from the master dataframe

### 2. KeyError: 'show_all_columns'
**Root Cause:** The app was accessing `filters['show_all_columns']` directly without checking if the key exists.

**Solution:**
- Changed `app.py` to use `filters.get('show_all_columns', False)` with a safe default value

## Changes Made

### File: `/workspace/calculations/metrics.py`
1. Updated `calculate_all_metrics_for_etf()` signature:
   - Added `scheme_code: str` parameter
   - Changed NAV lookup to use `scheme_code` instead of `nse_code`
   
```python
# Before:
last_nav_row = nav_df[nav_df['scheme_code'].astype(str) == str(nse_code)]

# After:
last_nav_row = nav_df[nav_df['scheme_code'].astype(str) == str(scheme_code)]
```

### File: `/workspace/services/processor.py`
1. Updated `calculate_all_etf_metrics()` to extract and pass `scheme_code`:
```python
scheme_code = row['scheme_code']
metrics = calculate_all_metrics_for_etf(
    nse_code=nse_code,
    scheme_code=scheme_code,  # NEW
    ohlc_df=ohlc_df,
    nav_df=nav_df,
    risk_free_rate=risk_free_rate
)
```

### File: `/workspace/app.py`
1. Fixed KeyError by using safe dictionary access:
```python
# Before:
render_results_table(sorted_df, filters['selected_metric'], show_all_columns=filters['show_all_columns'])

# After:
render_results_table(
    sorted_df, 
    filters['selected_metric'], 
    show_all_columns=filters.get('show_all_columns', False)
)
```

### File: `/workspace/ui/results_table.py`
1. **DEFAULT_COLUMNS** constant defined with 10 columns in exact order:
   - ETF Name
   - Index Tracked
   - NSE Code
   - Last Close
   - Last NAV
   - Prem/Dis to NAV %
   - 50 DMA
   - 100 DMA
   - 200 DMA
   - 5D Avg Traded Value

2. **COLUMN_MAPPING** moved to module level for consistent column name mapping

3. **get_metric_display_name()** helper function added to convert internal metric names to display names

4. **prepare_display_dataframe()** updated:
   - Accepts `selected_metric` and `show_all_columns` parameters
   - Shows only default columns + selected metric by default
   - Selected metric inserted after "Prem/Dis to NAV %" (position 6)
   - All columns shown when `show_all_columns=True`

5. **render_results_table()** updated:
   - Added `show_all_columns` parameter (defaults to False)
   - Fixed formatting functions to work correctly with pandas styler

### File: `/workspace/ui/sidebar.py`
1. Added "Show All Columns" checkbox in sidebar
2. Returns `show_all_columns` in filters dictionary

## Default Column Order Verification

The following columns are displayed by default in this exact order:
1. ETF Name
2. Index Tracked
3. NSE Code
4. Last Close
5. Last NAV ✓ (Now working with scheme_code lookup)
6. Prem/Dis to NAV % ✓ (Now calculated correctly)
7. [Selected Return/Sharpe Metric] (e.g., 3M Return, 6M Sharpe)
8. 50 DMA
9. 100 DMA
10. 200 DMA
11. 5D Avg Traded Value

All other columns (Volatility, 52w High, Median Volumes, etc.) are optional and can be viewed by checking "Show All Columns" in the sidebar.

## Testing Performed

✓ All Python files compile successfully
✓ Format functions (currency, percentage, number) work correctly
✓ DEFAULT_COLUMNS contains all required columns in correct order
✓ get_metric_display_name() converts metric names correctly
✓ prepare_display_dataframe() shows correct columns in default and expanded views
✓ NAV lookup works correctly using scheme_code
✓ Premium/Discount calculation works correctly
✓ Sidebar returns show_all_columns in filters dict
✓ app.py uses safe .get() method for show_all_columns

