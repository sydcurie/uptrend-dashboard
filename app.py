"""US Market Uptrend Stock Ratio Dashboard — Main Page."""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.data_loader import cached_load_sector_data
from src.data_processor import (
    get_current_status,
    build_sector_summary,
    default_start_date,
    filter_by_date_range,
    prepare_timeseries_csv,
    localized_summary_styler,
)
from src.chart_builder import build_ratio_chart, build_sector_summary_chart
from src.i18n import t, val, render_language_selector

st.set_page_config(
    page_title=t("app.page_title"),
    page_icon="📈",
    layout="wide",
)

st.title(t("app.title"))


def load_data():
    """Load sector data from SQLite (cached cross-page)."""
    return cached_load_sector_data()


# Sidebar
with st.sidebar:
    render_language_selector()
    st.header(t("common.settings"))
    if st.button(t("common.refresh")):
        st.cache_data.clear()
        st.rerun()

    all_data = load_data()
    df_all = all_data.get("all")

    if df_all is not None and not df_all.empty:
        min_date = df_all["date"].min().date()
        max_date = df_all["date"].max().date()
        default_start = default_start_date(min_date, max_date)
        date_range = st.date_input(
            t("common.date_range"),
            value=(default_start, max_date),
            min_value=min_date,
            max_value=max_date,
        )
    else:
        date_range = None

    st.markdown("---")
    st.markdown(
        t("app.sidebar_desc"),
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
    st.warning(t("common.no_data_import"))
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
    st.metric(t("metric.current_ratio"), f"{status['ratio']:.1%}")
with col2:
    st.metric(t("metric.10ma"), f"{status['ratio_10ma']:.1%}" if status["ratio_10ma"] is not None else "N/A")
with col3:
    trend_icons = {"up": "🔼", "down": "🔽", "neutral": "➖"}
    st.metric(t("metric.trend"), f"{trend_icons.get(status['trend'], '➖')} {val(status['trend'].title())}")
with col4:
    if status["is_overbought"]:
        st.metric(t("metric.status"), f"⚠️ {val('Overbought')}")
    elif status["is_oversold"]:
        st.metric(t("metric.status"), f"⚠️ {val('Oversold')}")
    else:
        st.metric(t("metric.status"), val("Normal"))

st.markdown(t("metric.last_updated", date=status["date"]))

# Full market ratio chart
st.subheader(t("app.full_market_ratio"))
fig = build_ratio_chart(df_filtered, title=t("app.chart_title"))
st.plotly_chart(fig, use_container_width=True)

# Sector summary
st.subheader(t("app.sector_summary"))
summary = build_sector_summary(all_data)

fig_summary = build_sector_summary_chart(summary)
event = st.plotly_chart(fig_summary, use_container_width=True, on_select="rerun", key="sector_summary")

if event and event.selection and event.selection.points:
    point = event.selection.points[0]
    customdata = point.get("customdata")
    if customdata:
        st.session_state["selected_sector"] = customdata
        st.switch_page("pages/1_Sector_Detail.py")

table_event = st.dataframe(
    localized_summary_styler(
        summary.drop(columns=["_key"]),
        numeric_formats={"Ratio": "{:.1%}", "10MA": "{:.1%}", "Slope": "{:.4f}"},
    ),
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
st.subheader(t("common.data_download"))

col_dl1, col_dl2 = st.columns(2)
with col_dl1:
    ts_csv = prepare_timeseries_csv(df_filtered)
    st.download_button(
        t("dl.ratio_timeseries"),
        ts_csv.to_csv(index=False),
        "uptrend_ratio_timeseries.csv",
        "text/csv",
    )
with col_dl2:
    st.download_button(
        t("dl.sector_summary"),
        summary.drop(columns=["_key"]).to_csv(index=False),
        "sector_summary.csv",
        "text/csv",
    )
