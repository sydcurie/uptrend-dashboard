"""Tests for indicator_calculator module."""

import pandas as pd
import numpy as np
import pytest

from src.indicator_calculator import (
    IndicatorConfig,
    calculate_indicators,
    _calc_ratio,
    _calc_ma,
    _calc_slope,
    _calc_trend,
    _detect_peaks_troughs,
)


class TestCalcRatio:
    """Tests for ratio calculation."""

    def test_calc_ratio(self):
        """count/total should produce correct ratio."""
        df = pd.DataFrame({"count": [150, 200, 250], "total": [500, 500, 500]})
        result = _calc_ratio(df)
        assert list(result) == [0.3, 0.4, 0.5]

    def test_calc_ratio_zero_total(self):
        """total=0 should produce 0.0, not raise ZeroDivisionError."""
        df = pd.DataFrame({"count": [100, 0], "total": [0, 0]})
        result = _calc_ratio(df)
        assert list(result) == [0.0, 0.0]


class TestCalcMA:
    """Tests for moving average calculation."""

    def test_calc_ma_10(self, sample_raw_df):
        """10-day MA should have valid values from row 10 onwards."""
        ratio = _calc_ratio(sample_raw_df)
        ma = _calc_ma(ratio, period=10)
        # First 9 values should be NaN
        assert all(pd.isna(ma.iloc[:9]))
        # 10th value onwards should be valid
        assert pd.notna(ma.iloc[9])
        # Verify 10th value is mean of first 10 ratios
        expected = ratio.iloc[:10].mean()
        assert abs(ma.iloc[9] - expected) < 1e-10

    def test_calc_ma_insufficient_data(self):
        """With fewer than period rows, all values should be NaN."""
        ratio = pd.Series([0.3, 0.4, 0.5])
        ma = _calc_ma(ratio, period=10)
        assert all(pd.isna(ma))


class TestCalcSlope:
    """Tests for slope calculation."""

    def test_calc_slope(self, sample_raw_df):
        """Slope should be diff of MA."""
        ratio = _calc_ratio(sample_raw_df)
        ma = _calc_ma(ratio, period=10)
        slope = _calc_slope(ma)
        # First value of slope (where MA starts) should be NaN
        assert pd.isna(slope.iloc[9])
        # 11th value should be diff of 10th and 11th MA
        if pd.notna(ma.iloc[10]) and pd.notna(ma.iloc[9]):
            expected = ma.iloc[10] - ma.iloc[9]
            assert abs(slope.iloc[10] - expected) < 1e-10


class TestCalcTrend:
    """Tests for trend calculation."""

    def test_calc_trend_up(self, sample_raw_df):
        """When slope > 0, trend_up should have the ratio value."""
        ratio = _calc_ratio(sample_raw_df)
        ma = _calc_ma(ratio, period=10)
        slope = _calc_slope(ma)
        trend_up, trend_down = _calc_trend(ratio, slope)

        # Where slope > 0, trend_up should equal ratio
        for i in range(len(slope)):
            if pd.notna(slope.iloc[i]) and slope.iloc[i] > 0:
                assert trend_up.iloc[i] == ratio.iloc[i]

    def test_calc_trend_down(self, sample_raw_df):
        """When slope <= 0, trend_down should have the ratio value."""
        ratio = _calc_ratio(sample_raw_df)
        ma = _calc_ma(ratio, period=10)
        slope = _calc_slope(ma)
        trend_up, trend_down = _calc_trend(ratio, slope)

        # Where slope <= 0 and not NaN, trend_down should equal ratio
        for i in range(len(slope)):
            if pd.notna(slope.iloc[i]) and slope.iloc[i] <= 0:
                assert trend_down.iloc[i] == ratio.iloc[i]


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


class TestDetectPeaksTroughs:
    """Unit tests for _detect_peaks_troughs helper and integration."""

    def test_detect_peaks_returns_indices(self):
        """Peaks are detected at the tops of a sine wave."""
        df = _make_sine_raw_df(n=200, period=40, amplitude=0.1)
        ratio = _calc_ratio(df)
        ma = _calc_ma(ratio, period=10)
        peaks, _ = _detect_peaks_troughs(ma, distance=20, prominence=0.01)

        assert len(peaks) > 0, "At least one peak should be detected"
        for idx in peaks:
            assert 0 <= idx < len(ma)

    def test_detect_troughs_returns_indices(self):
        """Troughs are detected at the bottoms of a sine wave."""
        df = _make_sine_raw_df(n=200, period=40, amplitude=0.1)
        ratio = _calc_ratio(df)
        ma = _calc_ma(ratio, period=10)
        _, troughs = _detect_peaks_troughs(ma, distance=20, prominence=0.01)

        assert len(troughs) > 0, "At least one trough should be detected"
        for idx in troughs:
            assert 0 <= idx < len(ma)

    def test_peaks_troughs_in_calculate_indicators(self):
        """calculate_indicators adds is_peak / is_trough boolean columns."""
        df = _make_sine_raw_df(n=200, period=40, amplitude=0.1)
        config = IndicatorConfig()
        result = calculate_indicators(df, config)

        assert "is_peak" in result.columns
        assert "is_trough" in result.columns
        assert result["is_peak"].dtype == bool
        assert result["is_trough"].dtype == bool
        assert result["is_peak"].sum() > 0
        assert result["is_trough"].sum() > 0

    def test_custom_peak_config(self):
        """distance / prominence parameters influence detection count."""
        df = _make_sine_raw_df(n=300, period=40, amplitude=0.1)
        config_default = IndicatorConfig()
        config_strict = IndicatorConfig(peak_distance=60, peak_prominence=0.05)

        result_default = calculate_indicators(df, config_default)
        result_strict = calculate_indicators(df, config_strict)

        assert result_strict["is_peak"].sum() <= result_default["is_peak"].sum()
        assert result_strict["is_trough"].sum() <= result_default["is_trough"].sum()
