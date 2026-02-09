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
        """Should produce an overlay chart for all sectors."""
        fig = build_sector_comparison_chart(sample_all_data)
        assert isinstance(fig, go.Figure)
        # Should have one trace per sector (excluding "all")
        assert len(fig.data) == 11

    def test_sector_comparison_selected(self, sample_all_data):
        """Should filter to selected sectors only."""
        selected = ["sec_technology", "sec_healthcare"]
        fig = build_sector_comparison_chart(sample_all_data, selected_sectors=selected)
        assert len(fig.data) == 2


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
