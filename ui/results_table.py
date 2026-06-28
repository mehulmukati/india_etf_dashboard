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


def prepare_display_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare the dataframe for display with proper column names and formatting.
    
    Args:
        df: DataFrame with all calculated metrics
        
    Returns:
        DataFrame ready for display with formatted column names
    """
    if df.empty:
        return df
    
    display_df = df.copy()
    
    # Map internal column names to display names
    column_mapping = {
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
    
    # Add return columns
    for period in ['3', '6', '9', '12']:
        column_mapping[f'{period}m_return'] = f'{period}M Return'
        column_mapping[f'{period}m_annualized'] = f'{period}M Ann. Return'
        column_mapping[f'{period}m_sharpe'] = f'{period}M Sharpe'
    
    # Add average columns
    column_mapping['avg_3_6_9_12m_return'] = 'Avg 3/6/9/12M Return'
    column_mapping['avg_3_6m_return'] = 'Avg 3/6M Return'
    column_mapping['avg_6_9_12m_return'] = 'Avg 6/9/12M Return'
    column_mapping['avg_9_12m_return'] = 'Avg 9/12M Return'
    column_mapping['avg_3_6_9_12m_sharpe'] = 'Avg 3/6/9/12M Sharpe'
    column_mapping['avg_3_6m_sharpe'] = 'Avg 3/6M Sharpe'
    column_mapping['avg_6_9_12m_sharpe'] = 'Avg 6/9/12M Sharpe'
    column_mapping['avg_9_12m_sharpe'] = 'Avg 9/12M Sharpe'
    
    # Rename columns that exist in the dataframe
    existing_cols = set(display_df.columns)
    rename_dict = {k: v for k, v in column_mapping.items() if k in existing_cols}
    display_df = display_df.rename(columns=rename_dict)
    
    return display_df


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
    use_container_width: bool = True
) -> None:
    """
    Render the results table with proper formatting and sorting.
    
    Args:
        df: DataFrame with all calculated and filtered data
        selected_metric: Currently selected metric for highlighting
        use_container_width: Whether to use full container width
    """
    if df.empty:
        st.warning("No ETFs match the selected filters.")
        return
    
    # Prepare display dataframe
    display_df = prepare_display_dataframe(df)
    
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
            styler = styler.format({col: lambda x: format_currency(x)})
    
    # Apply formatting to percentage columns
    for col in percentage_columns:
        if col in display_df.columns:
            styler = styler.format({col: lambda x: format_percentage(x)})
    
    # Highlight the selected metric column
    metric_display_name = selected_metric.replace('_', ' ').title()
    # Map common patterns
    if 'return' in selected_metric.lower():
        metric_display_name = metric_display_name.replace('Return', 'M Return').replace('M M', 'M')
    if 'sharpe' in selected_metric.lower():
        metric_display_name = metric_display_name.replace('Sharpe', 'M Sharpe').replace('M M', 'M')
    
    if metric_display_name in display_df.columns:
        styler = styler.highlight_max(
            subset=[metric_display_name],
            props='background-color: #d4edda; color: #155724'
        )
    
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
