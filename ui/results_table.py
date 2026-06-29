"""
UI module for formatting and rendering the results table.
"""
import streamlit as st
import pandas as pd
from typing import List, Optional


def format_currency(value: float) -> str:
    """Format a value as Indian currency."""
    if pd.isna(value):
        return "N/A"
    
    if value >= 1_00_00_000:  # 1 crore
        return f"₹{value/1_00_00_000:.2f} Cr"
    elif value >= 1_00_000:  # 1 lakh
        return f"₹{value/1_00_000:.2f} L"
    elif value >= 1000:
        return f"₹{value/1000:.2f} K"
    else:
        return f"₹{value:.2f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format a decimal as percentage."""
    if pd.isna(value):
        return "N/A"
    return f"{value * 100:.{decimals}f}%"


def format_number(value: float, decimals: int = 2) -> str:
    """Format a number with specified decimals."""
    if pd.isna(value):
        return "N/A"
    return f"{value:.{decimals}f}"


# Default columns to display (in order)
DEFAULT_COLUMNS = [
    'ETF Name',
    'Index Tracked',
    'NSE Code',
    'Last Close',
    'Last NAV',
    'Prem/Dis to NAV %',
    '50 DMA',
    '100 DMA',
    '200 DMA',
    '5D Avg Traded Value'
]

# Column name mapping from internal to display names
COLUMN_MAPPING = {
    'nse_code': 'NSE Code',
    'scheme_name': 'ETF Name',
    'index_tracked': 'Index Tracked',
    'category': 'Category',
    'last_close': 'Last Close',
    'last_nav': 'Last NAV',
    'premium_discount_pct': 'Prem/Dis to NAV %',
    'volatility': 'Volatility (Ann.)',
    'high_52w': '52w High',
    'median_volume_1m': '1M Median Volume',
    'median_volume_5d': '5D Median Volume',
    'avg_turnover_5d': '5D Avg Traded Value',
    'dma_50': '50 DMA',
    'dma_100': '100 DMA',
    'dma_200': '200 DMA'
}

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
    show_all_columns: bool = False
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
    
    # Rename columns using the mapping
    existing_cols = set(display_df.columns)
    rename_dict = {k: v for k, v in COLUMN_MAPPING.items() if k in existing_cols}
    display_df = display_df.rename(columns=rename_dict)
    
    # Determine which columns to show
    if show_all_columns:
        # Show all columns
        columns_to_show = [col for col in display_df.columns if col in list(COLUMN_MAPPING.values())]
    else:
        # Show only default columns + the selected metric
        metric_col = get_metric_display_name(selected_metric)
        columns_to_show = DEFAULT_COLUMNS.copy()
        
        # Add the selected metric column if it exists and is not already in defaults
        if metric_col in display_df.columns and metric_col not in columns_to_show:
            # Insert the metric column after Prem/Dis to NAV % (position 6)
            insert_pos = 6
            columns_to_show.insert(insert_pos, metric_col)
        
        # Filter to only columns that exist in the dataframe
        columns_to_show = [col for col in columns_to_show if col in display_df.columns]
    
    return display_df[columns_to_show]


def get_table_column_config() -> dict:
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
        'Last NAV': {'type': 'currency'},
        'Prem/Dis to NAV %': {'type': 'percentage', 'format': '{:.2f}'},
        'Volatility (Ann.)': {'type': 'percentage', 'format': '{:.2f}'},
        '52w High': {'type': 'currency'},
        '1M Median Volume': {'type': 'number'},
        '5D Median Volume': {'type': 'number'},
        '5D Avg Traded Value': {'type': 'currency'}
    }


def render_results_table(
    df: pd.DataFrame,
    selected_metric: str,
    width: bool = True,
    show_all_columns: bool = False
) -> None:
    """
    Render the results table with proper formatting and sorting.
    
    Args:
        df: DataFrame with all calculated and filtered data
        selected_metric: Currently selected metric for highlighting
        width: Whether to use full container width
        show_all_columns: If True, show all available columns; otherwise show only defaults
    """
    if df.empty:
        st.warning("No ETFs match the selected filters.")
        return
    
    # Prepare display dataframe
    display_df = prepare_display_dataframe(df, selected_metric, show_all_columns)
    
    # Format numeric columns
    numeric_columns = [
        'Last Close', 'Last NAV', '52w High',
        '1M Median Volume', '5D Median Volume'
    ]
    
    percentage_columns = [
        'Prem/Dis to NAV %', 'Volatility (Ann.)'
    ]
    
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
    
    # Create styled dataframe
    styler = display_df.style
    
    # Apply formatting to numeric columns
    for col in numeric_columns:
        if col in display_df.columns:
            styler = styler.format({col: format_currency})
    
    # Apply formatting to percentage columns
    for col in percentage_columns:
        if col in display_df.columns:
            styler = styler.format({col: format_percentage})
    
    # Highlight the selected metric column
    metric_display_name = get_metric_display_name(selected_metric)
    
    if metric_display_name in display_df.columns:
        styler = styler.highlight_max(
            subset=[metric_display_name],
            props='background-color: #d4edda; color: #155724'
        )
    
    # Display the table
    st.dataframe(
        styler,
        width=width,
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
