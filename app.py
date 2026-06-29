"""
ETF Screener Application - Main Orchestrator
Lean entry point that coordinates data fetching, calculations, and UI rendering.
"""
import streamlit as st
from services.processor import load_all_data, calculate_all_etf_metrics, process_screener
from ui.sidebar import build_sidebar
from ui.results_table import render_results_table, render_summary_stats, export_to_csv


def main():
    st.set_page_config(page_title="ETF Screener", page_icon="📊", layout="wide")
    st.title("📊 ETF Screener")
    st.markdown("Find top-performing ETFs across different indices with advanced filtering.")

    filters = build_sidebar()

    with st.spinner("Loading ETF data..."):
        master_df, nav_df, ohlc_df = load_all_data()


	st.write("### Data Debug Info")
	st.write(f"Master rows: {len(master_df)}")
	st.write(f"NAV rows: {len(nav_df)}")
	st.write(f"OHLC rows: {len(ohlc_df)}")

	if not ohlc_df.empty:
	    st.write(f"OHLC date range: {ohlc_df['trade_date'].min()} to {ohlc_df['trade_date'].max()}")
	    st.write(f"Unique NSE codes in OHLC: {ohlc_df['nse_code'].nunique()}")
	    st.dataframe(ohlc_df.head(10))
	    st.dataframe(master_df.head(10))


    if master_df.empty or ohlc_df.empty:
        st.error("Unable to load ETF data. Please check your database connection.")
        return

    with st.spinner("Calculating metrics..."):
        results_df = calculate_all_etf_metrics(master_df, nav_df, ohlc_df, filters['risk_free_rate'])

    if results_df.empty:
        st.warning("No ETF data available for analysis.")
        return

    sorted_df = process_screener(results_df, filters)
    render_summary_stats(sorted_df)
    st.divider()
    render_results_table(
        sorted_df,
        filters['selected_metric'],
        show_all_columns=filters.get('show_all_columns', False)
    )
    st.divider()
    export_to_csv(sorted_df)


if __name__ == "__main__":
    main()