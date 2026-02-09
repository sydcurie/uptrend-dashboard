"""SQLite data access layer for uptrend dashboard."""

import os
import sqlite3
from typing import Dict, List, Tuple

import pandas as pd


VALID_WORKSHEETS = [
    "all",
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


class DBClient:
    """Client for reading and writing uptrend data to SQLite."""

    def __init__(self, db_path: str = "data/uptrend.db"):
        self.db_path = db_path
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_tables(self) -> None:
        conn = self._get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS uptrend_raw (
                date      TEXT    NOT NULL,
                worksheet TEXT    NOT NULL,
                count     INTEGER NOT NULL,
                total     INTEGER NOT NULL,
                PRIMARY KEY (date, worksheet)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_uptrend_raw_worksheet
                ON uptrend_raw (worksheet, date)
        """)
        conn.commit()
        conn.close()

    def upsert_raw_data(self, date: str, worksheet: str, count: int, total: int) -> None:
        conn = self._get_connection()
        conn.execute(
            "INSERT OR REPLACE INTO uptrend_raw (date, worksheet, count, total) VALUES (?, ?, ?, ?)",
            (date, worksheet, count, total),
        )
        conn.commit()
        conn.close()

    def upsert_bulk(self, df: pd.DataFrame) -> None:
        conn = self._get_connection()
        for _, row in df.iterrows():
            conn.execute(
                "INSERT OR REPLACE INTO uptrend_raw (date, worksheet, count, total) VALUES (?, ?, ?, ?)",
                (str(row["date"]), str(row["worksheet"]), int(row["count"]), int(row["total"])),
            )
        conn.commit()
        conn.close()

    def fetch_raw_data(self, worksheet: str) -> pd.DataFrame:
        conn = self._get_connection()
        df = pd.read_sql_query(
            "SELECT date, count, total FROM uptrend_raw WHERE worksheet = ? ORDER BY date ASC",
            conn,
            params=(worksheet,),
        )
        conn.close()
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
        else:
            df = pd.DataFrame(columns=["date", "count", "total"])
        return df

    def fetch_all_raw_data(self) -> Dict[str, pd.DataFrame]:
        worksheets = self.get_worksheets()
        return {ws: self.fetch_raw_data(ws) for ws in worksheets}

    def get_worksheets(self) -> List[str]:
        conn = self._get_connection()
        cursor = conn.execute("SELECT DISTINCT worksheet FROM uptrend_raw ORDER BY worksheet")
        result = [row[0] for row in cursor.fetchall()]
        conn.close()
        return result

    def get_date_range(self, worksheet: str) -> Tuple[str, str]:
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT MIN(date), MAX(date) FROM uptrend_raw WHERE worksheet = ?",
            (worksheet,),
        )
        row = cursor.fetchone()
        conn.close()
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
