"""Industry Heatmap Page — treemap overview of all industries."""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.data_loader import cached_load_all_data
from src.data_processor import (
    build_industry_summary_with_sector,
    localized_summary_styler,
)
from src.chart_builder import build_industry_heatmap
from src.i18n import t, val, render_language_selector

st.set_page_config(page_title=t("p5.page_title"), page_icon="🗺️", layout="wide")
st.title(t("p5.title"))

with st.sidebar:
    render_language_selector()
    st.markdown("---")
    st.markdown(t("p5.sidebar_desc"))

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

# Controls
col_color, col_size = st.columns(2)
with col_color:
    color_mode = st.radio(
        t("p5.color_mode"),
        [t("p5.opt_ratio"), t("p5.opt_trend_status")],
        horizontal=True,
    )
with col_size:
    size_mode = st.radio(
        t("p5.size_mode"),
        [t("p5.opt_uniform"), t("p5.opt_stock_count")],
        horizontal=True,
    )

color_mode_key = "ratio" if color_mode == t("p5.opt_ratio") else "status"
size_mode_key = "uniform" if size_mode == t("p5.opt_uniform") else "count"

# Build summary data
summary = build_industry_summary_with_sector(all_data)

if summary.empty:
    st.warning(t("p5.no_industry_data"))
    st.stop()

# KPI metrics
total_count = len(summary)
status_counts = summary["Status"].value_counts()
trend_counts = summary["Trend"].value_counts()

kpi_cols = st.columns(5)
with kpi_cols[0]:
    st.metric(val("Oversold"), f"{status_counts.get('Oversold', 0) / total_count:.1%}")
with kpi_cols[1]:
    st.metric(val("Normal"), f"{status_counts.get('Normal', 0) / total_count:.1%}")
with kpi_cols[2]:
    st.metric(val("Overbought"), f"{status_counts.get('Overbought', 0) / total_count:.1%}")
with kpi_cols[3]:
    st.metric(t("p5.kpi_trend_up"), f"{trend_counts.get('Up', 0) / total_count:.1%}")
with kpi_cols[4]:
    st.metric(t("p5.kpi_trend_down"), f"{trend_counts.get('Down', 0) / total_count:.1%}")

# Treemap (display only)
fig = build_industry_heatmap(summary, color_mode=color_mode_key, size_mode=size_mode_key)
st.plotly_chart(fig, use_container_width=True)

# Industry Summary Table
st.markdown("---")
st.subheader(t("p5.industry_summary"))

display_df = summary.sort_values(["Sector", "Industry"]).reset_index(drop=True)

table_event = st.dataframe(
    localized_summary_styler(
        display_df.drop(columns=["_key", "Total"]),
        numeric_formats={"Ratio": "{:.1%}", "10MA": "{:.1%}", "Slope": "{:.4f}"},
    ),
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    key="heatmap_industry_table",
)

if table_event and table_event.selection and table_event.selection.rows:
    selected_row = table_event.selection.rows[0]
    selected_key = display_df.iloc[selected_row]["_key"]
    st.session_state["selected_industry"] = selected_key
    st.switch_page("pages/3_Industry_Detail.py")
