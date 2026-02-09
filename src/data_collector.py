"""Finviz Elite CSV-based data collector for uptrend dashboard."""

import io
import logging
import random
import time
from dataclasses import dataclass
from datetime import date
from typing import Dict, Optional, Tuple

import pandas as pd
import requests

from src.constants import SECTORS, VALID_WORKSHEETS
from src.db_client import DBClient

logger = logging.getLogger(__name__)

# Finviz screener filters
_BASE_FILTERS = ["cap_microover", "sh_avgvol_o100", "sh_price_o10"]
_UPTREND_FILTERS = _BASE_FILTERS + [
    "ta_highlow52w_a30h",
    "ta_perf2_4wup",
    "ta_sma20_pa",
    "ta_sma200_pa",
    "ta_sma50_sa200",
]


@dataclass
class CollectorConfig:
    """Configuration for DataCollector."""

    finviz_api_key: str
    base_url: str = "https://elite.finviz.com"
    max_retries: int = 5
    retry_delay: float = 2.0
    request_interval: float = 2.0
    http_timeout: float = 30.0


class DataCollector:
    """Collects uptrend stock counts from Finviz Elite CSV export API."""

    def __init__(self, db_client: DBClient, config: CollectorConfig):
        self._db = db_client
        self._config = config
        self._session = requests.Session()

    def _build_filters(self, uptrend: bool, sector: str = None) -> str:
        filters = list(_UPTREND_FILTERS if uptrend else _BASE_FILTERS)
        if sector:
            filters.append(sector)
        return ",".join(filters)

    def _build_url(self, uptrend: bool, sector: str = None) -> str:
        filters = self._build_filters(uptrend, sector)
        return (
            f"{self._config.base_url}/export.ashx"
            f"?v=151&f={filters}&ft=4&auth={self._config.finviz_api_key}"
        )

    def _build_uptrend_url(self, sector: str = None) -> str:
        return self._build_url(uptrend=True, sector=sector)

    def _build_total_url(self, sector: str = None) -> str:
        return self._build_url(uptrend=False, sector=sector)

    _RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    def _make_request(self, url: str) -> pd.DataFrame:
        """Fetch CSV from Finviz with exponential backoff retry + jitter."""
        delay = self._config.retry_delay
        for attempt in range(1, self._config.max_retries + 1):
            try:
                resp = self._session.get(url, timeout=self._config.http_timeout)
                resp.raise_for_status()
                try:
                    return pd.read_csv(io.BytesIO(resp.content))
                except pd.errors.EmptyDataError:
                    logger.warning("Empty CSV body received")
                    return pd.DataFrame()
            except (requests.ConnectionError, requests.Timeout) as exc:
                logger.warning("Request failed (attempt %d/%d): %s",
                               attempt, self._config.max_retries, exc)
                if attempt == self._config.max_retries:
                    raise
                jitter = random.uniform(0, delay * 0.25)
                time.sleep(delay + jitter)
                delay *= 2
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status in self._RETRYABLE_STATUS_CODES:
                    logger.warning("HTTP %s (attempt %d/%d), backing off %.1fs",
                                   status, attempt, self._config.max_retries, delay)
                    if attempt == self._config.max_retries:
                        raise
                    jitter = random.uniform(0, delay * 0.25)
                    time.sleep(delay + jitter)
                    delay *= 2
                else:
                    raise

    def _fetch_stock_count(self, sector: str = None) -> Tuple[int, int]:
        """Fetch uptrend count and total count for a sector (or all)."""
        uptrend_url = self._build_uptrend_url(sector)
        total_url = self._build_total_url(sector)

        uptrend_df = self._make_request(uptrend_url)
        time.sleep(self._config.request_interval)
        total_df = self._make_request(total_url)

        return len(uptrend_df), len(total_df)

    def _validate_counts(self, worksheet: str, count: int, total: int) -> None:
        """Validate count and total values before DB write."""
        if count < 0 or total < 0:
            raise ValueError(
                f"Invalid negative value for {worksheet}: "
                f"count={count}, total={total}"
            )
        if count > total:
            raise ValueError(
                f"count exceeds total for {worksheet}: "
                f"count={count}, total={total}"
            )

    def collect_worksheet(
        self, worksheet: str, date: Optional[str] = None, dry_run: bool = False
    ) -> Tuple[int, int]:
        """Collect data for a single worksheet and write to DB."""
        if worksheet not in VALID_WORKSHEETS:
            raise ValueError(
                f"Invalid worksheet: '{worksheet}'. "
                f"Must be one of {VALID_WORKSHEETS}"
            )
        if date is None:
            from datetime import date as date_cls
            date = date_cls.today().isoformat()

        sector = worksheet if worksheet != "all" else None
        count, total = self._fetch_stock_count(sector)
        self._validate_counts(worksheet, count, total)

        if dry_run:
            logger.info("Dry run %s: count=%d, total=%d", worksheet, count, total)
        elif total > 0:
            self._db.upsert_raw_data(date, worksheet, count, total)
            logger.info("Collected %s: count=%d, total=%d", worksheet, count, total)
        else:
            logger.warning("Skipping %s: total=0", worksheet)

        return count, total

    def collect_all(
        self, date: Optional[str] = None, dry_run: bool = False
    ) -> Dict[str, Tuple[int, int]]:
        """Collect data for all 12 worksheets."""
        if date is None:
            from datetime import date as date_cls
            date = date_cls.today().isoformat()

        results = {}
        for worksheet in VALID_WORKSHEETS:
            try:
                results[worksheet] = self.collect_worksheet(
                    worksheet, date, dry_run=dry_run,
                )
            except (requests.RequestException, ValueError, pd.errors.EmptyDataError) as exc:
                logger.error("Failed to collect %s: %s", worksheet, exc, exc_info=True)
        return results

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()
