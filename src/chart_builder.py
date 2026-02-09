"""Plotly chart builders for uptrend dashboard (v2)."""

import logging
from typing import Dict, List, Optional

import pandas as pd
import numpy as np
import plotly.graph_objects as go

from src.constants import (
    SECTOR_DISPLAY_NAMES,
    UPPER_THRESHOLD,
    LOWER_THRESHOLD,
    CHART_HEIGHT_RATIO,
    CHART_HEIGHT_SUMMARY,
    CHART_HEIGHT_COMPARISON,
    CHART_Y_MAX_MIN,
    CHART_Y_MAX_MULTIPLIER,
)

logger = logging.getLogger(__name__)


# Color constants for trend segments
COLOR_TREND_UP = "#00cc96"
COLOR_TREND_DOWN = "#ef553b"
COLOR_TREND_NA = "#636efa"

# 11-color palette for sector comparison (maximally distinguishable)
SECTOR_PALETTE = [
    "#1f77b4",  # blue
    "#ff7f0e",  # orange
    "#2ca02c",  # green
    "#d62728",  # red
    "#9467bd",  # purple
    "#8c564b",  # brown
    "#e377c2",  # pink
    "#7f7f7f",  # gray
    "#bcbd22",  # olive
    "#17becf",  # cyan
    "#ff6600",  # dark orange
]

COLOR_MA = "rgba(148, 103, 189, 0.8)"
COLOR_PEAK = "#FF0000"
COLOR_TROUGH = "#00BFFF"
COLOR_UPPER = "#d62728"
COLOR_LOWER = "#2ca02c"

STATUS_COLORS = {
    "Overbought": "#d62728",
    "Oversold": "#2ca02c",
    "Normal": "#1f77b4",
}


def _get_trend_state(slope_val):
    """Determine trend state from slope value."""
    if pd.isna(slope_val):
        return "na"
    return "up" if slope_val > 0 else "down"


def _trend_color(state: str) -> str:
    """Map trend state to color."""
    if state == "up":
        return COLOR_TREND_UP
    elif state == "down":
        return COLOR_TREND_DOWN
    return COLOR_TREND_NA


def _trend_legend_name(state: str) -> str:
    """Map trend state to legend name."""
    if state == "up":
        return "Ratio (Up)"
    elif state == "down":
        return "Ratio (Down)"
    return "Ratio (N/A)"


def _add_ratio_segments(fig: go.Figure, df: pd.DataFrame) -> None:
    """Add color-coded ratio trend segments to the figure."""
    segments = []
    if len(df) > 0:
        current_state = _get_trend_state(df["slope"].iloc[0])
        seg_start = 0

        for i in range(1, len(df)):
            state = _get_trend_state(df["slope"].iloc[i])
            if state != current_state:
                segments.append((seg_start, i, current_state))
                seg_start = i
                current_state = state
        segments.append((seg_start, len(df), current_state))

    shown_legends = set()
    for start, end, state in segments:
        actual_start = max(0, start - 1) if start > 0 else start
        seg_df = df.iloc[actual_start:end]

        name = _trend_legend_name(state)
        show_legend = name not in shown_legends
        shown_legends.add(name)

        fig.add_trace(
            go.Scatter(
                x=seg_df["date"],
                y=seg_df["ratio"],
                mode="lines",
                name=name,
                line=dict(color=_trend_color(state), width=2),
                showlegend=show_legend,
            )
        )


def _add_moving_average(fig: go.Figure, df: pd.DataFrame) -> None:
    """Add 10MA line to the figure."""
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["ma_10"],
            mode="lines",
            name="10MA",
            line=dict(color=COLOR_MA, width=1.5),
            opacity=0.85,
        )
    )


def _add_peaks_and_troughs(fig: go.Figure, df: pd.DataFrame) -> None:
    """Add peak and trough markers to the figure."""
    if "is_peak" in df.columns:
        peak_df = df[df["is_peak"]]
        if len(peak_df) > 0:
            fig.add_trace(
                go.Scatter(
                    x=peak_df["date"],
                    y=peak_df["ma_10"],
                    mode="markers",
                    name="10MA Peak",
                    marker=dict(symbol="triangle-down", size=10, color=COLOR_PEAK),
                )
            )

    if "is_trough" in df.columns:
        trough_df = df[df["is_trough"]]
        if len(trough_df) > 0:
            fig.add_trace(
                go.Scatter(
                    x=trough_df["date"],
                    y=trough_df["ma_10"],
                    mode="markers",
                    name="10MA Trough",
                    marker=dict(symbol="triangle-up", size=10, color=COLOR_TROUGH),
                )
            )


def _add_threshold_lines(fig: go.Figure, df: pd.DataFrame) -> None:
    """Add upper and lower threshold lines to the figure."""
    upper_val = df["upper"].dropna().iloc[0] if not df["upper"].dropna().empty else UPPER_THRESHOLD
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=[upper_val] * len(df),
            mode="lines",
            name="Upper",
            line=dict(color=COLOR_UPPER, width=1, dash="dot"),
        )
    )

    lower_val = df["lower"].dropna().iloc[0] if not df["lower"].dropna().empty else LOWER_THRESHOLD
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=[lower_val] * len(df),
            mode="lines",
            name="Lower",
            line=dict(color=COLOR_LOWER, width=1, dash="dot"),
        )
    )


def _apply_chart_layout(fig: go.Figure, df: pd.DataFrame, title: str) -> None:
    """Apply standard layout settings to the ratio chart."""
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Ratio",
        template="plotly_white",
        height=CHART_HEIGHT_RATIO,
        yaxis=dict(range=[0, max(CHART_Y_MAX_MIN, df["ratio"].max() * CHART_Y_MAX_MULTIPLIER)]),
        hovermode="x unified",
    )


def build_ratio_chart(df: pd.DataFrame, title: str = "Uptrend Ratio") -> go.Figure:
    """Build a time series chart of ratio data with color-coded trend segments."""
    fig = go.Figure()
    _add_ratio_segments(fig, df)
    _add_moving_average(fig, df)
    _add_peaks_and_troughs(fig, df)
    _add_threshold_lines(fig, df)
    _apply_chart_layout(fig, df, title)
    return fig


def build_sector_summary_chart(summary_df: pd.DataFrame) -> go.Figure:
    """Build a horizontal bar chart of sector ratios."""
    fig = go.Figure()

    colors = [STATUS_COLORS.get(s, "#1f77b4") for s in summary_df["Status"]]

    fig.add_trace(
        go.Bar(
            y=summary_df["Sector"],
            x=summary_df["Ratio"],
            orientation="h",
            marker_color=colors,
            text=summary_df["Ratio"].apply(lambda x: f"{x:.1%}"),
            textposition="auto",
        )
    )

    fig.add_vline(x=UPPER_THRESHOLD, line_dash="dash", line_color=COLOR_UPPER, annotation_text="Upper")
    fig.add_vline(x=LOWER_THRESHOLD, line_dash="dash", line_color=COLOR_LOWER, annotation_text="Lower")

    fig.update_layout(
        title="Sector Ratio Summary",
        template="plotly_white",
        height=CHART_HEIGHT_SUMMARY,
        xaxis_title="Ratio",
        yaxis=dict(autorange="reversed"),
    )

    return fig


def build_sector_comparison_chart(
    all_data: Dict[str, pd.DataFrame],
    selected_sectors: Optional[List[str]] = None,
    use_ma: bool = True,
) -> go.Figure:
    """Build an overlay chart comparing sector ratios over time.

    Args:
        all_data: Dict of worksheet name -> calculated DataFrame.
        selected_sectors: List of sector keys to display.
        use_ma: If True, plot ma_10 (smoothed). If False, plot raw ratio.
    """
    fig = go.Figure()

    sectors = selected_sectors or [k for k in all_data if k != "all"]

    y_col = "ma_10" if use_ma else "ratio"

    # Collect latest values for sorting legend by descending value
    sector_latest = []
    for sector in sectors:
        if sector not in all_data:
            continue
        df = all_data[sector]
        if df.empty or y_col not in df.columns:
            continue
        valid = df[y_col].dropna()
        latest_val = valid.iloc[-1] if len(valid) > 0 else 0.0
        suffix = sector.replace("sec_", "", 1)
        display_name = SECTOR_DISPLAY_NAMES.get(suffix, sector)
        sector_latest.append((sector, display_name, latest_val))

    # Sort by latest value descending
    sector_latest.sort(key=lambda x: x[2], reverse=True)

    for idx, (sector, display_name, latest_val) in enumerate(sector_latest):
        df = all_data[sector]
        color = SECTOR_PALETTE[idx % len(SECTOR_PALETTE)]
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df[y_col],
                mode="lines",
                name=display_name,
                line=dict(color=color, width=2),
            )
        )

        # Annotate latest value at the right end of each line
        valid = df[y_col].dropna()
        if len(valid) > 0:
            last_date = df.loc[valid.index[-1], "date"]
            fig.add_annotation(
                x=last_date,
                y=latest_val,
                text=f"{display_name} {latest_val:.0%}",
                showarrow=False,
                xanchor="left",
                xshift=5,
                font=dict(size=10, color=color),
            )

    # Threshold lines
    fig.add_trace(
        go.Scatter(
            x=[],
            y=[],
            mode="lines",
            name="Upper",
            line=dict(color=COLOR_UPPER, width=1, dash="dash"),
            showlegend=True,
        )
    )
    fig.add_hline(
        y=UPPER_THRESHOLD,
        line_dash="dash",
        line_color=COLOR_UPPER,
        line_width=1,
    )

    fig.add_trace(
        go.Scatter(
            x=[],
            y=[],
            mode="lines",
            name="Lower",
            line=dict(color=COLOR_LOWER, width=1, dash="dash"),
            showlegend=True,
        )
    )
    fig.add_hline(
        y=LOWER_THRESHOLD,
        line_dash="dash",
        line_color=COLOR_LOWER,
        line_width=1,
    )

    title_suffix = " (10MA)" if use_ma else " (Raw Ratio)"
    fig.update_layout(
        title="Sector Comparison" + title_suffix,
        xaxis_title="Date",
        yaxis_title="Ratio",
        yaxis=dict(tickformat=".0%"),
        template="plotly_white",
        height=CHART_HEIGHT_COMPARISON,
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        hovermode="x unified",
    )

    return fig
