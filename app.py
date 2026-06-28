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


# TEMP DIAGNOSTIC
    # TEMPORARY DIAGNOSTIC
    st.write("master_df columns:", master_df.columns.tolist())
    st.write("master_df shape:", master_df.shape)
    st.write("master_df head:", master_df.head(2))
#    st.stop()  # stops execution here so we can read the output
# TEMP DIAGNOSTIC


    if master_df.empty or ohlc_df.empty:
        st.error("Unable to load ETF data. Please check your database connection.")
        return

    with st.spinner("Calculating metrics..."):
        results_df = calculate_all_etf_metrics(master_df, nav_df, ohlc_df, filters['risk_free_rate'])

    if results_df.empty:
        st.warning("No ETF data available for analysis.")
        return

    # ── TEMPORARY DIAGNOSTIC ──────────────────────────────────────────────────
    with st.expander("🔍 Debug Info (remove before production)", expanded=True):
        st.write(f"**Total ETFs with metrics:** {len(results_df)}")
        st.write(f"**Risk-free rate received:** {filters['risk_free_rate']}")
        st.write(f"**Unique index_tracked values:** {results_df['index_tracked'].nunique()}")
        st.write(f"**Null index_tracked count:** {results_df['index_tracked'].isna().sum()}")
        st.write(f"**Empty string index_tracked:** {(results_df['index_tracked'] == '').sum()}")

        if '12m_sharpe' in results_df.columns:
            st.write(f"**12m_sharpe range:** {results_df['12m_sharpe'].min():.2f} to {results_df['12m_sharpe'].max():.2f}")
            st.write(f"**12m_sharpe NaN count:** {results_df['12m_sharpe'].isna().sum()}")
        else:
            st.write("**12m_sharpe column: MISSING**")

        if '12m_return' in results_df.columns:
            st.write(f"**12m_return range:** {results_df['12m_return'].min():.4f} to {results_df['12m_return'].max():.4f}")
            st.write(f"**12m_return NaN count:** {results_df['12m_return'].isna().sum()}")
        else:
            st.write("**12m_return column: MISSING**")

        if 'avg_turnover_5d' in results_df.columns:
            st.write(f"**avg_turnover_5d range:** {results_df['avg_turnover_5d'].min():.0f} to {results_df['avg_turnover_5d'].max():.0f}")
            st.write(f"**avg_turnover_5d NaN count:** {results_df['avg_turnover_5d'].isna().sum()}")
        else:
            st.write("**avg_turnover_5d column: MISSING**")

        st.write("**Sample data (first 10 rows):**")
        cols = ['nse_code', 'index_tracked', 'category', '12m_return', '12m_sharpe', 'avg_turnover_5d']
        available_cols = [c for c in cols if c in results_df.columns]
        st.dataframe(results_df[available_cols].head(10))

        st.write(f"**Selected metric:** {filters['selected_metric']}")
        if filters['selected_metric'] in results_df.columns:
            st.write(f"**Selected metric range:** {results_df[filters['selected_metric']].min():.4f} to {results_df[filters['selected_metric']].max():.4f}")
            st.write(f"**Selected metric NaN count:** {results_df[filters['selected_metric']].isna().sum()}")
        else:
            st.write(f"**Selected metric column '{filters['selected_metric']}': MISSING ⚠️**")

        sorted_df_debug = process_screener(results_df, filters)
        st.write(f"**ETFs after all filters:** {len(sorted_df_debug)}")
        st.write("**Post-filter sample:**")
        st.dataframe(sorted_df_debug[available_cols].head(10))
    # ── END DIAGNOSTIC ────────────────────────────────────────────────────────

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