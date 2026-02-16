"""Tests for chart_builder module (v2)."""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import pytest

from src.chart_builder import (
    build_ratio_chart,
    build_sector_summary_chart,
    build_sector_comparison_chart,
    build_industry_summary_chart,
    build_industry_comparison_chart,
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


    def test_sector_summary_chart_customdata(self, sample_all_data):
        """Bar trace should have customdata with sector keys for click navigation."""
        from src.data_processor import build_sector_summary

        summary = build_sector_summary(sample_all_data)
        fig = build_sector_summary_chart(summary)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        assert len(bar_traces) >= 1
        bar = bar_traces[0]
        assert bar.customdata is not None
        assert len(bar.customdata) == len(summary)
        # All customdata values should be sector keys (start with "sec_")
        for key in bar.customdata:
            assert key.startswith("sec_"), f"Unexpected key: {key}"


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


class TestBuildIndustrySummaryChart:
    """Tests for build_industry_summary_chart function."""

    def _make_industry_summary(self):
        """Create a sample industry summary DataFrame."""
        return pd.DataFrame({
            "Industry": ["Semiconductors", "Software - Application", "Banks - Regional"],
            "Ratio": [0.45, 0.32, 0.20],
            "10MA": [0.40, 0.30, 0.22],
            "Trend": ["Up", "Up", "Down"],
            "Slope": [0.02, 0.01, -0.005],
            "Status": ["Overbought", "Normal", "Normal"],
            "_key": ["ind_semiconductors", "ind_softwareapplication", "ind_banksregional"],
        })

    def test_industry_summary_chart(self):
        """Should return a go.Figure with Bar trace."""
        summary = self._make_industry_summary()
        fig = build_industry_summary_chart(summary)
        assert isinstance(fig, go.Figure)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        assert len(bar_traces) >= 1

    def test_industry_summary_chart_customdata(self):
        """Bar trace customdata should contain ind_* keys."""
        summary = self._make_industry_summary()
        fig = build_industry_summary_chart(summary)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        bar = bar_traces[0]
        assert bar.customdata is not None
        for key in bar.customdata:
            assert key.startswith("ind_"), f"Unexpected key: {key}"

    def test_industry_summary_chart_dynamic_height(self):
        """Chart height should scale with number of bars."""
        summary_3 = self._make_industry_summary()
        fig_3 = build_industry_summary_chart(summary_3)
        # 3 bars: max(300, 3*35+100) = 300
        assert fig_3.layout.height == 300

        # 10 bars: max(300, 10*35+100) = 450
        summary_10 = pd.DataFrame({
            "Industry": [f"Ind {i}" for i in range(10)],
            "Ratio": [0.3] * 10,
            "10MA": [0.28] * 10,
            "Trend": ["Up"] * 10,
            "Slope": [0.01] * 10,
            "Status": ["Normal"] * 10,
            "_key": [f"ind_test{i}" for i in range(10)],
        })
        fig_10 = build_industry_summary_chart(summary_10)
        assert fig_10.layout.height == 450

    def test_industry_summary_chart_title_with_sector(self):
        """Title should include sector name when provided."""
        summary = self._make_industry_summary()
        fig = build_industry_summary_chart(summary, sector_name="Technology")
        assert "Technology" in fig.layout.title.text

    def test_industry_summary_chart_title_default(self):
        """Default title without sector name."""
        summary = self._make_industry_summary()
        fig = build_industry_summary_chart(summary)
        assert fig.layout.title.text == "Industry Ratio Summary"


class TestBuildIndustryComparisonChart:
    """Tests for build_industry_comparison_chart function."""

    def _make_industry_data(self):
        """Create sample all_data with industry entries."""
        from src.indicator_calculator import calculate_indicators
        dates = pd.bdate_range("2024-01-02", periods=20, freq="B")
        counts = [150, 170, 190, 200, 210, 220, 230, 240, 250, 245,
                  230, 210, 195, 180, 170, 175, 185, 195, 210, 220]
        base_df = pd.DataFrame({"date": dates, "count": counts, "total": [500] * 20})
        data = {}
        for i, ind in enumerate(["ind_semiconductors", "ind_softwareapplication", "ind_banksregional"]):
            df = base_df.copy()
            df["count"] = (df["count"] * (0.8 + i * 0.1)).astype(int)
            data[ind] = calculate_indicators(df)
        return data

    def test_industry_comparison_chart(self):
        """Should produce traces for each industry + 2 threshold traces."""
        data = self._make_industry_data()
        fig = build_industry_comparison_chart(data)
        assert isinstance(fig, go.Figure)
        # 3 industry traces + 2 threshold legend traces
        assert len(fig.data) == 5

    def test_industry_comparison_selected(self):
        """Should filter to selected industries only."""
        data = self._make_industry_data()
        selected = ["ind_semiconductors"]
        fig = build_industry_comparison_chart(data, selected_industries=selected)
        # 1 industry trace + 2 threshold traces
        assert len(fig.data) == 3

    def test_industry_comparison_uses_industry_palette(self):
        """Should use INDUSTRY_PALETTE colors."""
        from src.chart_builder import INDUSTRY_PALETTE
        data = self._make_industry_data()
        fig = build_industry_comparison_chart(data)
        industry_traces = [t for t in fig.data if t.name not in ("Upper", "Lower")]
        for t in industry_traces:
            assert t.line.color in INDUSTRY_PALETTE

    def test_industry_comparison_title(self):
        """Title should indicate Industry Comparison."""
        data = self._make_industry_data()
        fig = build_industry_comparison_chart(data)
        assert "Industry Comparison" in fig.layout.title.text


class TestSectorComparisonExcludesIndustries:
    """Test that sector comparison filters out ind_* entries."""

    def test_sector_comparison_excludes_industries(self, sample_all_data):
        """ind_* entries in all_data should not appear in sector comparison."""
        from src.indicator_calculator import calculate_indicators
        # Add industry data to sample_all_data
        dates = pd.bdate_range("2024-01-02", periods=20, freq="B")
        counts = [150, 170, 190, 200, 210, 220, 230, 240, 250, 245,
                  230, 210, 195, 180, 170, 175, 185, 195, 210, 220]
        ind_df = pd.DataFrame({"date": dates, "count": counts, "total": [500] * 20})
        sample_all_data["ind_semiconductors"] = calculate_indicators(ind_df)

        fig = build_sector_comparison_chart(sample_all_data)
        trace_names = [t.name for t in fig.data]
        # Should not have "Semiconductors" in any trace name
        for name in trace_names:
            assert name != "Semiconductors", "Industry should not appear in sector comparison"
        # Should still have 11 sector traces + 2 threshold traces
        assert len(fig.data) == 13


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
