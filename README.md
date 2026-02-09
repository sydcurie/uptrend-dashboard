# US Market Uptrend Stock Ratio Dashboard

Streamlit + Plotly dashboard for visualizing US market uptrend stock ratios from Google Sheets.

## Features

- **Full Market Overview**: Ratio time series with 10MA, Upper/Lower thresholds, and Long/Short signals
- **Sector Detail**: Individual sector analysis with signal markers
- **Sector Comparison**: Overlay multiple sector ratios for comparison
- **Auto-refresh**: 1-hour cache with manual refresh button

## Setup

### Prerequisites

- Python 3.9+
- Google Sheets service account credentials (JSON key file)
- Access to "US Market - Uptrend Stocks" spreadsheet

### Local Development

1. Clone and install dependencies:
```bash
git clone <repo-url>
cd uptrend-dashboard
pip install -r requirements.txt
```

2. Configure credentials:
```bash
cp .env.sample .env
# Edit .env and set GOOGLE_SHEETS_CREDENTIALS_PATH to your credentials JSON path
```

3. Run the dashboard:
```bash
streamlit run app.py
```

4. Run tests:
```bash
pytest tests/ -v
```

### Streamlit Cloud

1. Add your Google service account credentials as a secret in Streamlit Cloud:
   - Go to App Settings > Secrets
   - Add `gcp_service_account` with your JSON credentials content

2. Deploy from the repository.

## Project Structure

```
uptrend-dashboard/
├── .streamlit/config.toml     # Theme settings
├── src/
│   ├── sheets_client.py       # Google Sheets data fetcher
│   ├── data_processor.py      # DataFrame processing
│   └── chart_builder.py       # Plotly chart generation
├── tests/
│   ├── conftest.py            # Test fixtures
│   ├── test_sheets_client.py
│   ├── test_data_processor.py
│   └── test_chart_builder.py
├── pages/
│   ├── 1_Sector_Detail.py     # Sector detail page
│   └── 2_Sector_Comparison.py # Sector comparison page
├── app.py                     # Main page
└── requirements.txt
```

## Data Source

Reads from Google Sheets "US Market - Uptrend Stocks" with worksheets:
- `all` — Full market aggregate
- `sec_*` — 11 sector worksheets (Basic Materials, Technology, etc.)
