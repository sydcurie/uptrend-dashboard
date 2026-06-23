"""Sector Dispersion Monitor — regime detection, signals, and sector ranking."""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.data_loader import cached_load_sector_data
from src.indicator_calculator import (
    calculate_forward_returns,
    calculate_sector_dispersion,
    calculate_sector_edge,
    detect_dispersion_signals,
)
from src.chart_builder import build_dispersion_chart, build_regime_timeline_chart
from src.data_processor import (
    build_sector_ranking_table,
    default_start_date,
    filter_by_date_range,
    localized_summary_styler,
)
from src.i18n import t, val, actions as regime_actions, render_language_selector

st.set_page_config(page_title=t("p6.page_title"), page_icon="📡", layout="wide")
st.title(t("p6.title"))

with st.sidebar:
    render_language_selector()
    st.markdown("---")
    st.markdown(t("p6.sidebar_desc"))
    st.markdown("---")
    st.markdown(
        'Made with <img src="https://streamlit.io/images/brand/streamlit-mark-color.png" '
        'alt="Streamlit" height="16"> by '
        '<a href="https://github.com/tradermonty">@tradermonty</a>',
        unsafe_allow_html=True,
    )
    st.markdown(
        "[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-yellow"
        "?style=for-the-badge&logo=buy-me-a-coffee)](https://buymeacoffee.com/tradermonty)"
    )

# === Full-history calculation (before any date filter) ===
sector_data = cached_load_sector_data()
dispersion_df = calculate_sector_dispersion(sector_data)

# === Data sufficiency guard ===
valid_df = (
    dispersion_df.dropna(subset=["regime", "level_regime"])
    if not dispersion_df.empty
    else dispersion_df
)
if valid_df.empty:
    st.warning(t("p6.insufficient"))
    st.stop()

# === Valid data — normal processing ===
signals = detect_dispersion_signals(dispersion_df)
market_df = sector_data.get("all")
forward_stats = (
    calculate_forward_returns(dispersion_df, market_df)
    if market_df is not None and not market_df.empty
    else None
)
sector_edge = calculate_sector_edge(dispersion_df, sector_data)
latest_valid = valid_df.iloc[-1]
current_regime = latest_valid["regime"]
current_level = latest_valid["level_regime"]

# --- 1. Signal Banner ---
active_signals = [s for s in signals if s.active]
if not active_signals:
    st.success(t("p6.signal_normal", disp=latest_valid["dispersion"], mean=latest_valid["mean_ratio"]))
else:
    for sig in active_signals:
        if sig.signal_id == "CAPITULATION":
            st.error(t("p6.signal_capitulation", disp=sig.dispersion, mean=sig.mean_ratio))
        elif sig.signal_id == "DIVERGENCE_WARNING":
            st.warning(t("p6.signal_divergence", disp=sig.dispersion))
        elif sig.signal_id == "BREAKOUT_VELOCITY":
            st.info(t("p6.signal_breakout", disp=sig.dispersion))

# --- Status metrics ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(t("metric.dispersion_sigma"), f"{latest_valid['dispersion']:.4f}")
with col2:
    st.metric(t("metric.mean_ratio"), f"{latest_valid['mean_ratio']:.1%}")
with col3:
    regime_emoji = {"converged": "🟢", "normal": "🔵", "diverged": "🔴"}
    st.metric(t("metric.regime"), f"{regime_emoji.get(current_regime, '')} {val(current_regime)}")
with col4:
    st.metric(t("metric.level"), val(current_level))

# === Date filter (chart/table display only) ===
with st.sidebar:
    if not dispersion_df.empty and "date" in dispersion_df.columns:
        min_date = dispersion_df["date"].min()
        max_date = dispersion_df["date"].max()
        if hasattr(min_date, "date"):
            min_date = min_date.date()
            max_date = max_date.date()
        default_start = default_start_date(min_date, max_date)
        date_range = st.date_input(
            t("common.date_range"),
            value=(default_start, max_date),
            min_value=min_date,
            max_value=max_date,
        )
    else:
        date_range = None

if date_range and len(date_range) == 2:
    start, end = date_range
    filtered_df = filter_by_date_range(
        dispersion_df.assign(date=lambda d: d["date"] if hasattr(d["date"].iloc[0], "date") else d["date"]),
        start, end,
    ) if hasattr(dispersion_df["date"].iloc[0], "date") else dispersion_df
else:
    filtered_df = dispersion_df

# --- 2. Dispersion Chart ---
st.subheader(t("p6.dispersion_chart"))
fig = build_dispersion_chart(filtered_df)
st.plotly_chart(fig, use_container_width=True)

# --- 3. Regime Timeline ---
st.subheader(t("p6.regime_timeline"))
fig_timeline = build_regime_timeline_chart(filtered_df)
st.plotly_chart(fig_timeline, use_container_width=True)

# --- 4. Sector Ranking Table ---
st.subheader(t("p6.sector_ranking"))
if current_regime == "converged" and current_level == "low":
    st.caption(t("p6.cap_caption"))
elif current_regime == "diverged":
    st.caption(t("p6.div_caption"))
else:
    st.caption(t("p6.normal_caption"))

ranking = build_sector_ranking_table(sector_data, current_regime, current_level, sector_edge)
if not ranking.empty:
    st.dataframe(
        localized_summary_styler(
            ranking,
            numeric_formats={
                "Current Ratio": "{:.1%}",
                "10MA": "{:.1%}",
                "Historical Edge": lambda x: f"{x:+.4f}" if x is not None and x == x else "N/A",
            },
            localize_values=("Trend",),
            style_rows=False,
        ),
        use_container_width=True,
        hide_index=True,
    )

# --- 5. Historical Stats (Expander) ---
with st.expander(t("p6.hist_stats")):
    if forward_stats is not None and not forward_stats.empty:
        st.caption(t("p6.hist_samples_caption"))
        st.dataframe(
            localized_summary_styler(
                forward_stats,
                numeric_formats={
                    "mean_return": "{:+.4f}",
                    "win_rate": "{:.1%}",
                    "count": "{:.0f}",
                },
                localize_values=("regime", "level_regime"),
                style_rows=False,
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(t("p6.forward_stats_pending"))

# --- 6. Regime Action Guide ---
st.subheader(t("p6.action_guide"))
st.caption(t("p6.action_disclaimer"))

# Maps (regime, level_regime) -> i18n guide key + Streamlit display style.
# Labels and action bullets are resolved from i18n at render time.
_REGIME_GUIDE = {
    ("converged", "low"): {"key": "converged_low", "type": "success"},
    ("converged", "mid"): {"key": "converged_mid", "type": "success"},
    ("converged", "high"): {"key": "converged_high", "type": "success"},
    ("normal", None): {"key": "normal", "type": "info"},
    ("diverged", None): {"key": "diverged", "type": "error"},
}

# Current regime highlight
current_key = (current_regime, current_level)
# Fall back to (regime, None) for normal/diverged which don't vary by level
guide = _REGIME_GUIDE.get(current_key) or _REGIME_GUIDE.get((current_regime, None))

if guide:
    guide_label = t(f"guide.{guide['key']}")
    action_text = "\n".join(f"- {a}" for a in regime_actions(guide["key"]))
    display_fn = {"error": st.error, "warning": st.warning, "info": st.info, "success": st.success}
    display_fn.get(guide["type"], st.info)(
        f"{t('p6.current_prefix', label=guide_label)}\n\n{action_text}"
    )

# Full regime reference table
with st.expander(t("p6.all_regime_actions")):
    for key, g in _REGIME_GUIDE.items():
        is_current = (key == current_key) or (
            key == (current_regime, None) and current_key not in _REGIME_GUIDE
        )
        badge = f" `{t('p6.current_badge')}`" if is_current else ""
        ref_label = t("guide." + g["key"])
        st.markdown(f"**{ref_label}**{badge}")
        for a in regime_actions(g["key"]):
            st.markdown(f"- {a}")
