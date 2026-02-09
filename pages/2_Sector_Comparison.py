"""Sector Comparison Page — overlay multiple sector ratios."""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.db_client import load_all_data
from src.data_processor import _sector_display_name
from src.chart_builder import build_sector_comparison_chart

st.set_page_config(page_title="Sector Comparison", page_icon="📊", layout="wide")
st.title("Sector Comparison")

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

# Multi-select sectors
sector_names = {_sector_display_name(s): s for s in SECTORS}
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
    date_range = st.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if date_range and len(date_range) == 2:
        start, end = date_range
        filtered_data = {}
        for key in selected_keys:
            df = all_data.get(key)
            if df is not None:
                mask = (df["date"].dt.date >= start) & (df["date"].dt.date <= end)
                filtered_data[key] = df[mask]
    else:
        filtered_data = {k: all_data[k] for k in selected_keys if k in all_data}
else:
    filtered_data = {k: all_data[k] for k in selected_keys if k in all_data}

# Chart
fig = build_sector_comparison_chart(filtered_data, selected_sectors=selected_keys)
st.plotly_chart(fig, use_container_width=True)
