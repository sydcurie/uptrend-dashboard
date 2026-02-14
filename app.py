"""US Market Uptrend Stock Ratio Dashboard — Main Page."""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.db_client import load_all_data
from src.data_processor import (
    get_current_status,
    build_sector_summary,
    filter_by_date_range,
    prepare_timeseries_csv,
    prepare_market_status_csv,
)
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

    st.markdown("---")
    st.markdown(
        "Tracks the percentage of US stocks in an uptrend "
        "across the full market and 11 sectors. "
        'Data is collected daily from <a href="https://finviz.com/?affilId=279192576" target="_blank" rel="noopener noreferrer">Finviz</a>.',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown(
        'Made with <img src="https://streamlit.io/images/brand/streamlit-mark-color.png" alt="Streamlit" height="16"> by <a href="https://github.com/tradermonty">@tradermonty</a>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-yellow?style=for-the-badge&logo=buy-me-a-coffee)](https://buymeacoffee.com/tradermonty)'
    )

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
    st.metric("10MA", f"{status['ratio_10ma']:.1%}" if status["ratio_10ma"] is not None else "N/A")
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

fig_summary = build_sector_summary_chart(summary)
event = st.plotly_chart(fig_summary, use_container_width=True, on_select="rerun", key="sector_summary")

if event and event.selection and event.selection.points:
    point = event.selection.points[0]
    customdata = point.get("customdata")
    if customdata:
        st.session_state["selected_sector"] = customdata
        st.switch_page("pages/1_Sector_Detail.py")

STATUS_STYLES = {
    "Overbought": "color: #d62728",
    "Oversold": "color: #2ca02c",
    "Normal": "color: #1f77b4",
}


def color_row(row):
    styles = []
    for col in row.index:
        if col == "Trend":
            styles.append("color: #00cc96" if row["Trend"] == "Up" else "color: #ef553b")
        elif col == "Status":
            styles.append(STATUS_STYLES.get(row["Status"], ""))
        else:
            styles.append("")
    return styles


table_event = st.dataframe(
    summary.drop(columns=["_key"]).style
    .format({"Ratio": "{:.1%}", "10MA": "{:.1%}", "Slope": "{:.4f}"})
    .apply(color_row, axis=1),
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    key="sector_table",
)

if table_event and table_event.selection and table_event.selection.rows:
    selected_row = table_event.selection.rows[0]
    selected_key = summary.iloc[selected_row]["_key"]
    st.session_state["selected_sector"] = selected_key
    st.switch_page("pages/1_Sector_Detail.py")

# Data Download
st.markdown("---")
st.subheader("Data Download")

col_dl1, col_dl2, col_dl3 = st.columns(3)
with col_dl1:
    ts_csv = prepare_timeseries_csv(df_filtered)
    st.download_button(
        "Download Ratio Time Series",
        ts_csv.to_csv(index=False),
        "uptrend_ratio_timeseries.csv",
        "text/csv",
    )
with col_dl2:
    st.download_button(
        "Download Sector Summary",
        summary.drop(columns=["_key"]).to_csv(index=False),
        "sector_summary.csv",
        "text/csv",
    )
with col_dl3:
    ms_csv = prepare_market_status_csv(status)
    st.download_button(
        "Download Market Status",
        ms_csv.to_csv(index=False),
        "market_status_latest.csv",
        "text/csv",
    )
