"""Tests for DataCollector — Finviz Elite CSV-based data collection."""

from unittest.mock import MagicMock, call

import pandas as pd
import pytest
import requests

from src.data_collector import CollectorConfig, DataCollector


class TestCollectorConfig:
    """Test CollectorConfig defaults."""

    def test_default_values(self):
        config = CollectorConfig(finviz_api_key="test_key")
        assert config.base_url == "https://elite.finviz.com"
        assert config.max_retries == 5
        assert config.retry_delay == 2.0
        assert config.request_interval == 2.0
        assert config.http_timeout == 30.0


class TestBuildUrl:
    """Test URL construction for Finviz CSV export API."""

    @pytest.fixture
    def collector(self, db_client):
        config = CollectorConfig(finviz_api_key="test_key_123")
        return DataCollector(db_client=db_client, config=config)

    def test_build_uptrend_url_no_sector(self, collector):
        url = collector._build_uptrend_url()
        assert "/export.ashx" in url
        assert "cap_microover" in url
        assert "sh_avgvol_o100" in url
        assert "sh_price_o10" in url
        assert "ta_highlow52w_a30h" in url
        assert "ta_perf2_4wup" in url
        assert "ta_sma20_pa" in url
        assert "ta_sma200_pa" in url
        assert "ta_sma50_sa200" in url
        # No sector filter
        assert "sec_" not in url

    def test_build_uptrend_url_with_sector(self, collector):
        url = collector._build_uptrend_url(sector="sec_technology")
        assert "sec_technology" in url
        # All uptrend filters still present
        assert "ta_sma50_sa200" in url

    def test_build_total_url_no_sector(self, collector):
        url = collector._build_total_url()
        assert "cap_microover" in url
        assert "sh_avgvol_o100" in url
        assert "sh_price_o10" in url
        # No technical filters
        assert "ta_highlow52w_a30h" not in url
        assert "ta_sma50_sa200" not in url

    def test_build_total_url_with_sector(self, collector):
        url = collector._build_total_url(sector="sec_financial")
        assert "sec_financial" in url
        assert "cap_microover" in url
        # No technical filters
        assert "ta_sma50_sa200" not in url

    def test_url_contains_auth_key(self, collector):
        url = collector._build_uptrend_url()
        assert "auth=test_key_123" in url

    def test_url_uses_export_endpoint(self, collector):
        url = collector._build_uptrend_url()
        assert url.startswith("https://elite.finviz.com/export.ashx?")
        assert "v=151" in url
        assert "ft=4" in url


def _csv_response(csv_text, status_code=200):
    """Helper to create a mock response with CSV content."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.content = csv_text.encode("utf-8")
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
    return resp


SAMPLE_CSV = "No.,Ticker,Company,Sector\n1,AAPL,Apple Inc.,Technology\n2,MSFT,Microsoft,Technology\n3,GOOGL,Alphabet,Technology\n"
EMPTY_CSV = "No.,Ticker,Company,Sector\n"


class TestFetchStockCount:
    """Test HTTP fetching and CSV parsing."""

    @pytest.fixture
    def collector(self, db_client):
        config = CollectorConfig(
            finviz_api_key="test_key",
            max_retries=3,
            retry_delay=0.01,
            request_interval=0.0,
        )
        return DataCollector(db_client=db_client, config=config)

    def test_fetch_stock_count_success(self, collector, mocker):
        mock_get = mocker.patch.object(
            collector._session, "get",
            side_effect=[_csv_response(SAMPLE_CSV), _csv_response(SAMPLE_CSV)],
        )
        count, total = collector._fetch_stock_count()
        assert count == 3
        assert total == 3
        assert mock_get.call_count == 2

    def test_fetch_stock_count_retry_on_429(self, collector, mocker):
        resp_429 = _csv_response("", status_code=429)
        resp_ok = _csv_response(SAMPLE_CSV)
        mocker.patch.object(
            collector._session, "get",
            side_effect=[resp_429, resp_ok, resp_ok],
        )
        count, total = collector._fetch_stock_count()
        assert count == 3
        assert total == 3

    def test_fetch_stock_count_zero_results(self, collector, mocker):
        mocker.patch.object(
            collector._session, "get",
            side_effect=[_csv_response(EMPTY_CSV), _csv_response(SAMPLE_CSV)],
        )
        count, total = collector._fetch_stock_count()
        assert count == 0
        assert total == 3

    def test_fetch_stock_count_max_retries(self, collector, mocker):
        resp_429 = _csv_response("", status_code=429)
        mocker.patch.object(
            collector._session, "get",
            return_value=resp_429,
        )
        with pytest.raises(requests.HTTPError):
            collector._fetch_stock_count()

    def test_fetch_stock_count_network_error(self, collector, mocker):
        mocker.patch.object(
            collector._session, "get",
            side_effect=[
                requests.ConnectionError("network down"),
                _csv_response(SAMPLE_CSV),
                _csv_response(SAMPLE_CSV),
            ],
        )
        count, total = collector._fetch_stock_count()
        assert count == 3
        assert total == 3

    def test_make_request_empty_csv_body(self, collector, mocker):
        """Fix 2: 200 + empty body should return empty DataFrame."""
        resp = MagicMock(spec=requests.Response)
        resp.status_code = 200
        resp.content = b""
        resp.raise_for_status = MagicMock()
        mocker.patch.object(collector._session, "get", return_value=resp)
        result = collector._make_request("http://example.com")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_make_request_retries_on_500(self, collector, mocker):
        """Fix 3: 5xx errors should trigger retry."""
        resp_500 = _csv_response("", status_code=500)
        resp_ok = _csv_response(SAMPLE_CSV)
        mocker.patch.object(
            collector._session, "get",
            side_effect=[resp_500, resp_ok],
        )
        mocker.patch("time.sleep")
        result = collector._make_request("http://example.com")
        assert len(result) == 3

    def test_make_request_jitter_applied(self, collector, mocker):
        """Fix 3: Sleep delay should include jitter (not exact delay)."""
        resp_429 = _csv_response("", status_code=429)
        resp_ok = _csv_response(SAMPLE_CSV)
        mocker.patch.object(
            collector._session, "get",
            side_effect=[resp_429, resp_ok],
        )
        mock_sleep = mocker.patch("time.sleep")
        mocker.patch("random.uniform", return_value=0.001)
        collector._make_request("http://example.com")
        # With jitter, sleep value should be delay + jitter, not exact delay
        actual_sleep = mock_sleep.call_args[0][0]
        assert actual_sleep != collector._config.retry_delay
        assert actual_sleep > collector._config.retry_delay

    def test_session_closed(self, db_client):
        """Fix 8: close() should close the underlying Session."""
        config = CollectorConfig(finviz_api_key="test_key")
        collector = DataCollector(db_client=db_client, config=config)
        mock_session = MagicMock()
        collector._session = mock_session
        collector.close()
        mock_session.close.assert_called_once()


class TestCollectWorkflow:
    """Test collection workflow with DB integration."""

    @pytest.fixture
    def collector(self, db_client):
        config = CollectorConfig(
            finviz_api_key="test_key",
            max_retries=3,
            retry_delay=0.01,
            request_interval=0.0,
        )
        return DataCollector(db_client=db_client, config=config)

    def test_collect_worksheet(self, collector, db_client, mocker):
        mocker.patch.object(
            collector._session, "get",
            side_effect=[_csv_response(SAMPLE_CSV), _csv_response(SAMPLE_CSV)],
        )
        count, total = collector.collect_worksheet("all", date="2026-02-07")
        assert count == 3
        assert total == 3
        # Verify data was written to DB
        df = db_client.fetch_raw_data("all")
        assert len(df) == 1
        assert df.iloc[0]["count"] == 3
        assert df.iloc[0]["total"] == 3

    def test_collect_worksheet_skip_zero(self, collector, db_client, mocker):
        mocker.patch.object(
            collector._session, "get",
            side_effect=[_csv_response(EMPTY_CSV), _csv_response(EMPTY_CSV)],
        )
        count, total = collector.collect_worksheet("all", date="2026-02-07")
        assert count == 0
        assert total == 0
        # No data written when total is 0
        df = db_client.fetch_raw_data("all")
        assert len(df) == 0

    def test_collect_all(self, collector, mocker):
        mocker.patch.object(
            collector._session, "get",
            return_value=_csv_response(SAMPLE_CSV),
        )
        results = collector.collect_all(date="2026-02-07")
        # 12 worksheets: 'all' + 11 sectors
        assert len(results) == 12
        for ws, (count, total) in results.items():
            assert count == 3
            assert total == 3

    def test_collect_all_continue_on_error(self, collector, mocker):
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Fail on the first call only (first worksheet's uptrend request)
            if call_count == 1:
                raise requests.ConnectionError("network down")
            return _csv_response(SAMPLE_CSV)

        mocker.patch.object(collector._session, "get", side_effect=side_effect)
        mocker.patch.object(collector._config, "max_retries", 1)
        results = collector.collect_all(date="2026-02-07")
        # First worksheet ("all") failed, remaining 11 should succeed
        assert len(results) == 11

    def test_collect_worksheet_invalid(self, collector):
        with pytest.raises(ValueError, match="Invalid worksheet"):
            collector.collect_worksheet("invalid_sheet")

    def test_validate_counts_negative(self, collector, mocker):
        """Fix 4: Negative count/total should raise ValueError."""
        mocker.patch.object(
            collector, "_fetch_stock_count", return_value=(-1, 100),
        )
        with pytest.raises(ValueError, match="negative"):
            collector.collect_worksheet("all", date="2026-02-07")

    def test_validate_counts_count_exceeds_total(self, collector, mocker):
        """Fix 4: count > total should raise ValueError."""
        mocker.patch.object(
            collector, "_fetch_stock_count", return_value=(200, 100),
        )
        with pytest.raises(ValueError, match="exceeds total"):
            collector.collect_worksheet("all", date="2026-02-07")

    def test_collect_worksheet_dry_run(self, collector, db_client, mocker):
        """Fix 7: dry_run=True should skip DB write but run validation."""
        mocker.patch.object(
            collector._session, "get",
            side_effect=[_csv_response(SAMPLE_CSV), _csv_response(SAMPLE_CSV)],
        )
        count, total = collector.collect_worksheet("all", date="2026-02-07", dry_run=True)
        assert count == 3
        assert total == 3
        # No data written to DB
        df = db_client.fetch_raw_data("all")
        assert len(df) == 0

    def test_collect_all_dry_run(self, collector, mocker):
        """Fix 7: collect_all dry_run=True should skip DB writes."""
        mocker.patch.object(
            collector._session, "get",
            return_value=_csv_response(SAMPLE_CSV),
        )
        mock_upsert = mocker.patch.object(collector._db, "upsert_raw_data")
        results = collector.collect_all(date="2026-02-07", dry_run=True)
        assert len(results) == 12
        mock_upsert.assert_not_called()


class TestCLI:
    """Test collect.py CLI entrypoint."""

    def test_cli_default_collect_all(self, tmp_db, mocker):
        from src.constants import VALID_WORKSHEETS as ws_list
        mocker.patch("sys.argv", ["collect.py", "--db", tmp_db])
        mocker.patch.dict("os.environ", {"FINVIZ_API_KEY": "test_key"})
        mock_collect_all = mocker.patch(
            "src.data_collector.DataCollector.collect_all",
            return_value={ws: (100, 500) for ws in ws_list},
        )
        from collect import main
        main()
        mock_collect_all.assert_called_once()

    def test_cli_missing_api_key(self, tmp_db, mocker):
        mocker.patch("sys.argv", ["collect.py", "--db", tmp_db])
        mocker.patch.dict("os.environ", {}, clear=True)
        # Also ensure dotenv doesn't load a real key
        mocker.patch("collect.load_dotenv")
        from collect import main
        with pytest.raises(SystemExit):
            main()

    def test_cli_dry_run(self, tmp_db, mocker):
        mocker.patch("sys.argv", ["collect.py", "--db", tmp_db, "--dry-run"])
        mocker.patch.dict("os.environ", {"FINVIZ_API_KEY": "test_key"})
        mock_collect_all = mocker.patch(
            "src.data_collector.DataCollector.collect_all",
            return_value={"all": (100, 500)},
        )
        mock_upsert = mocker.patch("src.db_client.DBClient.upsert_raw_data")
        from collect import main
        main()
        # collect_all called with dry_run=True
        mock_collect_all.assert_called_once_with(date=None, dry_run=True)
        mock_upsert.assert_not_called()

    def test_cli_exit_code_complete_failure(self, tmp_db, mocker):
        mocker.patch("sys.argv", ["collect.py", "--db", tmp_db])
        mocker.patch.dict("os.environ", {"FINVIZ_API_KEY": "test_key"})
        mocker.patch(
            "src.data_collector.DataCollector.collect_all",
            return_value={},
        )
        from collect import main
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_cli_exit_code_partial_failure(self, tmp_db, mocker):
        mocker.patch("sys.argv", ["collect.py", "--db", tmp_db])
        mocker.patch.dict("os.environ", {"FINVIZ_API_KEY": "test_key"})
        mocker.patch(
            "src.data_collector.DataCollector.collect_all",
            return_value={"all": (100, 500), "sec_technology": (50, 200)},
        )
        from collect import main
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2

    def test_cli_worksheet_error_exit_code(self, tmp_db, mocker):
        mocker.patch("sys.argv", [
            "collect.py", "--db", tmp_db, "--worksheet", "all",
        ])
        mocker.patch.dict("os.environ", {"FINVIZ_API_KEY": "test_key"})
        mocker.patch(
            "src.data_collector.DataCollector.collect_worksheet",
            side_effect=requests.ConnectionError("network down"),
        )
        from collect import main
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_cli_invalid_date_format(self, tmp_db, mocker):
        """Fix 5: Invalid date format should exit 1."""
        mocker.patch("sys.argv", [
            "collect.py", "--db", tmp_db, "--date", "2026-99-99",
        ])
        mocker.patch.dict("os.environ", {"FINVIZ_API_KEY": "test_key"})
        from collect import main
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
