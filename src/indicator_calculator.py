"""Derived indicator calculations for uptrend dashboard."""

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from scipy.signal import find_peaks

logger = logging.getLogger(__name__)


@dataclass
class IndicatorConfig:
    """Configuration for indicator calculations."""

    ma_period: int = 10
    upper_threshold: float = 0.37
    lower_threshold: float = 0.097
    peak_distance: int = 20
    peak_prominence: float = 0.015


def _calc_ratio(df: pd.DataFrame) -> pd.Series:
    """Calculate ratio = count / total, handling zero total and NaN values."""
    count = df["count"].fillna(0)
    total = df["total"].fillna(0)
    return pd.Series(
        np.where(total == 0, 0.0, count / total),
        index=df.index,
    )


def _calc_ma(ratio: pd.Series, period: int = 10) -> pd.Series:
    """Calculate simple moving average of ratio."""
    return ratio.rolling(window=period).mean()


def _calc_slope(ma: pd.Series) -> pd.Series:
    """Calculate slope as 1-day difference of MA."""
    return ma.diff()


def _calc_trend(ratio: pd.Series, slope: pd.Series) -> Tuple[pd.Series, pd.Series]:
    """Split ratio into trend_up and trend_down based on slope.

    Returns:
        (trend_up, trend_down) where:
        - trend_up has ratio values where slope > 0, NaN otherwise
        - trend_down has ratio values where slope <= 0, NaN otherwise
        - Both are NaN where slope is NaN
    """
    trend_up = pd.Series(np.nan, index=ratio.index)
    trend_down = pd.Series(np.nan, index=ratio.index)

    up_mask = slope > 0
    down_mask = slope.notna() & (slope <= 0)

    trend_up[up_mask] = ratio[up_mask]
    trend_down[down_mask] = ratio[down_mask]

    return trend_up, trend_down


def _detect_peaks_troughs(
    ma: pd.Series, distance: int, prominence: float
) -> Tuple[np.ndarray, np.ndarray]:
    """Detect peaks (tops) and troughs (bottoms) in a moving average series.

    Args:
        ma: Moving average series (may contain leading NaNs).
        distance: Minimum distance between peaks in data points.
        prominence: Minimum prominence for peak detection.

    Returns:
        (peak_indices, trough_indices) mapped back to the original series index.
    """
    valid = ma.dropna()
    if len(valid) == 0:
        return np.array([], dtype=int), np.array([], dtype=int)

    offset = ma.index.get_loc(valid.index[0])
    if isinstance(offset, slice):
        offset = offset.start

    peaks, _ = find_peaks(valid.values, distance=distance, prominence=prominence)
    troughs, _ = find_peaks(-valid.values, distance=distance, prominence=prominence)

    return peaks + offset, troughs + offset


def calculate_indicators(
    df: pd.DataFrame, config: Optional[IndicatorConfig] = None
) -> pd.DataFrame:
    """Calculate all derived indicators from raw data.

    Args:
        df: DataFrame with columns (date, count, total).
        config: Optional configuration for MA period and thresholds.

    Returns:
        DataFrame with added columns: ratio, ma_10, slope, trend_up, trend_down,
        upper, lower, is_peak, is_trough.
    """
    if config is None:
        config = IndicatorConfig()

    result = df.copy()
    ratio = pd.Series(_calc_ratio(result), index=result.index)
    result["ratio"] = ratio
    result["ma_10"] = _calc_ma(ratio, period=config.ma_period)
    result["slope"] = _calc_slope(result["ma_10"])
    result["trend_up"], result["trend_down"] = _calc_trend(ratio, result["slope"])
    result["upper"] = config.upper_threshold
    result["lower"] = config.lower_threshold

    peak_idx, trough_idx = _detect_peaks_troughs(
        result["ma_10"], config.peak_distance, config.peak_prominence
    )
    result["is_peak"] = False
    result["is_trough"] = False
    if len(peak_idx) > 0:
        result.iloc[peak_idx, result.columns.get_loc("is_peak")] = True
    if len(trough_idx) > 0:
        result.iloc[trough_idx, result.columns.get_loc("is_trough")] = True

    return result
