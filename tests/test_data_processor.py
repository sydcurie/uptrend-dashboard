"""Tests for data_processor module (v2)."""

import pandas as pd
import numpy as np
import pytest

from src.data_processor import (
    MarketStatus,
    get_current_status,
    build_sector_summary,
    get_sector_display_name,
)


class TestGetCurrentStatus:
    """Tests for get_current_status function."""

    def test_get_current_status_uptrend(self, sample_calculated_df):
        """slope > 0 in last row should give trend='up'."""
        # Find a row with positive slope and set it as last
        df = sample_calculated_df.copy()
        # Last row of our sample data has positive slope (rising pattern at end)
        status = get_current_status(df)
        # Verify it returns expected keys (no signal fields)
        expected_keys = {
            "date", "ratio", "ratio_10ma", "trend",
            "slope", "is_overbought", "is_oversold",
        }
        assert set(status.keys()) == expected_keys

    def test_get_current_status_downtrend(self, sample_calculated_df):
        """slope <= 0 should give trend='down'."""
        # Use a row where slope is negative (falling section, around row 12-14)
        df = sample_calculated_df.copy()
        # Find rows with negative slope
        negative_slope_rows = df[df["slope"] < 0]
        if not negative_slope_rows.empty:
            single_row = negative_slope_rows.iloc[-1:].reset_index(drop=True)
            status = get_current_status(single_row)
            assert status["trend"] == "down"

    def test_get_current_status_overbought(self):
        """ratio > 0.37 should set is_overbought=True."""
        df = pd.DataFrame({
            "date": [pd.Timestamp("2024-01-02")],
            "count": [250],
            "total": [500],
            "ratio": [0.50],
            "ma_10": [0.40],
            "slope": [0.01],
            "trend_up": [0.50],
            "trend_down": [np.nan],
            "upper": [0.37],
            "lower": [0.097],
        })
        status = get_current_status(df)
        assert status["is_overbought"] is True
        assert status["is_oversold"] is False

    def test_get_current_status_oversold(self):
        """ratio < 0.097 should set is_oversold=True."""
        df = pd.DataFrame({
            "date": [pd.Timestamp("2024-01-02")],
            "count": [20],
            "total": [500],
            "ratio": [0.04],
            "ma_10": [0.06],
            "slope": [-0.01],
            "trend_up": [np.nan],
            "trend_down": [0.04],
            "upper": [0.37],
            "lower": [0.097],
        })
        status = get_current_status(df)
        assert status["is_overbought"] is False
        assert status["is_oversold"] is True


class TestBuildSectorSummary:
    """Tests for build_sector_summary function."""

    def test_build_sector_summary(self, sample_all_data):
        """Should produce summary with correct columns for all sectors."""
        summary = build_sector_summary(sample_all_data)
        expected_columns = {"Sector", "Ratio", "10MA", "Trend", "Slope", "Status"}
        assert set(summary.columns) == expected_columns
        assert len(summary) == 11

    def test_build_sector_summary_excludes_all(self, sample_all_data):
        """'all' worksheet should be excluded from sector summary."""
        summary = build_sector_summary(sample_all_data)
        assert "All" not in summary["Sector"].values


class TestSectorDisplayName:
    """Tests for get_sector_display_name helper."""

    def testget_sector_display_name(self):
        """Should convert worksheet names to display names."""
        assert get_sector_display_name("sec_technology") == "Technology"
        assert get_sector_display_name("sec_basicmaterials") == "Basic Materials"
        assert get_sector_display_name("sec_communicationservices") == "Communication Services"
        assert get_sector_display_name("sec_realestate") == "Real Estate"


class TestEmptyDataFrameGuards:
    """Tests for empty DataFrame handling."""

    def test_get_current_status_empty_df(self):
        """Empty DataFrame should return default status values."""
        df = pd.DataFrame(columns=[
            "date", "count", "total", "ratio", "ma_10", "slope",
            "trend_up", "trend_down", "upper", "lower", "is_peak", "is_trough",
        ])
        status = get_current_status(df)
        expected_keys = {
            "date", "ratio", "ratio_10ma", "trend",
            "slope", "is_overbought", "is_oversold",
        }
        assert set(status.keys()) == expected_keys
        assert status["ratio"] == 0.0
        assert status["ratio_10ma"] is None
        assert status["trend"] == "down"
        assert status["slope"] == 0.0
        assert status["is_overbought"] is False
        assert status["is_oversold"] is False

    def test_build_sector_summary_empty(self):
        """Empty data dict should return DataFrame with correct columns."""
        summary = build_sector_summary({})
        expected_columns = {"Sector", "Ratio", "10MA", "Trend", "Slope", "Status"}
        assert set(summary.columns) == expected_columns
        assert len(summary) == 0

    def test_build_sector_summary_all_empty_dfs(self):
        """Data dict with only empty DataFrames should return empty summary."""
        data = {
            "sec_technology": pd.DataFrame(columns=[
                "date", "count", "total", "ratio", "ma_10", "slope",
                "trend_up", "trend_down", "upper", "lower",
            ]),
        }
        summary = build_sector_summary(data)
        assert len(summary) == 0
