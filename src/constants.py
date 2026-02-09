"""Centralized constants for uptrend dashboard."""

SECTORS = [
    "sec_basicmaterials",
    "sec_communicationservices",
    "sec_consumercyclical",
    "sec_consumerdefensive",
    "sec_energy",
    "sec_financial",
    "sec_healthcare",
    "sec_industrials",
    "sec_realestate",
    "sec_technology",
    "sec_utilities",
]

VALID_WORKSHEETS = ["all"] + SECTORS

SECTOR_DISPLAY_NAMES = {
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

# Indicator thresholds
UPPER_THRESHOLD = 0.37
LOWER_THRESHOLD = 0.097
MA_PERIOD = 10
PEAK_DISTANCE = 20
PEAK_PROMINENCE = 0.015

# Chart layout
CHART_HEIGHT_RATIO = 500
CHART_HEIGHT_SUMMARY = 450
CHART_HEIGHT_COMPARISON = 600
CHART_Y_MAX_MIN = 0.6
CHART_Y_MAX_MULTIPLIER = 1.1
