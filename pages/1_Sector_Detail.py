"""Sector Detail Page — individual sector analysis."""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.db_client import load_all_data
from src.data_processor import get_current_status, _sector_display_name
from src.chart_builder import build_ratio_chart

st.set_page_config(page_title="Sector Detail", page_icon="🔍", layout="wide")
st.title("Sector Detail")

SECTORS = [
    "sec_basicmaterials",
    "sec_communicationservices",
    "sec_consumercyclical",
    "sec_consumerdefensive",
    "sec_energy",
    "sec_financial",
    "sec_healthcare",
    "sec_industrials",
    "sec_realestate",
    "sec_technology",
    "sec_utilities",
]


@st.cache_data(ttl=3600)
def load_data():
    return load_all_data()


all_data = load_data()

# Sector selector
sector_names = {_sector_display_name(s): s for s in SECTORS}
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
    mask = (df["date"].dt.date >= start) & (df["date"].dt.date <= end)
    df_filtered = df[mask]
else:
    df_filtered = df

# Chart
fig = build_ratio_chart(df_filtered, title=f"{selected_display} Uptrend Ratio")
st.plotly_chart(fig, use_container_width=True)
