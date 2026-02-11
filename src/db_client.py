"""SQLite data access layer for uptrend dashboard."""

import logging
import numbers
import os
import sqlite3
from contextlib import contextmanager
from typing import Dict, List, Tuple

import pandas as pd

from src.constants import VALID_WORKSHEETS


logger = logging.getLogger(__name__)


class DBClient:
    """Client for reading and writing uptrend data to SQLite."""

    def __init__(self, db_path: str = "data/uptrend.db"):
        self.db_path = db_path
        self._init_tables()

    @contextmanager
    def _connection(self):
        """Context manager for database connections with automatic cleanup."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_tables(self) -> None:
        with self._connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS uptrend_raw (
                    date      TEXT    NOT NULL,
                    worksheet TEXT    NOT NULL,
                    count     INTEGER NOT NULL CHECK (count >= 0),
                    total     INTEGER NOT NULL CHECK (total >= 0),
                    CHECK (count <= total),
                    PRIMARY KEY (date, worksheet)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_uptrend_raw_worksheet
                    ON uptrend_raw (worksheet, date)
            """)

    @staticmethod
    def _coerce_whole_number(value, field_name: str) -> int:
        """Coerce integer-like values to int, rejecting non-integers."""
        if isinstance(value, bool):
            raise ValueError(f"{field_name} must be an integer, got bool")
        if isinstance(value, numbers.Integral):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        raise ValueError(f"{field_name} must be an integer, got {value!r}")

    def _validate_counts(self, count, total) -> Tuple[int, int]:
        """Validate count/total values and return coerced ints."""
        count_i = self._coerce_whole_number(count, "count")
        total_i = self._coerce_whole_number(total, "total")
        if count_i < 0 or total_i < 0:
            raise ValueError(f"count and total must be non-negative: count={count_i}, total={total_i}")
        if count_i > total_i:
            raise ValueError(f"count cannot exceed total: count={count_i}, total={total_i}")
        return count_i, total_i

    def upsert_raw_data(self, date: str, worksheet: str, count: int, total: int) -> None:
        if worksheet not in VALID_WORKSHEETS:
            raise ValueError(f"Invalid worksheet: '{worksheet}'. Must be one of {VALID_WORKSHEETS}")
        count, total = self._validate_counts(count, total)
        with self._connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO uptrend_raw (date, worksheet, count, total) VALUES (?, ?, ?, ?)",
                (date, worksheet, count, total),
            )
        logger.debug("Upserted row: date=%s, worksheet=%s", date, worksheet)

    def upsert_bulk(self, df: pd.DataFrame) -> None:
        required_columns = {"date", "worksheet", "count", "total"}
        missing = required_columns - set(df.columns)
        if missing:
            raise ValueError(f"DataFrame missing required columns: {sorted(missing)}")

        invalid = set(df["worksheet"].unique()) - set(VALID_WORKSHEETS)
        if invalid:
            raise ValueError(f"Invalid worksheet(s): {invalid}. Must be one of {VALID_WORKSHEETS}")

        counts = pd.to_numeric(df["count"], errors="coerce")
        totals = pd.to_numeric(df["total"], errors="coerce")

        if counts.isna().any() or totals.isna().any():
            raise ValueError("count/total contain non-numeric values")

        non_integer_mask = (counts % 1 != 0) | (totals % 1 != 0)
        if non_integer_mask.any():
            bad_rows = non_integer_mask[non_integer_mask].index.tolist()
            raise ValueError(f"count/total must be integers (bad rows: {bad_rows})")

        negative_mask = (counts < 0) | (totals < 0)
        if negative_mask.any():
            bad_rows = negative_mask[negative_mask].index.tolist()
            raise ValueError(f"count/total must be non-negative (bad rows: {bad_rows})")

        exceeds_mask = counts > totals
        if exceeds_mask.any():
            bad_rows = exceeds_mask[exceeds_mask].index.tolist()
            raise ValueError(f"count cannot exceed total (bad rows: {bad_rows})")

        rows = [
            (
                str(row["date"]),
                str(row["worksheet"]),
                int(counts.loc[idx]),
                int(totals.loc[idx]),
            )
            for idx, row in df.iterrows()
        ]
        with self._connection() as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO uptrend_raw (date, worksheet, count, total) VALUES (?, ?, ?, ?)",
                rows,
            )
        logger.info("Bulk upserted %d rows", len(rows))

    def fetch_raw_data(self, worksheet: str) -> pd.DataFrame:
        with self._connection() as conn:
            df = pd.read_sql_query(
                "SELECT date, count, total FROM uptrend_raw WHERE worksheet = ? ORDER BY date ASC",
                conn,
                params=(worksheet,),
            )
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
        else:
            df = pd.DataFrame(columns=["date", "count", "total"])
        return df

    def fetch_all_raw_data(self) -> Dict[str, pd.DataFrame]:
        worksheets = self.get_worksheets()
        return {ws: self.fetch_raw_data(ws) for ws in worksheets}

    def get_worksheets(self) -> List[str]:
        with self._connection() as conn:
            cursor = conn.execute("SELECT DISTINCT worksheet FROM uptrend_raw ORDER BY worksheet")
            result = [row[0] for row in cursor.fetchall()]
        return result

    def get_date_range(self, worksheet: str) -> Tuple[str, str]:
        with self._connection() as conn:
            cursor = conn.execute(
                "SELECT MIN(date), MAX(date) FROM uptrend_raw WHERE worksheet = ?",
                (worksheet,),
            )
            row = cursor.fetchone()
        return (row[0], row[1])


def load_all_data(db_path: str = None) -> Dict[str, pd.DataFrame]:
    """Load all data from SQLite and calculate indicators.

    This function is intended to be wrapped with @st.cache_data(ttl=3600)
    in the Streamlit app layer.
    """
    from src.indicator_calculator import calculate_indicators

    if db_path is None:
        db_path = os.environ.get("DB_PATH", "data/uptrend.db")
    client = DBClient(db_path)
    raw_data = client.fetch_all_raw_data()
    return {name: calculate_indicators(df) for name, df in raw_data.items() if not df.empty}
