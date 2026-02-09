"""US Market Uptrend Stock Ratio Dashboard — Main Page."""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.db_client import load_all_data
from src.data_processor import get_current_status, build_sector_summary, filter_by_date_range
from src.chart_builder import build_ratio_chart, build_sector_summary_chart

st.set_page_config(
    page_title="US Market Uptrend Ratio",
    page_icon="📈",
    layout="wide",
)

st.title("US Market Uptrend Stock Ratio")


@st.cache_data(ttl=3600)
def load_data():
    """Load and process all data from SQLite."""
    return load_all_data()


# Sidebar
with st.sidebar:
    st.header("Settings")
    if st.button("Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    all_data = load_data()
    df_all = all_data.get("all")

    if df_all is not None and not df_all.empty:
        min_date = df_all["date"].min().date()
        max_date = df_all["date"].max().date()
        date_range = st.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
    else:
        date_range = None

# Main content
all_data = load_data()
df_all = all_data.get("all")

if df_all is None or df_all.empty:
    st.warning("No data available. Import data using import_excel.py first.")
    st.stop()

# Apply date filter
if date_range and len(date_range) == 2:
    start, end = date_range
    df_filtered = filter_by_date_range(df_all, start, end)
else:
    df_filtered = df_all

# Current status indicators
status = get_current_status(df_all)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Current Ratio", f"{status['ratio']:.1%}")
with col2:
    st.metric("10MA", f"{status['ratio_10ma']:.1%}" if status["ratio_10ma"] else "N/A")
with col3:
    trend_icon = "🔼" if status["trend"] == "up" else "🔽"
    st.metric("Trend", f"{trend_icon} {status['trend'].title()}")
with col4:
    if status["is_overbought"]:
        st.metric("Status", "⚠️ Overbought")
    elif status["is_oversold"]:
        st.metric("Status", "⚠️ Oversold")
    else:
        st.metric("Status", "Normal")

st.markdown(f"**Last updated:** {status['date']}")

# Full market ratio chart
st.subheader("Full Market Ratio")
fig = build_ratio_chart(df_filtered, title="US Market Uptrend Ratio")
st.plotly_chart(fig, use_container_width=True)

# Sector summary
st.subheader("Sector Summary")
summary = build_sector_summary(all_data)

col_chart, col_table = st.columns([2, 1])
with col_chart:
    fig_summary = build_sector_summary_chart(summary)
    st.plotly_chart(fig_summary, use_container_width=True)
with col_table:
    st.dataframe(
        summary.style.format({"Ratio": "{:.1%}", "10MA": "{:.1%}", "Slope": "{:.4f}"}),
        use_container_width=True,
        hide_index=True,
    )
