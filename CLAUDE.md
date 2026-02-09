# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

US Market Uptrend Dashboard — A Streamlit-based sector-level uptrend analysis dashboard. Uses SQLite (not DuckDB) as the backend, computing indicators on-the-fly from raw data (count, total) imported from Excel.

## Commands

```bash
# Run dashboard
streamlit run app.py

# Run all tests
pytest tests/ -v

# Run single test file
pytest tests/test_indicator_calculator.py -v

# Run single test
pytest tests/test_indicator_calculator.py::TestCalculateIndicators::test_calculate_indicators_full -v

# Import data from Excel
python import_excel.py path/to/export.xlsx
python import_excel.py path/to/export.xlsx --dry-run    # preview only
python import_excel.py path/to/export.xlsx --sheet all   # specific sheets
```

## Architecture

```
Presentation (app.py, pages/)
    ↓
Chart Layer (src/chart_builder.py) — Plotly figures with color-coded trends
    ↓
Processing (src/data_processor.py) — status aggregation, sector summaries
    ↓
Calculation (src/indicator_calculator.py) — ratio, 10MA, slope, trend, peak/trough
    ↓
Data Access (src/db_client.py) — SQLite CRUD, UPSERT via INSERT OR REPLACE
    ↓
Storage (data/uptrend.db) — uptrend_raw table, PK: (date, worksheet)
```

### Key Design Decisions

- **Single Source of Truth**: Only raw data (count, total) is stored in the DB. ratio, MA, slope, and trend are all computed at read time by `calculate_indicators()`
- **Caching**: `@st.cache_data(ttl=3600)` caches data for 1 hour. Manual clear via the sidebar Refresh button
- **UPSERT**: Idempotent data import via `INSERT OR REPLACE`

### DB Schema

```sql
uptrend_raw (date TEXT, worksheet TEXT, count INTEGER, total INTEGER)
-- PK: (date, worksheet)
-- worksheets: 'all' + 11 sectors (sec_technology, sec_financial, etc.)
-- 12 rows/day, ~4,720 rows current
```

### Indicator Thresholds

- Upper (Overbought): 0.37
- Lower (Oversold): 0.097
- MA period: 10
- Peak detection: scipy.signal.find_peaks (distance=20, prominence=0.015)

### Multi-Page Structure

Streamlit auto-discovers `pages/` directory:
- `app.py` — Full market overview
- `pages/1_Sector_Detail.py` — Individual sector deep dive
- `pages/2_Sector_Comparison.py` — Multi-sector overlay comparison

## Testing

pytest + pytest-mock. Tests use `tmp_path`-based temporary DBs instead of the real DB. Shared fixtures are defined in `tests/conftest.py`:
- `tmp_db` / `db_client` — temporary DB
- `sample_raw_df` — 20-row synthetic data
- `sample_calculated_df` — DataFrame with indicators pre-calculated
- `sample_all_data` — data for all 12 worksheets

## Development Rules

- **TDD**: Use the `/tdd-developer` skill when implementing code, following the Red→Green→Refactor cycle
- **Design Doc Sync**: After code changes, reflect the updates in `docs/design.md` to prevent drift between design docs and code

## Adding New Features

**New indicator**: Add calculation to `indicator_calculator.py` → add column to `calculate_indicators()` → visualize in `chart_builder.py` → add tests

**New page**: Create `pages/N_Name.py`, following existing page patterns (`load_data` cache, sidebar date filter)
