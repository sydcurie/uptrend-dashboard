"""Industry Detail Page — individual industry analysis."""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.constants import INDUSTRIES, SECTORS, SECTOR_INDUSTRIES
from src.db_client import cached_load_all_data
from src.data_processor import (
    get_current_status,
    get_industry_display_name,
    get_sector_display_name,
    get_sector_for_industry,
    filter_by_date_range,
    prepare_timeseries_csv,
)
from src.chart_builder import build_ratio_chart

st.set_page_config(page_title="Industry Detail", page_icon="🏭", layout="wide")
st.title("Industry Detail")

with st.sidebar:
    st.markdown("---")
    st.markdown(
        "Deep dive into individual industry uptrend ratios "
        "with trend direction, 10-day moving average, "
        "and overbought/oversold indicators."
    )

    st.markdown("---")
    st.markdown(
        'Made with <img src="https://streamlit.io/images/brand/streamlit-mark-color.png" alt="Streamlit" height="16"> by <a href="https://github.com/tradermonty">@tradermonty</a>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-yellow?style=for-the-badge&logo=buy-me-a-coffee)](https://buymeacoffee.com/tradermonty)'
    )


def load_data():
    return cached_load_all_data()


all_data = load_data()

# Two-stage selector: Sector filter → Industry select
sector_display_names = {get_sector_display_name(s): s for s in SECTORS}
sector_filter_options = ["All Sectors"] + list(sector_display_names.keys())
selected_sector_display = st.selectbox("Filter by Sector", sector_filter_options)

if selected_sector_display == "All Sectors":
    available_industries = INDUSTRIES
else:
    sector_key = sector_display_names[selected_sector_display]
    available_industries = SECTOR_INDUSTRIES.get(sector_key, [])

industry_names = {get_industry_display_name(ind): ind for ind in available_industries}
industry_display_list = sorted(industry_names.keys())

if not industry_display_list:
    st.warning("No industries available.")
    st.stop()

# Pre-selection from Sector Detail drilldown
preselected_key = st.session_state.pop("selected_industry", None)
default_index = 0
if preselected_key:
    preselected_display = get_industry_display_name(preselected_key)
    if preselected_display in industry_display_list:
        default_index = industry_display_list.index(preselected_display)

selected_display = st.selectbox("Select Industry", industry_display_list, index=default_index)
selected_key = industry_names[selected_display]

# Show parent sector
parent_sector = get_sector_for_industry(selected_key)
if parent_sector:
    parent_display = get_sector_display_name(parent_sector)
    st.caption(f"Parent Sector: {parent_display}")

df = all_data.get(selected_key)

if df is None or df.empty:
    st.warning(f"No data available for {selected_display}.")
    st.stop()

# Status indicators
status = get_current_status(df)

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Ratio", f"{status['ratio']:.1%}")
with col2:
    st.metric("10MA", f"{status['ratio_10ma']:.1%}" if status["ratio_10ma"] is not None else "N/A")
with col3:
    trend_icons = {"up": "🔼", "down": "🔽", "neutral": "➖"}
    st.metric("Trend", f"{trend_icons.get(status['trend'], '➖')} {status['trend'].title()}")
with col4:
    st.metric("Slope", f"{status['slope']:.4f}" if status["slope"] is not None else "N/A")
with col5:
    if status["is_overbought"]:
        st.metric("Status", "⚠️ Overbought")
    elif status["is_oversold"]:
        st.metric("Status", "⚠️ Oversold")
    else:
        st.metric("Status", "Normal")

# Date filter
min_date = df["date"].min().date()
max_date = df["date"].max().date()
date_range = st.date_input(
    "Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if date_range and len(date_range) == 2:
    start, end = date_range
    df_filtered = filter_by_date_range(df, start, end)
else:
    df_filtered = df

# Chart
fig = build_ratio_chart(df_filtered, title=f"{selected_display} Uptrend Ratio")
st.plotly_chart(fig, use_container_width=True)

# Data Download
st.markdown("---")
st.subheader("Data Download")
ts_csv = prepare_timeseries_csv(df_filtered)
st.download_button(
    f"Download {selected_display} Time Series",
    ts_csv.to_csv(index=False),
    f"{selected_key}_timeseries.csv",
    "text/csv",
)
