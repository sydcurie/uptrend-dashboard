# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

US Market Uptrend Dashboard — Streamlit ベースのセクター別上昇トレンド分析ダッシュボード。SQLite (DuckDB ではなく) をバックエンドに使用し、Excel からインポートした生データ (count, total) からインジケーターをオンザフライ計算する設計。

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

- **Single Source of Truth**: DB には生データ (count, total) のみ保存。ratio, MA, slope, trend はすべて読み込み時に `calculate_indicators()` で計算
- **Caching**: `@st.cache_data(ttl=3600)` で1時間キャッシュ。サイドバーの Refresh ボタンで手動クリア
- **UPSERT**: `INSERT OR REPLACE` による冪等なデータインポート

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

pytest + pytest-mock。テストは実 DB を使わず `tmp_path` ベースの一時 DB を使用。共通フィクスチャは `tests/conftest.py` に定義:
- `tmp_db` / `db_client` — 一時 DB
- `sample_raw_df` — 20行の合成データ
- `sample_calculated_df` — インジケーター計算済みデータ
- `sample_all_data` — 全12ワークシート分のデータ

## Development Rules

- **TDD**: コード実装時は `/tdd-developer` スキルを使用し、Red→Green→Refactor サイクルに従うこと
- **設計書同期**: コード変更後は `docs/design.md` に変更内容を反映すること。設計書とコードの乖離を防ぐ

## Adding New Features

**New indicator**: `indicator_calculator.py` に計算追加 → `calculate_indicators()` にカラム追加 → `chart_builder.py` で可視化 → テスト追加

**New page**: `pages/N_Name.py` を作成、既存ページのパターンに従う (`load_data` キャッシュ、サイドバー日付フィルター)
