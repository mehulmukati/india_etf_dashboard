"""
UI module for building sidebar filter controls.
"""
import streamlit as st
from typing import Dict, List, Tuple
from config import (
    DMA_PERIODS
)
from calculations.filters import get_available_metric_options


def build_metric_dropdown() -> str:
    """
    Build the main metric dropdown for sorting/filtering.
    
    Returns:
        Selected metric key
    """
    options = get_available_metric_options()
    
    # Group options by category
    returns_options = [opt for opt in options if opt['group'] == 'Returns']
    sharpe_options = [opt for opt in options if opt['group'] == 'Sharpe']
    
    # Create formatted labels with optgroups using HTML-like structure
    # Streamlit doesn't support true optgroups, so we use separators
    all_labels = []
    all_keys = []
    
    # Returns section
    all_labels.append("--- Returns ---")
    all_keys.append(None)
    
    for opt in returns_options:
        all_labels.append(opt['name'])
        all_keys.append(opt['key'])
    
    # Sharpe section
    all_labels.append("--- Sharpe ---")
    all_keys.append(None)
    
    for opt in sharpe_options:
        all_labels.append(opt['name'])
        all_keys.append(opt['key'])
    
    # Filter out separator entries for actual selection
    selectable_labels = [label for label in all_labels if not label.startswith('---')]
    selectable_keys = [key for key in all_keys if key is not None]
    
    selected_label = st.selectbox(
        "Select Metric",
        options=selectable_labels,
        index=0,
        help="Choose a metric to rank ETFs. The top performer for each index will be shown."
    )
    
    # Map label back to key
    selected_index = selectable_labels.index(selected_label)
    selected_key = selectable_keys[selected_index]
    
    return selected_key


def build_risk_free_rate_input() -> float:
    """
    Build risk-free rate input field.
    
    Returns:
        Selected risk-free rate as decimal
    """
    rate_pct = st.number_input(
        "Risk-Free Rate (%)",
        min_value=0.0,
        max_value=50.0,
        value=6.50,
        step=0.25,
        help="Annual risk-free rate used for Sharpe ratio calculation"
    )
    
    return rate_pct / 100


def build_dma_filters() -> Tuple[bool, bool, bool]:
    """
    Build DMA filter checkboxes.
    
    Returns:
        Tuple of (above_50_dma, above_100_dma, above_200_dma)
    """
    st.subheader("DMA Filters")
    
    above_50 = st.checkbox(
        f"Above {DMA_PERIODS[0]} DMA",
        value=False,
        help=f"Show only ETFs trading above their {DMA_PERIODS[0]}-day moving average"
    )
    
    above_100 = st.checkbox(
        f"Above {DMA_PERIODS[1]} DMA",
        value=False,
        help=f"Show only ETFs trading above their {DMA_PERIODS[1]}-day moving average"
    )
    
    above_200 = st.checkbox(
        f"Above {DMA_PERIODS[2]} DMA",
        value=False,
        help=f"Show only ETFs trading above their {DMA_PERIODS[2]}-day moving average"
    )
    
    return above_50, above_100, above_200


def build_category_filter() -> str:
    """
    Build category filter dropdown.
    
    Returns:
        Selected category
    """
    categories = [
        'All',
        'Broad Based',
        'Thematic/Sectoral',
        'Foreign',
        'All except Foreign'
    ]
    
    selected = st.selectbox(
        "Category",
        options=categories,
        index=0,
        help="Filter ETFs by category"
    )
    
    return selected


def build_min_annual_return_filter() -> float:
    """
    Build minimum annual return filter.
    
    Returns:
        Minimum annual return as decimal
    """
    min_return_pct = st.number_input(
        "Min Annual Return (%)",
        min_value=-100.0,
        max_value=500.0,
        value=0.0,
        step=1.0,
        help="Minimum 12-month annualized return (can be negative)"
    )
    
    return min_return_pct / 100


def build_min_traded_value_filter() -> float:
    """
    Build minimum traded value filter.
    
    Returns:
        Minimum 5-day average traded value in INR
    """
    min_turnover = st.number_input(
        "Min 5-Day Avg Traded Value (INR)",
        min_value=0.0,
        value=0.0,
        step=100000.0,
        help="Minimum average daily turnover over the past 5 days"
    )
    
    return min_turnover


def build_sidebar() -> Dict:
    """
    Build the complete sidebar with all filters.
    
    Returns:
        Dictionary containing all filter values
    """
    with st.sidebar:
        st.header("Filters")
        
        # Main metric dropdown
        selected_metric = build_metric_dropdown()
        
        st.divider()
        
        # Risk-free rate
        risk_free_rate = build_risk_free_rate_input()
        
        st.divider()
        
        # DMA filters
        above_50_dma, above_100_dma, above_200_dma = build_dma_filters()
        
        st.divider()
        
        # Category filter
        category = build_category_filter()
        
        st.divider()
        
        # Minimum annual return
        min_annual_return = build_min_annual_return_filter()
        
        st.divider()
        
        # Minimum traded value
        min_traded_value = build_min_traded_value_filter()
        
        st.divider()
        
        # Table display options
        show_all_columns = st.checkbox(
            "Show All Columns",
            value=False,
            help="If checked, display all available columns. Otherwise, show only default columns plus the selected metric."
        )
        
        return {
            'selected_metric': selected_metric,
            'risk_free_rate': risk_free_rate,
            'above_50_dma': above_50_dma,
            'above_100_dma': above_100_dma,
            'above_200_dma': above_200_dma,
            'category': category,
            'min_annual_return': min_annual_return,
            'min_traded_value': min_traded_value,
            'show_all_columns': show_all_columns
        }
