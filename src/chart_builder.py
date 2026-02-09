"""Plotly chart builders for uptrend dashboard (v2)."""

from typing import Dict, List, Optional

import pandas as pd
import numpy as np
import plotly.graph_objects as go


# Color constants for trend segments
COLOR_TREND_UP = "#00cc96"
COLOR_TREND_DOWN = "#ef553b"
COLOR_TREND_NA = "#636efa"

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

_SECTOR_DISPLAY = {
    "sec_basicmaterials": "Basic Materials",
    "sec_communicationservices": "Communication Services",
    "sec_consumercyclical": "Consumer Cyclical",
    "sec_consumerdefensive": "Consumer Defensive",
    "sec_energy": "Energy",
    "sec_financial": "Financial",
    "sec_healthcare": "Healthcare",
    "sec_industrials": "Industrials",
    "sec_realestate": "Real Estate",
    "sec_technology": "Technology",
    "sec_utilities": "Utilities",
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


def build_ratio_chart(df: pd.DataFrame, title: str = "Uptrend Ratio") -> go.Figure:
    """Build a time series chart of ratio data with color-coded trend segments."""
    fig = go.Figure()

    # Build color-coded ratio segments
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
        # Include overlap point to prevent gaps
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

    # 10MA line
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

    # Peak markers
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

    # Trough markers
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

    # Upper threshold
    upper_val = df["upper"].dropna().iloc[0] if not df["upper"].dropna().empty else 0.37
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=[upper_val] * len(df),
            mode="lines",
            name="Upper",
            line=dict(color=COLOR_UPPER, width=1, dash="dot"),
        )
    )

    # Lower threshold
    lower_val = df["lower"].dropna().iloc[0] if not df["lower"].dropna().empty else 0.097
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=[lower_val] * len(df),
            mode="lines",
            name="Lower",
            line=dict(color=COLOR_LOWER, width=1, dash="dot"),
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Ratio",
        template="plotly_white",
        height=500,
        yaxis=dict(range=[0, max(0.6, df["ratio"].max() * 1.1)]),
        hovermode="x unified",
    )

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

    fig.add_vline(x=0.37, line_dash="dash", line_color=COLOR_UPPER, annotation_text="Upper")
    fig.add_vline(x=0.097, line_dash="dash", line_color=COLOR_LOWER, annotation_text="Lower")

    fig.update_layout(
        title="Sector Ratio Summary",
        template="plotly_white",
        height=450,
        xaxis_title="Ratio",
        yaxis=dict(autorange="reversed"),
    )

    return fig


def build_sector_comparison_chart(
    all_data: Dict[str, pd.DataFrame],
    selected_sectors: Optional[List[str]] = None,
) -> go.Figure:
    """Build an overlay chart comparing sector ratios over time."""
    fig = go.Figure()

    sectors = selected_sectors or [k for k in all_data if k != "all"]

    for sector in sectors:
        if sector not in all_data:
            continue
        df = all_data[sector]
        display_name = _SECTOR_DISPLAY.get(sector, sector)
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["ratio"],
                mode="lines",
                name=display_name,
            )
        )

    fig.update_layout(
        title="Sector Comparison",
        xaxis_title="Date",
        yaxis_title="Ratio",
        template="plotly_white",
        height=600,
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        hovermode="x unified",
    )

    return fig
