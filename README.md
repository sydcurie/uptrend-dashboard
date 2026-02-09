# US Market Uptrend Stock Ratio Dashboard

Streamlit + Plotly dashboard for visualizing US market uptrend stock ratios. Data is collected from Finviz Elite and stored in SQLite.

**Live App**: https://uptrend-dashboard.streamlit.app/

## Features

- **Full Market Overview**: Ratio time series with 10MA, Upper/Lower thresholds, peak/trough markers
- **Sector Detail**: Individual sector analysis with trend signals
- **Sector Comparison**: Overlay multiple sector ratios (10MA smoothed) with threshold annotations
- **Auto-refresh**: 1-hour cache with manual refresh button
- **Self-Contained Data Collection**: Finviz Elite CSV scraper with cron-ready CLI

## Setup

### Prerequisites

- Python 3.9+
- Finviz Elite API key (for data collection)

### Installation

```bash
git clone https://github.com/tradermonty/uptrend-dashboard.git
cd uptrend-dashboard
pip install -r requirements.txt
```

### Configuration

```bash
cp .env.sample .env
# Edit .env and set FINVIZ_API_KEY
```

### Data Collection

```bash
# Collect all sectors (writes to SQLite)
python collect.py

# Dry run (fetch without writing to DB)
python collect.py --dry-run

# Specific date
python collect.py --date 2026-02-07

# Single worksheet
python collect.py --worksheet sec_technology

# Import from Excel (legacy data migration)
python import_excel.py path/to/export.xlsx
```

### Run Dashboard

```bash
streamlit run app.py
```

### Run Tests

```bash
pytest tests/ -v
```

## Project Structure

```
uptrend-dashboard/
├── .streamlit/config.toml          # Theme settings
├── src/
│   ├── constants.py                # Sectors, thresholds, shared constants
│   ├── db_client.py                # SQLite CRUD (UPSERT via INSERT OR REPLACE)
│   ├── indicator_calculator.py     # Ratio, 10MA, slope, trend, peak/trough
│   ├── data_processor.py           # Status aggregation, sector summaries
│   ├── data_collector.py           # Finviz Elite CSV scraper
│   └── chart_builder.py            # Plotly chart generation
├── tests/
│   ├── conftest.py                 # Shared fixtures (tmp_db, sample data)
│   ├── test_db_client.py
│   ├── test_indicator_calculator.py
│   ├── test_data_processor.py
│   ├── test_chart_builder.py
│   ├── test_data_collector.py
│   ├── test_import_excel.py
│   └── test_integration.py
├── pages/
│   ├── 1_Sector_Detail.py          # Sector detail page
│   └── 2_Sector_Comparison.py      # Sector comparison page
├── app.py                          # Main page
├── collect.py                      # Data collection CLI (cron-ready)
├── import_excel.py                 # Excel import tool
├── data/uptrend.db                 # SQLite database
└── docs/design.md                  # Design document
```

## Uptrend Definition

A stock is classified as "uptrend" when it meets **all** of the following conditions on Finviz screener:

| Condition | Description |
|-----------|-------------|
| Price > $10 | Penny stocks excluded |
| Avg Volume > 100K | Sufficient liquidity |
| Market Cap > $50M | Micro-cap and above |
| Price > SMA20 | Short-term uptrend |
| Price > SMA200 | Long-term uptrend |
| SMA50 > SMA200 | Golden cross (bullish structure) |
| 52W High/Low > 30% above Low | Recovering from bottom |
| 4-Week Performance: Up | Recent momentum positive |

The **uptrend ratio** = (stocks meeting all conditions) / (stocks meeting base filters only: price, volume, market cap). This ratio is tracked daily per sector to gauge market breadth.

## Data Source

Finviz Elite CSV export API. Collects uptrend count and total count for:
- `all` -- Full market aggregate
- `sec_*` -- 11 sector worksheets (Basic Materials, Technology, Financial, etc.)

Data is stored in SQLite (`data/uptrend.db`) with raw counts (count, total). Indicators (ratio, 10MA, slope, trend) are calculated on-the-fly at read time.
