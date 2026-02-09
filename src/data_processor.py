"""Data processing utilities for uptrend dashboard (v2)."""

import logging
from dataclasses import dataclass, asdict
from typing import Dict, Optional

import pandas as pd
import numpy as np

from src.constants import SECTOR_DISPLAY_NAMES

logger = logging.getLogger(__name__)


@dataclass
class MarketStatus:
    """Current market status extracted from the latest indicator data."""

    date: str
    ratio: float
    ratio_10ma: Optional[float]
    trend: str
    slope: float
    is_overbought: bool
    is_oversold: bool

    def __getitem__(self, key):
        return getattr(self, key)

    def __contains__(self, key):
        return key in self.__dataclass_fields__

    def keys(self):
        return self.__dataclass_fields__.keys()


def get_current_status(df: pd.DataFrame) -> MarketStatus:
    """Extract current status from the latest row of a calculated DataFrame."""
    if df.empty:
        logger.warning("get_current_status called with empty DataFrame")
        return MarketStatus(
            date="",
            ratio=0.0,
            ratio_10ma=None,
            trend="down",
            slope=0.0,
            is_overbought=False,
            is_oversold=False,
        )

    latest = df.iloc[-1]

    trend = "up" if pd.notna(latest.get("trend_up")) else "down"

    ratio = float(latest["ratio"])
    upper = float(latest["upper"]) if pd.notna(latest.get("upper")) else 0.37
    lower = float(latest["lower"]) if pd.notna(latest.get("lower")) else 0.097

    return MarketStatus(
        date=str(latest["date"].date()) if hasattr(latest["date"], "date") else str(latest["date"]),
        ratio=ratio,
        ratio_10ma=float(latest["ma_10"]) if pd.notna(latest.get("ma_10")) else None,
        trend=trend,
        slope=float(latest["slope"]) if pd.notna(latest.get("slope")) else 0.0,
        is_overbought=ratio > upper,
        is_oversold=ratio < lower,
    )


def get_sector_display_name(worksheet_name: str) -> str:
    """Convert worksheet name like 'sec_basicmaterials' to 'Basic Materials'."""
    suffix = worksheet_name.replace("sec_", "", 1)
    return SECTOR_DISPLAY_NAMES.get(suffix, suffix.title())


def build_sector_summary(all_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Build a summary DataFrame of all sectors' latest status."""
    rows = []
    for name, df in all_data.items():
        if name == "all" or df.empty:
            continue
        status = get_current_status(df)
        if status["is_overbought"]:
            market_status = "Overbought"
        elif status["is_oversold"]:
            market_status = "Oversold"
        else:
            market_status = "Normal"

        rows.append(
            {
                "Sector": get_sector_display_name(name),
                "Ratio": status["ratio"],
                "10MA": status["ratio_10ma"],
                "Trend": "Up" if status["trend"] == "up" else "Down",
                "Slope": status["slope"],
                "Status": market_status,
            }
        )

    if not rows:
        return pd.DataFrame(columns=["Sector", "Ratio", "10MA", "Trend", "Slope", "Status"])

    summary = pd.DataFrame(rows)
    summary = summary.sort_values("Ratio", ascending=False).reset_index(drop=True)
    return summary


def filter_by_date_range(df: pd.DataFrame, start, end) -> pd.DataFrame:
    """Filter a DataFrame by date range (inclusive).

    Args:
        df: DataFrame with a 'date' column (datetime).
        start: Start date (date object).
        end: End date (date object).

    Returns:
        Filtered DataFrame.
    """
    mask = (df["date"].dt.date >= start) & (df["date"].dt.date <= end)
    return df[mask]
