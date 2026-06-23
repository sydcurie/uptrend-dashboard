"""Sector Comparison Page — overlay multiple sector ratios."""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.constants import SECTORS
from src.data_loader import cached_load_sector_data
from src.data_processor import get_sector_display_name, default_start_date, filter_by_date_range
from src.chart_builder import build_sector_comparison_chart
from src.indicator_calculator import calculate_sector_dispersion
from src.i18n import t, render_language_selector

st.set_page_config(page_title=t("p2.page_title"), page_icon="📊", layout="wide")
st.title(t("p2.title"))

with st.sidebar:
    render_language_selector()
    st.markdown("---")
    st.markdown(t("p2.sidebar_desc"))

    st.markdown("---")
    st.page_link("pages/6_Dispersion_Monitor.py", label=t("p2.dispersion_link"))
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

# Dispersion gauge in sidebar
with st.sidebar:
    dispersion_df = calculate_sector_dispersion(all_data)
    valid_disp = (
        dispersion_df.dropna(subset=["regime", "level_regime"])
        if not dispersion_df.empty
        else dispersion_df
    )
    if not valid_disp.empty:
        latest = valid_disp.iloc[-1]
        regime_icons = {"converged": "🟢", "normal": "🔵", "diverged": "🔴"}
        st.markdown(
            t(
                "p2.dispersion_label",
                sigma=latest["dispersion"],
                icon=regime_icons.get(latest["regime"], ""),
            )
        )
    else:
        st.markdown(t("p2.dispersion_na"))

# Multi-select sectors
sector_names = {get_sector_display_name(s): s for s in SECTORS}
selected_display = st.multiselect(
    t("p2.select_sectors"),
    options=list(sector_names.keys()),
    default=list(sector_names.keys()),
)

selected_keys = [sector_names[name] for name in selected_display]

if not selected_keys:
    st.warning(t("p2.select_one_sector"))
    st.stop()

# Date filter using first available sector
first_df = all_data.get(selected_keys[0])
if first_df is not None and not first_df.empty:
    min_date = first_df["date"].min().date()
    max_date = first_df["date"].max().date()
    default_start = default_start_date(min_date, max_date)
    date_range = st.date_input(
        t("common.date_range"),
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
    t("common.display_mode"),
    options=[t("opt.smoothed"), t("opt.raw")],
    horizontal=True,
)
use_ma = display_mode == t("opt.smoothed")

# Chart
fig = build_sector_comparison_chart(filtered_data, selected_sectors=selected_keys, use_ma=use_ma)
st.plotly_chart(fig, use_container_width=True)
