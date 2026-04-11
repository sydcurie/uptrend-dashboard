"""Sector Comparison Page — overlay multiple sector ratios."""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.constants import SECTORS
from src.data_loader import cached_load_sector_data
from src.data_processor import get_sector_display_name, default_start_date, filter_by_date_range
from src.chart_builder import build_sector_comparison_chart

st.set_page_config(page_title="Sector Comparison", page_icon="📊", layout="wide")
st.title("Sector Comparison")

with st.sidebar:
    st.markdown("---")
    st.markdown(
        "Compare uptrend ratios across multiple sectors side by side. "
        "Identify which sectors are leading or lagging the market."
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
    return cached_load_sector_data()


all_data = load_data()

# Multi-select sectors
sector_names = {get_sector_display_name(s): s for s in SECTORS}
selected_display = st.multiselect(
    "Select Sectors",
    options=list(sector_names.keys()),
    default=list(sector_names.keys()),
)

selected_keys = [sector_names[name] for name in selected_display]

if not selected_keys:
    st.warning("Please select at least one sector.")
    st.stop()

# Date filter using first available sector
first_df = all_data.get(selected_keys[0])
if first_df is not None and not first_df.empty:
    min_date = first_df["date"].min().date()
    max_date = first_df["date"].max().date()
    default_start = default_start_date(min_date, max_date)
    date_range = st.date_input(
        "Date Range",
        value=(default_start, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if date_range and len(date_range) == 2:
        start, end = date_range
        filtered_data = {}
        for key in selected_keys:
            df = all_data.get(key)
            if df is not None:
                filtered_data[key] = filter_by_date_range(df, start, end)
    else:
        filtered_data = {k: all_data[k] for k in selected_keys if k in all_data}
else:
    filtered_data = {k: all_data[k] for k in selected_keys if k in all_data}

# Display mode toggle
display_mode = st.radio(
    "Display Mode",
    options=["Smoothed (10MA)", "Raw Ratio"],
    horizontal=True,
)
use_ma = display_mode == "Smoothed (10MA)"

# Chart
fig = build_sector_comparison_chart(filtered_data, selected_sectors=selected_keys, use_ma=use_ma)
st.plotly_chart(fig, use_container_width=True)
