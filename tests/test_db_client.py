"""Tests for db_client module."""

import sqlite3

import pandas as pd
import pytest

from src.db_client import DBClient


class TestDBClient:
    """Tests for the DBClient class."""

    def test_init_creates_table(self, tmp_db):
        """DBClient(tmp_db) should auto-create the uptrend_raw table."""
        client = DBClient(tmp_db)
        conn = sqlite3.connect(tmp_db)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='uptrend_raw'"
        )
        tables = cursor.fetchall()
        conn.close()
        assert len(tables) == 1

    def test_upsert_inserts_new_row(self, db_client, tmp_db):
        """upsert_raw_data should insert a new row."""
        db_client.upsert_raw_data("2024-01-02", "all", 150, 500)
        conn = sqlite3.connect(tmp_db)
        cursor = conn.execute("SELECT * FROM uptrend_raw")
        rows = cursor.fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0] == ("2024-01-02", "all", 150, 500)

    def test_upsert_replaces_existing(self, db_client, tmp_db):
        """upsert_raw_data should replace an existing row with same PK."""
        db_client.upsert_raw_data("2024-01-02", "all", 150, 500)
        db_client.upsert_raw_data("2024-01-02", "all", 200, 600)
        conn = sqlite3.connect(tmp_db)
        cursor = conn.execute("SELECT * FROM uptrend_raw")
        rows = cursor.fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0] == ("2024-01-02", "all", 200, 600)

    def test_upsert_bulk(self, db_client, tmp_db):
        """upsert_bulk should insert all rows from a DataFrame."""
        df = pd.DataFrame({
            "date": ["2024-01-02", "2024-01-03", "2024-01-04"],
            "worksheet": ["all", "all", "all"],
            "count": [150, 160, 170],
            "total": [500, 500, 500],
        })
        db_client.upsert_bulk(df)
        conn = sqlite3.connect(tmp_db)
        cursor = conn.execute("SELECT COUNT(*) FROM uptrend_raw")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 3

    def test_fetch_raw_data(self, db_client):
        """fetch_raw_data should return data for a single worksheet sorted by date."""
        db_client.upsert_raw_data("2024-01-03", "all", 160, 500)
        db_client.upsert_raw_data("2024-01-02", "all", 150, 500)
        db_client.upsert_raw_data("2024-01-02", "sec_technology", 50, 100)

        df = db_client.fetch_raw_data("all")
        assert len(df) == 2
        assert list(df.columns) == ["date", "count", "total"]
        assert pd.api.types.is_datetime64_any_dtype(df["date"])
        # Should be sorted ascending
        assert df.iloc[0]["date"] < df.iloc[1]["date"]

    def test_fetch_raw_data_empty(self, db_client):
        """fetch_raw_data should return empty DataFrame for missing worksheet."""
        df = db_client.fetch_raw_data("sec_technology")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert list(df.columns) == ["date", "count", "total"]

    def test_fetch_all_raw_data(self, db_client):
        """fetch_all_raw_data should return dict of all worksheets with data."""
        db_client.upsert_raw_data("2024-01-02", "all", 150, 500)
        db_client.upsert_raw_data("2024-01-02", "sec_technology", 50, 100)

        result = db_client.fetch_all_raw_data()
        assert isinstance(result, dict)
        assert "all" in result
        assert "sec_technology" in result
        assert len(result["all"]) == 1
        assert len(result["sec_technology"]) == 1

    def test_get_worksheets(self, db_client):
        """get_worksheets should return list of registered worksheet names."""
        db_client.upsert_raw_data("2024-01-02", "all", 150, 500)
        db_client.upsert_raw_data("2024-01-02", "sec_technology", 50, 100)
        db_client.upsert_raw_data("2024-01-02", "sec_healthcare", 30, 80)

        worksheets = db_client.get_worksheets()
        assert isinstance(worksheets, list)
        assert set(worksheets) == {"all", "sec_technology", "sec_healthcare"}

    def test_get_date_range(self, db_client):
        """get_date_range should return (min_date, max_date) tuple."""
        db_client.upsert_raw_data("2024-01-02", "all", 150, 500)
        db_client.upsert_raw_data("2024-01-05", "all", 160, 500)
        db_client.upsert_raw_data("2024-01-10", "all", 170, 500)

        min_date, max_date = db_client.get_date_range("all")
        assert min_date == "2024-01-02"
        assert max_date == "2024-01-10"
