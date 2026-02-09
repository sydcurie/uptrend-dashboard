"""Sector Detail Page — individual sector analysis."""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.constants import SECTORS
from src.db_client import load_all_data
from src.data_processor import get_current_status, get_sector_display_name, filter_by_date_range
from src.chart_builder import build_ratio_chart

st.set_page_config(page_title="Sector Detail", page_icon="🔍", layout="wide")
st.title("Sector Detail")

with st.sidebar:
    st.markdown("---")
    st.markdown(
        "Deep dive into individual sector uptrend ratios "
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


@st.cache_data(ttl=3600)
def load_data():
    return load_all_data()


all_data = load_data()

# Sector selector
sector_names = {get_sector_display_name(s): s for s in SECTORS}
selected_display = st.selectbox("Select Sector", list(sector_names.keys()))
selected_key = sector_names[selected_display]

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
    st.metric("10MA", f"{status['ratio_10ma']:.1%}" if status["ratio_10ma"] else "N/A")
with col3:
    trend_icon = "🔼" if status["trend"] == "up" else "🔽"
    st.metric("Trend", f"{trend_icon} {status['trend'].title()}")
with col4:
    st.metric("Slope", f"{status['slope']:.4f}")
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
