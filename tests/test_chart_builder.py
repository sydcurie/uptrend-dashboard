"""Tests for chart_builder module (v2)."""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import pytest

from src.chart_builder import (
    build_ratio_chart,
    build_sector_summary_chart,
    build_sector_comparison_chart,
)


class TestBuildRatioChart:
    """Tests for build_ratio_chart function."""

    def test_ratio_chart_returns_figure(self, sample_calculated_df):
        """Should return a go.Figure."""
        fig = build_ratio_chart(sample_calculated_df)
        assert isinstance(fig, go.Figure)

    def test_ratio_chart_title(self, sample_calculated_df):
        """Should set custom title."""
        fig = build_ratio_chart(sample_calculated_df, title="Test Title")
        assert fig.layout.title.text == "Test Title"

    def test_ratio_chart_traces(self, sample_calculated_df):
        """Should have at least 3 traces: ratio segment(s) + 10MA + Upper + Lower."""
        fig = build_ratio_chart(sample_calculated_df)
        trace_names = [t.name for t in fig.data]
        assert "10MA" in trace_names
        assert "Upper" in trace_names
        assert "Lower" in trace_names
        # Should have at least one Ratio segment
        ratio_traces = [t for t in fig.data if t.name and "Ratio" in t.name]
        assert len(ratio_traces) >= 1

    def test_ratio_chart_color_segments(self, sample_calculated_df):
        """Should have green (#00cc96) and red (#ef553b) segments."""
        fig = build_ratio_chart(sample_calculated_df)
        colors = set()
        for trace in fig.data:
            if trace.line and trace.line.color:
                colors.add(trace.line.color)
        # Should contain at least one of the trend colors
        trend_colors = {"#00cc96", "#ef553b", "#636efa"}
        assert len(colors & trend_colors) >= 1


class TestBuildSectorSummaryChart:
    """Tests for build_sector_summary_chart function."""

    def test_sector_summary_chart(self, sample_all_data):
        """Should produce a horizontal bar chart."""
        from src.data_processor import build_sector_summary

        summary = build_sector_summary(sample_all_data)
        fig = build_sector_summary_chart(summary)
        assert isinstance(fig, go.Figure)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        assert len(bar_traces) >= 1


class TestBuildSectorComparisonChart:
    """Tests for build_sector_comparison_chart function."""

    def test_sector_comparison_chart(self, sample_all_data):
        """Should produce an overlay chart for all sectors plus threshold legend traces."""
        fig = build_sector_comparison_chart(sample_all_data)
        assert isinstance(fig, go.Figure)
        # 11 sector traces + 2 threshold legend traces (Upper, Lower)
        assert len(fig.data) == 13

    def test_sector_comparison_selected(self, sample_all_data):
        """Should filter to selected sectors only (plus threshold traces)."""
        selected = ["sec_technology", "sec_healthcare"]
        fig = build_sector_comparison_chart(sample_all_data, selected_sectors=selected)
        # 2 sector traces + 2 threshold legend traces
        assert len(fig.data) == 4

    def test_sector_comparison_uses_ma_by_default(self, sample_all_data):
        """Default mode should use ma_10 column."""
        fig = build_sector_comparison_chart(sample_all_data, use_ma=True)
        # Title should indicate 10MA mode
        assert "10MA" in fig.layout.title.text

    def test_sector_comparison_raw_ratio_mode(self, sample_all_data):
        """Raw ratio mode should use ratio column."""
        fig = build_sector_comparison_chart(sample_all_data, use_ma=False)
        assert "Raw Ratio" in fig.layout.title.text

    def test_sector_comparison_has_threshold_traces(self, sample_all_data):
        """Should have Upper and Lower threshold legend entries."""
        fig = build_sector_comparison_chart(sample_all_data)
        trace_names = [t.name for t in fig.data]
        assert "Upper" in trace_names
        assert "Lower" in trace_names

    def test_sector_comparison_y_axis_percent(self, sample_all_data):
        """Y axis should use percent format."""
        fig = build_sector_comparison_chart(sample_all_data)
        assert fig.layout.yaxis.tickformat == ".0%"

    def test_sector_comparison_annotations(self, sample_all_data):
        """Should have annotations for latest values."""
        fig = build_sector_comparison_chart(sample_all_data)
        # Should have one annotation per sector
        assert len(fig.layout.annotations) == 11

    def test_sector_comparison_legend_sorted_by_latest_value(self, sample_all_data):
        """Legend (trace order) should be sorted by latest value descending."""
        fig = build_sector_comparison_chart(sample_all_data)
        # Get sector traces only (exclude Upper/Lower)
        sector_traces = [t for t in fig.data if t.name not in ("Upper", "Lower")]
        # Extract latest ma_10 values from the traces
        latest_values = []
        for t in sector_traces:
            y_vals = [v for v in t.y if v is not None and not pd.isna(v)]
            latest_values.append(y_vals[-1] if y_vals else 0)
        # Verify descending order
        assert latest_values == sorted(latest_values, reverse=True)

    def test_sector_comparison_custom_colors(self, sample_all_data):
        """Each sector should have a distinct color from the palette."""
        from src.chart_builder import SECTOR_PALETTE
        fig = build_sector_comparison_chart(sample_all_data)
        sector_traces = [t for t in fig.data if t.name not in ("Upper", "Lower")]
        colors = [t.line.color for t in sector_traces]
        # All colors should be from the palette
        for color in colors:
            assert color in SECTOR_PALETTE


class TestRatioChartPeakTroughMarkers:
    """Tests for peak/trough markers on ratio chart."""

    def test_ratio_chart_has_peak_trough_markers(self):
        """Should have '10MA Peak' and '10MA Trough' marker traces."""
        import numpy as np
        from src.indicator_calculator import calculate_indicators, IndicatorConfig

        # Build a sine-wave dataset large enough for peak/trough detection
        n = 200
        period = 40
        dates = pd.bdate_range("2024-01-01", periods=n, freq="B")
        ratios = 0.5 + 0.1 * np.sin(2 * np.pi * np.arange(n) / period)
        total = 500
        counts = (ratios * total).astype(int)
        df = pd.DataFrame({"date": dates, "count": counts, "total": [total] * n})
        calc_df = calculate_indicators(df, IndicatorConfig())

        fig = build_ratio_chart(calc_df)
        trace_names = [t.name for t in fig.data]
        assert "10MA Peak" in trace_names, f"Missing '10MA Peak' in {trace_names}"
        assert "10MA Trough" in trace_names, f"Missing '10MA Trough' in {trace_names}"
