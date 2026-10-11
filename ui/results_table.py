"""
UI module for formatting and rendering the results table.
"""
import streamlit as st
import pandas as pd
from typing import List, Optional
from config import VOLUME_LOOKBACK_DEFAULT_DAYS


def format_currency(value: float, decimals: int = 2) -> str:
    """Format a value as Indian currency with the requested precision."""
    if pd.isna(value):
        return "N/A"
    
    if value >= 1_00_00_000:  # 1 crore
        return f"₹{value/1_00_00_000:.{decimals}f} Cr"
    elif value >= 1_00_000:  # 1 lakh
        return f"₹{value/1_00_000:.{decimals}f} L"
    elif value >= 1000:
        return f"₹{value/1000:.{decimals}f} K"
    else:
        return f"₹{value:.{decimals}f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format a decimal as percentage."""
    if pd.isna(value):
        return "N/A"
    return f"{value * 100:.{decimals}f}%"


def format_percentage_points(value: float, decimals: int = 2) -> str:
    """Format a value already expressed in percentage points."""
    if pd.isna(value):
        return "N/A"
    return f"{value:.{decimals}f}%"


def format_date(value) -> str:
    """Format timestamp-like values as an ISO calendar date only."""
    if pd.isna(value):
        return "N/A"
    return pd.Timestamp(value).strftime('%Y-%m-%d')


def format_number(value: float, decimals: int = 2) -> str:
    """Format a number with specified decimals."""
    if pd.isna(value):
        return "N/A"
    return f"{value:.{decimals}f}"


# Default columns to display (in order), represented by internal keys so the
# selected lookback can be reflected in the displayed volume labels.
DEFAULT_COLUMN_KEYS = [
    'scheme_name',
    'index_tracked',
    'nse_code',
    'last_close',
    'close_date',
    'last_nav',
    'nav_date',
    'premium_discount_pct',
    'avg_turnover',
    'dma_50',
    'dma_100',
    'dma_200'
]

# Column name mapping from internal to display names
COLUMN_MAPPING = {
    'nse_code': 'NSE Code',
    'scheme_name': 'ETF Name',
    'index_tracked': 'Index Tracked',
    'category': 'Category',
    'last_close': 'Last Close',
    'close_date': 'Close Price Date',
    'last_nav': 'Last NAV',
    'nav_date': 'NAV Date',
    'premium_discount_pct': 'Prem/Dis to NAV %',
    'volatility': 'Volatility (Ann.)',
    'high_52w': '52w High',
    'median_volume_1m': '1M Median Volume',
    'median_volume': 'Median Volume',
    'avg_turnover': 'Avg Traded Value',
    'dma_50': '50 DMA',
    'dma_100': '100 DMA',
    'dma_200': '200 DMA'
}


def get_column_mapping(volume_lookback_days: int = VOLUME_LOOKBACK_DEFAULT_DAYS) -> dict:
    """Return display labels using the selected volume lookback period."""
    mapping = COLUMN_MAPPING.copy()
    mapping['median_volume'] = f'{volume_lookback_days}D Median Volume'
    mapping['avg_turnover'] = f'{volume_lookback_days}D Avg Traded Value'
    return mapping

# Add return and sharpe columns to mapping
for period in ['3', '6', '9', '12']:
    COLUMN_MAPPING[f'{period}m_return'] = f'{period}M Return'
    COLUMN_MAPPING[f'{period}m_annualized'] = f'{period}M Ann. Return'
    COLUMN_MAPPING[f'{period}m_sharpe'] = f'{period}M Sharpe'

# Add average columns
COLUMN_MAPPING['avg_3_6_9_12m_return'] = 'Avg 3/6/9/12M Return'
COLUMN_MAPPING['avg_3_6m_return'] = 'Avg 3/6M Return'
COLUMN_MAPPING['avg_6_9_12m_return'] = 'Avg 6/9/12M Return'
COLUMN_MAPPING['avg_9_12m_return'] = 'Avg 9/12M Return'
COLUMN_MAPPING['avg_3_6_9_12m_sharpe'] = 'Avg 3/6/9/12M Sharpe'
COLUMN_MAPPING['avg_3_6m_sharpe'] = 'Avg 3/6M Sharpe'
COLUMN_MAPPING['avg_6_9_12m_sharpe'] = 'Avg 6/9/12M Sharpe'
COLUMN_MAPPING['avg_9_12m_sharpe'] = 'Avg 9/12M Sharpe'


def get_metric_display_name(selected_metric: str) -> str:
    """
    Get the display name for the selected metric column.
    
    Args:
        selected_metric: Internal metric name (e.g., '3m_return', '6m_sharpe')
        
    Returns:
        Display name for the metric
    """
    if selected_metric in COLUMN_MAPPING:
        return COLUMN_MAPPING[selected_metric]
    
    # Fallback: convert internal name to display name
    display_name = selected_metric.replace('_', ' ').title()
    if 'return' in selected_metric.lower():
        display_name = display_name.replace('Return', 'M Return').replace('M M', 'M')
    if 'sharpe' in selected_metric.lower():
        display_name = display_name.replace('Sharpe', 'M Sharpe').replace('M M', 'M')
    return display_name


def prepare_display_dataframe(
    df: pd.DataFrame,
    selected_metric: str,
    show_all_columns: bool = False,
    volume_lookback_days: int = VOLUME_LOOKBACK_DEFAULT_DAYS
) -> pd.DataFrame:
    """
    Prepare the dataframe for display with proper column names and formatting.
    
    Args:
        df: DataFrame with all calculated metrics
        selected_metric: Currently selected metric for highlighting
        show_all_columns: If True, show all available columns; otherwise show only defaults
        
    Returns:
        DataFrame ready for display with formatted column names
    """
    if df.empty:
        return df
    
    display_df = df.copy()
    column_mapping = get_column_mapping(volume_lookback_days)
    
    # Rename columns using the mapping
    existing_cols = set(display_df.columns)
    rename_dict = {k: v for k, v in column_mapping.items() if k in existing_cols}
    display_df = display_df.rename(columns=rename_dict)
    
    # Determine which columns to show
    if show_all_columns:
        # Show all columns
        columns_to_show = [col for col in display_df.columns if col in list(column_mapping.values())]
    else:
        # Show only default columns + the selected metric
        metric_col = column_mapping.get(selected_metric, get_metric_display_name(selected_metric))
        columns_to_show = [
            column_mapping[key]
            for key in DEFAULT_COLUMN_KEYS
            if key in existing_cols
        ]
        
        # Add the selected metric column if it exists and is not already in defaults
        if metric_col in display_df.columns and metric_col not in columns_to_show:
            # Insert the metric column after Prem/Dis to NAV % (position 6)
            insert_pos = 6
            columns_to_show.insert(insert_pos, metric_col)
        
        # Filter to only columns that exist in the dataframe
        columns_to_show = [col for col in columns_to_show if col in display_df.columns]
    
    return display_df[columns_to_show]


def get_table_column_config(
    volume_lookback_days: int = VOLUME_LOOKBACK_DEFAULT_DAYS
) -> dict:
    """
    Get column configuration for the results table.
    
    Returns:
        Dictionary mapping column names to their display configuration
    """
    return {
        'ETF Name': {'width': '200px'},
        'Index Tracked': {'width': '200px'},
        'NSE Code': {'width': '100px'},
        'Last Close': {'type': 'currency'},
        'Close Price Date': {'width': '125px'},
        'Last NAV': {'type': 'currency'},
        'NAV Date': {'width': '125px'},
        'Prem/Dis to NAV %': {'type': 'percentage', 'format': '{:.2f}'},
        'Volatility (Ann.)': {'type': 'percentage', 'format': '{:.2f}'},
        '52w High': {'type': 'currency'},
        '1M Median Volume': {'type': 'number'},
        f'{volume_lookback_days}D Median Volume': {'type': 'number'},
        f'{volume_lookback_days}D Avg Traded Value': {'type': 'currency'}
    }


def render_results_table(
    df: pd.DataFrame,
    selected_metric: str,
    use_container_width: bool = True,
    show_all_columns: bool = False,
    volume_lookback_days: int = VOLUME_LOOKBACK_DEFAULT_DAYS
) -> None:
    """
    Render the results table with proper formatting and sorting.
    
    Args:
        df: DataFrame with all calculated and filtered data
        selected_metric: Currently selected metric for highlighting
        use_container_width: Whether to use full container width
        show_all_columns: If True, show all available columns; otherwise show only defaults
    """
    if df.empty:
        st.warning("No ETFs match the selected filters.")
        return
    
    # Prepare display dataframe
    display_df = prepare_display_dataframe(
        df,
        selected_metric,
        show_all_columns,
        volume_lookback_days
    )
    
    # Format numeric columns
    currency_columns = ['Last Close', 'Last NAV', '52w High']
    dma_columns = ['50 DMA', '100 DMA', '200 DMA']
    volume_lookback_label = f'{volume_lookback_days}D Median Volume'
    traded_value_label = f'{volume_lookback_days}D Avg Traded Value'
    volume_columns = [volume_lookback_label]
    no_decimal_currency_columns = [traded_value_label]
    date_columns = ['Close Price Date', 'NAV Date']
    
    # Percentage columns – dynamically detect returns, annualized returns,
    # premium/discount, and volatility.
    percentage_columns = []
    sharpe_columns = []
    premium_discount_columns = []
    # Reverse mapping: display name -> internal key
    rev_mapping = {v: k for k, v in get_column_mapping(volume_lookback_days).items()}
    for col in display_df.columns:
        internal = rev_mapping.get(col)
        if internal:
            if (
                internal.endswith('_return')
                or internal.endswith('_annualized')
                or internal == 'volatility'
            ):
                percentage_columns.append(col)
            elif internal.endswith('_sharpe'):
                sharpe_columns.append(col)
            elif internal == 'premium_discount_pct':
                premium_discount_columns.append(col)
    
    # Apply formatting using styler
    def format_column(value, col_type):
        if pd.isna(value):
            return "N/A"
        if col_type == 'currency':
            return format_currency(value)
        elif col_type == 'percentage':
            return format_percentage(value)
        else:
            return format_number(value)
    
    # Build one formatter mapping. Calling Styler.format repeatedly resets
    # formatters registered by earlier calls, so all column formatters must be
    # applied together.
    formatters = {}

    # Apply Indian currency formatting to prices and 52-week high.
    for col in currency_columns:
        if col in display_df.columns:
            formatters[col] = format_currency

    # Apply two-decimal numeric formatting to DMA values.
    for col in dma_columns:
        if col in display_df.columns:
            formatters[col] = lambda value: format_number(value, 2)

    # Volumes are counts, so display the requested five-day volume with no decimals.
    for col in volume_columns:
        if col in display_df.columns:
            formatters[col] = lambda value: format_number(value, 0)

    # Traded value retains Indian currency notation but has no decimals.
    for col in no_decimal_currency_columns:
        if col in display_df.columns:
            formatters[col] = lambda value: format_currency(value, 0)
    
    # Apply formatting to percentage columns
    for col in percentage_columns:
        if col in display_df.columns:
            formatters[col] = format_percentage

    for col in premium_discount_columns:
        if col in display_df.columns:
            formatters[col] = format_percentage_points

    for col in sharpe_columns:
        if col in display_df.columns:
            formatters[col] = lambda value: format_number(value, 2)

    for col in date_columns:
        if col in display_df.columns:
            formatters[col] = format_date

    styler = display_df.style.format(formatters)
    
    # Display the table
    st.dataframe(
        styler,
        use_container_width=use_container_width,
        hide_index=True
    )


def render_summary_stats(df: pd.DataFrame) -> None:
    """
    Render summary statistics about the filtered results.
    
    Args:
        df: Filtered DataFrame
    """
    if df.empty:
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total ETFs", len(df))
    
    with col2:
        unique_indices = df['index_tracked'].nunique() if 'index_tracked' in df.columns else 0
        st.metric("Unique Indices", unique_indices)
    
    with col3:
        categories = df['category'].unique() if 'category' in df.columns else []
        st.metric("Categories", len(categories))


def export_to_csv(df: pd.DataFrame, filename: str = "etf_screener_results.csv") -> None:
    """
    Provide CSV download button for the results.
    
    Args:
        df: DataFrame to export
        filename: Name of the CSV file
    """
    if df.empty:
        return
    
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download Results as CSV",
        data=csv,
        file_name=filename,
        mime="text/csv"
    )
