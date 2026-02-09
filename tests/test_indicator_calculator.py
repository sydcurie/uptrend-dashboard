"""Tests for indicator_calculator module."""

import pandas as pd
import numpy as np
import pytest

from src.indicator_calculator import (
    IndicatorConfig,
    calculate_indicators,
)


class TestRatioCalculation:
    """Tests for ratio calculation via public API."""

    def test_ratio_values(self):
        """count/total should produce correct ratio via calculate_indicators."""
        df = pd.DataFrame({
            "date": pd.bdate_range("2024-01-01", periods=3, freq="B"),
            "count": [150, 200, 250],
            "total": [500, 500, 500],
        })
        result = calculate_indicators(df)
        assert list(result["ratio"]) == [0.3, 0.4, 0.5]

    def test_ratio_zero_total(self):
        """total=0 should produce ratio=0.0, not raise ZeroDivisionError."""
        df = pd.DataFrame({
            "date": pd.bdate_range("2024-01-01", periods=2, freq="B"),
            "count": [100, 0],
            "total": [0, 0],
        })
        result = calculate_indicators(df)
        assert list(result["ratio"]) == [0.0, 0.0]


class TestMovingAverage:
    """Tests for moving average via public API."""

    def test_ma_10_leading_nans(self, sample_raw_df):
        """10-day MA should have NaN for first 9 rows, valid from row 10."""
        result = calculate_indicators(sample_raw_df)
        assert all(pd.isna(result["ma_10"].iloc[:9]))
        assert pd.notna(result["ma_10"].iloc[9])

    def test_ma_10_value(self, sample_raw_df):
        """10th MA value should be mean of first 10 ratios."""
        result = calculate_indicators(sample_raw_df)
        expected = result["ratio"].iloc[:10].mean()
        assert abs(result["ma_10"].iloc[9] - expected) < 1e-10

    def test_ma_insufficient_data(self):
        """With fewer than 10 rows, all MA values should be NaN."""
        df = pd.DataFrame({
            "date": pd.bdate_range("2024-01-01", periods=3, freq="B"),
            "count": [150, 200, 250],
            "total": [500, 500, 500],
        })
        result = calculate_indicators(df)
        assert all(pd.isna(result["ma_10"]))


class TestSlope:
    """Tests for slope calculation via public API."""

    def test_slope_is_ma_diff(self, sample_raw_df):
        """Slope should be the 1-day diff of MA."""
        result = calculate_indicators(sample_raw_df)
        # First valid MA slope should be NaN (diff of first MA value)
        assert pd.isna(result["slope"].iloc[9])
        # 11th value should be diff of 10th and 11th MA
        if pd.notna(result["ma_10"].iloc[10]) and pd.notna(result["ma_10"].iloc[9]):
            expected = result["ma_10"].iloc[10] - result["ma_10"].iloc[9]
            assert abs(result["slope"].iloc[10] - expected) < 1e-10


class TestTrend:
    """Tests for trend calculation via public API."""

    def test_trend_up_matches_positive_slope(self, sample_raw_df):
        """When slope > 0, trend_up should have the ratio value."""
        result = calculate_indicators(sample_raw_df)
        for i in range(len(result)):
            if pd.notna(result["slope"].iloc[i]) and result["slope"].iloc[i] > 0:
                assert result["trend_up"].iloc[i] == result["ratio"].iloc[i]

    def test_trend_down_matches_nonpositive_slope(self, sample_raw_df):
        """When slope <= 0, trend_down should have the ratio value."""
        result = calculate_indicators(sample_raw_df)
        for i in range(len(result)):
            if pd.notna(result["slope"].iloc[i]) and result["slope"].iloc[i] <= 0:
                assert result["trend_down"].iloc[i] == result["ratio"].iloc[i]


class TestCalculateIndicators:
    """Tests for the full calculate_indicators function."""

    def test_calculate_indicators_full(self, sample_raw_df):
        """Full calculation should produce all expected columns."""
        result = calculate_indicators(sample_raw_df)
        expected_columns = {
            "date", "count", "total",
            "ratio", "ma_10", "slope",
            "trend_up", "trend_down",
            "upper", "lower",
            "is_peak", "is_trough",
        }
        assert set(result.columns) == expected_columns
        assert len(result) == 20
        # upper/lower should be constants
        assert all(result["upper"] == 0.37)
        assert all(result["lower"] == 0.097)

    def test_custom_config(self, sample_raw_df):
        """IndicatorConfig should allow custom parameters."""
        config = IndicatorConfig(ma_period=5, upper_threshold=0.4, lower_threshold=0.1)
        result = calculate_indicators(sample_raw_df, config=config)
        # With period=5, MA should be valid from row 5 onwards
        assert pd.isna(result["ma_10"].iloc[3])
        assert pd.notna(result["ma_10"].iloc[4])
        # Thresholds should use custom values
        assert all(result["upper"] == 0.4)
        assert all(result["lower"] == 0.1)


def _make_sine_raw_df(n: int = 200, period: int = 40, amplitude: float = 0.1,
                      baseline: float = 0.5) -> pd.DataFrame:
    """Create a sine-wave raw DataFrame for deterministic peak/trough testing."""
    dates = pd.bdate_range("2024-01-01", periods=n, freq="B")
    ratios = baseline + amplitude * np.sin(2 * np.pi * np.arange(n) / period)
    total = 500
    counts = (ratios * total).astype(int)
    return pd.DataFrame({"date": dates, "count": counts, "total": [total] * n})


class TestPeaksAndTroughs:
    """Tests for peak/trough detection via public API."""

    def test_peaks_detected_in_sine_wave(self):
        """Peaks should be detected at the tops of a sine wave."""
        df = _make_sine_raw_df(n=200, period=40, amplitude=0.1)
        result = calculate_indicators(df)
        assert result["is_peak"].sum() > 0
        # All peak indices should be within bounds
        peak_indices = result.index[result["is_peak"]]
        assert all(0 <= idx < len(result) for idx in peak_indices)

    def test_troughs_detected_in_sine_wave(self):
        """Troughs should be detected at the bottoms of a sine wave."""
        df = _make_sine_raw_df(n=200, period=40, amplitude=0.1)
        result = calculate_indicators(df)
        assert result["is_trough"].sum() > 0
        trough_indices = result.index[result["is_trough"]]
        assert all(0 <= idx < len(result) for idx in trough_indices)

    def test_peaks_troughs_boolean_columns(self):
        """calculate_indicators adds is_peak / is_trough boolean columns."""
        df = _make_sine_raw_df(n=200, period=40, amplitude=0.1)
        result = calculate_indicators(df)
        assert result["is_peak"].dtype == bool
        assert result["is_trough"].dtype == bool

    def test_strict_config_fewer_detections(self):
        """Stricter distance/prominence should detect fewer peaks/troughs."""
        df = _make_sine_raw_df(n=300, period=40, amplitude=0.1)
        config_default = IndicatorConfig()
        config_strict = IndicatorConfig(peak_distance=60, peak_prominence=0.05)

        result_default = calculate_indicators(df, config_default)
        result_strict = calculate_indicators(df, config_strict)

        assert result_strict["is_peak"].sum() <= result_default["is_peak"].sum()
        assert result_strict["is_trough"].sum() <= result_default["is_trough"].sum()


class TestEmptyDataFrame:
    """Tests for empty DataFrame handling."""

    def test_calculate_indicators_empty_df(self):
        """Empty DataFrame should return empty DataFrame with all expected columns."""
        df = pd.DataFrame(columns=["date", "count", "total"])
        result = calculate_indicators(df)
        expected_columns = {
            "date", "count", "total",
            "ratio", "ma_10", "slope",
            "trend_up", "trend_down",
            "upper", "lower",
            "is_peak", "is_trough",
        }
        assert set(result.columns) == expected_columns
        assert len(result) == 0


class TestNaNHandling:
    """Tests for NaN value handling in calculations."""

    def test_ratio_with_nan_count(self):
        """NaN count values should be treated as 0."""
        df = pd.DataFrame({
            "date": pd.bdate_range("2024-01-01", periods=3, freq="B"),
            "count": [100, np.nan, 200],
            "total": [500, 500, 500],
        })
        result = calculate_indicators(df)
        assert result["ratio"].iloc[0] == 0.2
        assert result["ratio"].iloc[1] == 0.0  # NaN count -> 0
        assert result["ratio"].iloc[2] == 0.4

    def test_ratio_with_nan_total(self):
        """NaN total values should be treated as 0 total (ratio = 0)."""
        df = pd.DataFrame({
            "date": pd.bdate_range("2024-01-01", periods=2, freq="B"),
            "count": [100, 200],
            "total": [500, np.nan],
        })
        result = calculate_indicators(df)
        assert result["ratio"].iloc[0] == 0.2
        assert result["ratio"].iloc[1] == 0.0  # NaN total -> 0
