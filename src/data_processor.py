"""Data processing utilities for uptrend dashboard (v2)."""

from typing import Dict

import pandas as pd
import numpy as np


# Mapping of camelCase sector suffixes to display names
_SECTOR_WORD_MAP = {
    "basicmaterials": "Basic Materials",
    "communicationservices": "Communication Services",
    "consumercyclical": "Consumer Cyclical",
    "consumerdefensive": "Consumer Defensive",
    "energy": "Energy",
    "financial": "Financial",
    "healthcare": "Healthcare",
    "industrials": "Industrials",
    "realestate": "Real Estate",
    "technology": "Technology",
    "utilities": "Utilities",
}


def get_current_status(df: pd.DataFrame) -> dict:
    """Extract current status from the latest row of a calculated DataFrame."""
    latest = df.iloc[-1]

    trend = "up" if pd.notna(latest.get("trend_up")) else "down"

    ratio = float(latest["ratio"])
    upper = float(latest["upper"]) if pd.notna(latest.get("upper")) else 0.37
    lower = float(latest["lower"]) if pd.notna(latest.get("lower")) else 0.097

    return {
        "date": str(latest["date"].date()) if hasattr(latest["date"], "date") else str(latest["date"]),
        "ratio": ratio,
        "ratio_10ma": float(latest["ma_10"]) if pd.notna(latest.get("ma_10")) else None,
        "trend": trend,
        "slope": float(latest["slope"]) if pd.notna(latest.get("slope")) else 0.0,
        "is_overbought": ratio > upper,
        "is_oversold": ratio < lower,
    }


def _sector_display_name(worksheet_name: str) -> str:
    """Convert worksheet name like 'sec_basicmaterials' to 'Basic Materials'."""
    suffix = worksheet_name.replace("sec_", "", 1)
    return _SECTOR_WORD_MAP.get(suffix, suffix.title())


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
                "Sector": _sector_display_name(name),
                "Ratio": status["ratio"],
                "10MA": status["ratio_10ma"],
                "Trend": "Up" if status["trend"] == "up" else "Down",
                "Slope": status["slope"],
                "Status": market_status,
            }
        )

    summary = pd.DataFrame(rows)
    summary = summary.sort_values("Ratio", ascending=False).reset_index(drop=True)
    return summary
