"""Finviz Elite CSV-based data collector for uptrend dashboard."""

import io
import logging
import random
import re
import time
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests

from src.constants import INDUSTRIES, SECTORS, VALID_WORKSHEETS
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


class CollectScope(Enum):
    """Scope for data collection."""

    SECTORS = "sectors"      # "all" + 11 sectors (12 worksheets)
    INDUSTRIES = "industries"  # 149 industries
    ALL = "all"              # all 161 worksheets


@dataclass
class CollectResult:
    """Result of a collect_all run, separating succeeded and failed worksheets."""

    succeeded: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    failed: List[str] = field(default_factory=list)

    @property
    def sector_succeeded(self) -> Dict[str, Tuple[int, int]]:
        return {k: v for k, v in self.succeeded.items() if k == "all" or k.startswith("sec_")}

    @property
    def industry_succeeded(self) -> Dict[str, Tuple[int, int]]:
        return {k: v for k, v in self.succeeded.items() if k.startswith("ind_")}

    @property
    def sector_failed(self) -> List[str]:
        return [k for k in self.failed if k == "all" or k.startswith("sec_")]

    @property
    def industry_failed(self) -> List[str]:
        return [k for k in self.failed if k.startswith("ind_")]


def mask_secrets(text: str) -> str:
    """Mask known secrets from URLs and exception messages."""
    if not text:
        return text
    return re.sub(r"(auth=)[^&\s]+", r"\1***", text)


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

    @staticmethod
    def _safe_http_error(exc: requests.HTTPError) -> requests.HTTPError:
        """Create an HTTPError with a sanitized message."""
        status = exc.response.status_code if exc.response is not None else "unknown"
        return requests.HTTPError(f"HTTP {status} from Finviz export API")

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
                logger.warning(
                    "Request failed (attempt %d/%d): %s",
                    attempt,
                    self._config.max_retries,
                    mask_secrets(str(exc)),
                )
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
                        raise self._safe_http_error(exc) from exc
                    jitter = random.uniform(0, delay * 0.25)
                    time.sleep(delay + jitter)
                    delay *= 2
                else:
                    raise self._safe_http_error(exc) from exc

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
            raise ValueError(
                f"Empty data for {worksheet}: total=0 "
                f"(API returned no stocks matching filters)"
            )

        return count, total

    def collect_all(
        self,
        date: Optional[str] = None,
        dry_run: bool = False,
        scope: CollectScope = CollectScope.ALL,
    ) -> CollectResult:
        """Collect data for worksheets determined by scope.

        Args:
            date: Date string in YYYY-MM-DD format (default: today).
            dry_run: If True, fetch data without writing to DB.
            scope: Which worksheets to collect (ALL, SECTORS, or INDUSTRIES).
        """
        if date is None:
            from datetime import date as date_cls
            date = date_cls.today().isoformat()

        if scope == CollectScope.SECTORS:
            worksheets = ["all"] + SECTORS
        elif scope == CollectScope.INDUSTRIES:
            worksheets = list(INDUSTRIES)
        else:
            worksheets = list(VALID_WORKSHEETS)

        result = CollectResult()
        total = len(worksheets)
        for idx, worksheet in enumerate(worksheets):
            logger.info("Collecting %d/%d: %s", idx + 1, total, worksheet)
            try:
                result.succeeded[worksheet] = self.collect_worksheet(
                    worksheet, date, dry_run=dry_run,
                )
            except (requests.RequestException, ValueError, pd.errors.EmptyDataError) as exc:
                logger.error("Failed to collect %s: %s", worksheet, mask_secrets(str(exc)))
                result.failed.append(worksheet)
        return result

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()
