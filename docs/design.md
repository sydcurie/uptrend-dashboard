# US Market Uptrend Stock Ratio Dashboard 設計書

| 項目 | 内容 |
|------|------|
| ドキュメント種別 | ソフトウェア設計書 |
| プロジェクト名 | uptrend-dashboard |
| 作成日 | 2026-02-08 |
| 改訂日 | 2026-02-08 |
| ステータス | v2.3 Sector Comparison チャート改善 |

---

## 改訂履歴

| 日付 | 版 | 内容 |
|------|-----|------|
| 2026-02-08 | v1 | 初版（Google Sheets ベース） |
| 2026-02-08 | v2 | データストアを Google Sheets → SQLite に移行。派生データ計算を Python に移植。Excelインポート機能を追加 |
| 2026-02-08 | v2.1 | シグナルロジック (Long/Short Entry/Exit) を削除。チャートのトレンド表示を緑/赤/灰色のカラーコーディングに変更 |
| 2026-02-08 | v2.2 | コードレビュー指摘事項修正。DB接続管理改善、定数一元化、空データハンドリング、ロギング追加、テスト改善 |
| 2026-02-08 | v2.3 | Sector Comparison チャート改善。10MA表示、閾値線、カスタムパレット、最新値アノテーション、Y軸%表記、凡例ソート |

### v2.3 主要変更点（Sector Comparison チャート改善）

- **MA線をメインに表示**: `build_sector_comparison_chart()` に `use_ma` パラメータ追加。デフォルトで `ma_10`（10日移動平均）を表示し、ノイズを大幅削減
- **閾値線追加**: Upper (37%) / Lower (9.7%) を破線で表示。チャートに文脈を付与
- **11色カスタムパレット**: `SECTOR_PALETTE` を定義。Plotly デフォルトの類似色問題を解消
- **最新値アノテーション**: 各線の右端にセクター名と現在値（%表記）をラベル表示
- **Y軸パーセント表記**: `tickformat=".0%"` で 0.37 → 37% に変換
- **凡例ソート**: 最新値の降順で凡例を自動ソート。現在の順位が一目でわかる
- **表示切替トグル**: Sector Comparison ページに「Smoothed (10MA)」/「Raw Ratio」のラジオボタン追加

### v2.2 主要変更点（コードレビュー修正）

- **DB接続管理**: `_connection()` コンテキストマネージャ導入。全メソッドで `with` パターン使用。`upsert_bulk()` を `executemany()` + 単一トランザクションに変更。例外時 rollback 保証
- **定数一元化**: `src/constants.py` 新設。`SECTORS`, `VALID_WORKSHEETS`, `SECTOR_DISPLAY_NAMES` を集約。4箇所の重複定義を排除
- **ロギング**: 全ソースモジュールに `logging.getLogger(__name__)` を設定
- **空データハンドリング**: `get_current_status()`, `build_sector_summary()`, `calculate_indicators()` に空 DataFrame ガード追加
- **Worksheet バリデーション**: `upsert_raw_data()`, `upsert_bulk()` で `VALID_WORKSHEETS` チェック
- **NaN ハンドリング**: `_calc_ratio()` で count/total の NaN を `fillna(0)` で処理
- **MarketStatus dataclass**: `get_current_status()` の戻り値を dict から `MarketStatus` dataclass に変更（dict 互換性維持）
- **日付フィルターヘルパー**: `filter_by_date_range()` を抽出し `app.py` / `pages/*.py` で共有
- **チャート関数分割**: `build_ratio_chart()` を 5 つの小関数に分割
- **マジックナンバー定数化**: チャート高さ、閾値等を `src/constants.py` に集約
- **Public API 整備**: `_sector_display_name` → `get_sector_display_name` にリネーム
- **テスト改善**: private関数依存解消、統合テスト追加（Excel → DB → 計算 → チャート）

### v2 主要変更点

- **データストア**: Google Sheets → SQLite (`data/uptrend.db`)
- **データアクセス層**: `sheets_client.py` → `db_client.py`
- **派生データ計算**: Google Sheets 数式 → `indicator_calculator.py`（Python/pandas で計算）
- **データ移行**: Excel ファイルからの一括インポートツール `import_excel.py` を追加
- **依存パッケージ**: `gspread`, `oauth2client` を削除。`openpyxl` を追加
- **stocktrading 側変更**: 書き込み先を Google Sheets → SQLite に変更（将来対応）

---

## 1. 概要

### 1.1 目的

米国市場における上昇トレンド銘柄比率（Uptrend Stock Ratio）のデータを可視化するインタラクティブな Web ダッシュボードを提供する。

データは SQLite に格納された元データ（Count, Total）を読み取り、派生指標（Ratio, 10MA, Slope, Trend）を Python で計算し、トレンド状態を緑（上昇）/赤（下降）/灰色（データ不足）のカラーコーディングで可視化する。

### 1.2 スコープ

- SQLite からの元データ（Count, Total）読み取り
- 派生指標の Python 計算（Ratio, 10MA, Slope, Trend）
- 全市場（all）および 11 セクターの Ratio 時系列可視化
- トレンド状態の緑/赤/灰色カラーコーディング表示
- セクター間比較チャート
- Excel ファイルからの過去データインポート

### 1.3 スコープ外

- Finviz / Alpaca API への直接アクセス
- トレード執行・ポジション管理
- ユーザー認証・アクセス制御
- stocktrading 側の書き込みロジック変更（将来対応として記載のみ）

---

## 2. システムアーキテクチャ

### 2.1 全体構成

```
┌───────────────────────────────────────────────────────────────┐
│                      Streamlit App                             │
│                                                               │
│  ┌──────────┐   ┌──────────────────┐   ┌──────────────────┐  │
│  │ app.py   │   │ 1_Sector_        │   │ 2_Sector_        │  │
│  │ (Main)   │   │  Detail.py       │   │  Comparison.py   │  │
│  └────┬─────┘   └──────┬───────────┘   └──────┬───────────┘  │
│       │                │                       │              │
│       └────────────────┼───────────────────────┘              │
│                        │                                      │
│              ┌─────────▼────────────┐                         │
│              │  chart_builder.py    │  ← Plotly Figure 生成   │
│              └─────────┬────────────┘                         │
│                        │                                      │
│              ┌─────────▼────────────┐                         │
│              │  data_processor.py   │  ← ステータス集計       │
│              └─────────┬────────────┘                         │
│                        │                                      │
│              ┌─────────▼────────────┐                         │
│              │indicator_calculator  │  ← 派生指標計算         │
│              │         .py         │     (Ratio, 10MA, etc.) │
│              └─────────┬────────────┘                         │
│                        │                                      │
│              ┌─────────▼────────────┐                         │
│              │  db_client.py        │  ← SQLite 読み書き      │
│              └─────────┬────────────┘                         │
│                        │                                      │
└────────────────────────┼──────────────────────────────────────┘
                         │ sqlite3
                         ▼
              ┌────────────────────────┐
              │  data/uptrend.db       │
              │  (SQLite)              │
              └────────────────────────┘

┌──────────────────────┐
│  import_excel.py     │ ← Excel → SQLite 一括インポート
│  (CLI ツール)        │
└──────┬───────────────┘
       │ pd.read_excel() + INSERT
       ▼
  data/uptrend.db
```

### 2.2 レイヤー構成

| レイヤー | ファイル | 責務 |
|----------|----------|------|
| Presentation | `app.py`, `pages/*.py` | Streamlit UI、ユーザーインタラクション |
| Chart | `src/chart_builder.py` | Plotly Figure オブジェクト生成 |
| Processing | `src/data_processor.py` | ステータス集計、セクターサマリー構築 |
| Calculation | `src/indicator_calculator.py` | 派生指標計算（Ratio, 10MA, Slope, Trend） |
| Data Access | `src/db_client.py` | SQLite 読み書き、テーブル初期化 |
| CLI Tools | `import_excel.py` | Excel からの過去データインポート |

### 2.3 データフロー

```
[ダッシュボード表示時]

SQLite (uptrend_raw: date, worksheet, count, total)
  │
  │ db_client.fetch_raw_data(worksheet)
  ▼
pd.DataFrame (date, count, total)          ← 元データのみ
  │
  │ indicator_calculator.calculate_indicators(df)
  ▼
pd.DataFrame (+ ratio, ma_10, slope,       ← 派生指標を追加
               trend_up, trend_down,
               upper, lower)
  │
  │ data_processor / chart_builder
  ▼
st.plotly_chart()                           ← ブラウザ描画


[Excel インポート時]

Excel ファイル (過去の Google Sheets エクスポート)
  │
  │ import_excel.py → pd.read_excel()
  ▼
date, worksheet(=シート名), count, total を抽出
  │
  │ db_client.upsert_raw_data()
  ▼
SQLite uptrend_raw テーブル
```

---

## 3. データ設計

### 3.1 データソース

| 属性 | 値 |
|------|-----|
| ストレージ | SQLite |
| ファイルパス | `data/uptrend.db` |
| アクセスモード | ダッシュボードからは読み取り専用 |
| 保存データ | 元データ（Count, Total）のみ |
| 派生データ | Python で読み取り時に計算（DB には保存しない） |

### 3.2 設計方針: 元データのみ保存

**理由:**

1. **Single Source of Truth** — Count/Total が唯一の真のデータ。Ratio 等は常にそこから導出
2. **計算ロジック変更が即座に反映** — MA 期間や閾値を変えたい場合、コード変更だけで済む（DB 再計算不要）
3. **DB サイズ最小** — 4 カラムのみ。10 年運用でも約 1 MB 以下
4. **データ整合性** — 派生データの不整合（計算ロジック変更時の旧データ残存）が起こらない

### 3.3 SQLite テーブル定義

```sql
CREATE TABLE IF NOT EXISTS uptrend_raw (
    date      TEXT    NOT NULL,   -- 'YYYY-MM-DD' (ISO 8601)
    worksheet TEXT    NOT NULL,   -- 'all', 'sec_technology', etc.
    count     INTEGER NOT NULL,   -- uptrend stock count
    total     INTEGER NOT NULL,   -- total stock count
    PRIMARY KEY (date, worksheet)
);

CREATE INDEX IF NOT EXISTS idx_uptrend_raw_worksheet
    ON uptrend_raw (worksheet, date);
```

**テーブル: `uptrend_raw`**

| カラム | 型 | 制約 | 説明 |
|--------|-----|------|------|
| date | TEXT | NOT NULL, PK | 日付 (YYYY-MM-DD) |
| worksheet | TEXT | NOT NULL, PK | カテゴリ名 |
| count | INTEGER | NOT NULL | 上昇トレンド銘柄数 |
| total | INTEGER | NOT NULL | 全体銘柄数 |

**複合主キー:** `(date, worksheet)` — 同一日・同一カテゴリの重複を防止
**インデックス:** `(worksheet, date)` — カテゴリ別の時系列クエリを高速化

### 3.4 worksheet 値の一覧

| 値 | 内容 | データ開始日 | 概算行数 |
|----|------|-------------|---------|
| `all` | 全市場集計 | 2023-08-11 | ~650 |
| `sec_basicmaterials` | Basic Materials | 2024-07-21 | ~370 |
| `sec_communicationservices` | Communication Services | 2024-07-21 | ~370 |
| `sec_consumercyclical` | Consumer Cyclical | 2024-07-21 | ~370 |
| `sec_consumerdefensive` | Consumer Defensive | 2024-07-21 | ~370 |
| `sec_energy` | Energy | 2024-07-21 | ~370 |
| `sec_financial` | Financial | 2024-07-21 | ~370 |
| `sec_healthcare` | Healthcare | 2024-07-21 | ~370 |
| `sec_industrials` | Industrials | 2024-07-21 | ~370 |
| `sec_realestate` | Real Estate | 2024-07-21 | ~370 |
| `sec_technology` | Technology | 2024-07-21 | ~370 |
| `sec_utilities` | Utilities | 2024-07-21 | ~370 |

### 3.5 データ量見積

| 項目 | 値 |
|------|-----|
| 現在の総行数 | ~4,720 |
| 1日あたり増加行数 | 12（1 all + 11 セクター） |
| 年間増加行数 | ~3,024（252 営業日） |
| 10 年後の総行数 | ~35,000 |
| 10 年後の DB サイズ | ~1 MB |

### 3.6 派生データ定義

以下のデータは DB に保存せず、`indicator_calculator.py` が読み取り時に計算する。

| カラム名 | 計算式 | 説明 |
|----------|--------|------|
| ratio | `count / total` | 上昇トレンド銘柄比率 (0.0~1.0) |
| ma_10 | `ratio.rolling(10).mean()` | Ratio の 10 日単純移動平均 |
| slope | `ma_10.diff()` | 10MA の 1 日変化量 |
| trend_up | `ratio` (slope > 0 の場合) / NaN | 上昇トレンド中の Ratio 値 |
| trend_down | `ratio` (slope <= 0 の場合) / NaN | 下降トレンド中の Ratio 値 |
| upper | 定数 `0.37` | 買われすぎ閾値 |
| lower | 定数 `0.097` | 売られすぎ閾値 |

### 3.7 ステータス判定ロジック

```
Trend:
  slope > 0 → "up"（緑）
  slope <= 0 → "down"（赤）
  slope が NaN（データ不足）→ "neutral"（灰色）

Status:
  ratio > upper (0.37) → "Overbought"
  ratio < lower (0.097) → "Oversold"
  それ以外 → "Normal"
```

### 3.8 チャートカラーコーディング

Ratio の時系列ラインをトレンド状態に応じてセグメントごとに色分けする。

| トレンド状態 | 条件 | 色 | カラーコード |
|------------|------|-----|------------|
| 上昇トレンド | slope > 0 | 緑 | `#00cc96` |
| 下降トレンド | slope <= 0 | 赤 | `#ef553b` |
| データ不足 | slope が NaN（MA 計算期間未満） | 灰色 | `#636efa` |

実装方法: Plotly の `Scatter` トレースを連続する同一トレンド区間ごとに分割し、各セグメントに対応する色を設定する。セグメント間の途切れを防ぐため、隣接セグメントの境界点を重複させる。

---

## 4. モジュール設計

### 4.0 constants.py — 定数定義モジュール（v2.2 新規）

全モジュールで使用する定数を一元管理する。

| 定数 | 説明 |
|------|------|
| `SECTORS` | 11 セクターのワークシート名リスト |
| `VALID_WORKSHEETS` | `["all"] + SECTORS` |
| `SECTOR_DISPLAY_NAMES` | ワークシートサフィックス → 表示名のマッピング |
| `UPPER_THRESHOLD` | 買われすぎ閾値 (0.37) |
| `LOWER_THRESHOLD` | 売られすぎ閾値 (0.097) |
| `MA_PERIOD` | 移動平均期間 (10) |
| `CHART_HEIGHT_*` | チャート高さ定数 |

### 4.1 db_client.py — データアクセス層

**クラス: `DBClient`**

| メソッド | シグネチャ | 説明 |
|----------|-----------|------|
| `__init__` | `(db_path: str = "data/uptrend.db")` | DB 接続、テーブル自動作成 |
| `_connection` | `() -> ContextManager` | DB 接続コンテキストマネージャ（自動 commit/rollback/close） |
| `_init_tables` | `() -> None` | CREATE TABLE IF NOT EXISTS 実行 |
| `upsert_raw_data` | `(date, worksheet, count, total) -> None` | 1 行 UPSERT (INSERT OR REPLACE)、worksheet バリデーション付き |
| `upsert_bulk` | `(df: DataFrame) -> None` | DataFrame 一括 UPSERT（executemany + 単一トランザクション） |
| `fetch_raw_data` | `(worksheet: str) -> DataFrame` | 指定カテゴリの全データ取得 |
| `fetch_all_raw_data` | `() -> Dict[str, DataFrame]` | 全 12 カテゴリ一括取得 |
| `get_worksheets` | `() -> List[str]` | 登録済みカテゴリ名一覧 |
| `get_date_range` | `(worksheet: str) -> Tuple[str, str]` | 指定カテゴリの日付範囲 |

**DB接続管理パターン（v2.2）:**

```python
@contextmanager
def _connection(self):
    conn = sqlite3.connect(self.db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

全 DB 操作メソッドは `with self._connection() as conn:` パターンを使用。接続リーク防止とトランザクション安全性を保証。

**UPSERT ステートメント:**

```sql
INSERT OR REPLACE INTO uptrend_raw (date, worksheet, count, total)
VALUES (?, ?, ?, ?)
```

**fetch_raw_data クエリ:**

```sql
SELECT date, count, total
FROM uptrend_raw
WHERE worksheet = ?
ORDER BY date ASC
```

**キャッシュ:**

| 関数 | TTL | 説明 |
|------|-----|------|
| `load_all_data()` | 3600 秒 | モジュールレベルのキャッシュラッパー。`fetch_all_raw_data()` + `calculate_indicators()` をまとめて実行 |

### 4.2 indicator_calculator.py — 派生指標計算層（新規）

| 関数 | シグネチャ | 説明 |
|------|-----------|------|
| `calculate_indicators` | `(df: DataFrame, config: IndicatorConfig = None) -> DataFrame` | 元データ DataFrame に全派生指標カラムを追加 |
| `_calc_ratio` | `(df) -> Series` | count / total（NaN は `fillna(0)` で処理） |
| `_calc_ma` | `(ratio, period) -> Series` | 移動平均 |
| `_calc_slope` | `(ma) -> Series` | MA の 1 日変化量 |
| `_calc_trend` | `(ratio, slope) -> (Series, Series)` | trend_up, trend_down |

**IndicatorConfig:**

```python
@dataclass
class IndicatorConfig:
    ma_period: int = 10           # 移動平均期間
    upper_threshold: float = 0.37 # 買われすぎ閾値
    lower_threshold: float = 0.097 # 売られすぎ閾値
```

設定値をクラスに集約することで、閾値や MA 期間の変更を 1 箇所で管理可能にする。

**入力 DataFrame（db_client から取得）:**

| カラム | 型 |
|--------|-----|
| date | datetime64 |
| count | int |
| total | int |

**出力 DataFrame（calculate_indicators 後）:**

| カラム | 型 | 計算元 |
|--------|-----|--------|
| date | datetime64 | そのまま |
| count | int | そのまま |
| total | int | そのまま |
| ratio | float | count / total |
| ma_10 | float | ratio.rolling(10).mean() |
| slope | float | ma_10.diff() |
| trend_up | float or NaN | ratio if slope > 0 |
| trend_down | float or NaN | ratio if slope <= 0 |
| upper | float | 定数 0.37 |
| lower | float | 定数 0.097 |

### 4.3 data_processor.py — ステータス集計層

v1 から以下の責務変更:

| v1 の責務 | v2 での変更 |
|-----------|-----------|
| 型変換・クリーニング (`process_worksheet_data`) | **削除** — DB から取得時点で型が確定 |
| `_clean_numeric` ヘルパー | **削除** — 不要 |
| `get_current_status` | **維持** — 最新行のステータス抽出 |
| `build_sector_summary` | **維持** — セクターサマリー構築 |
| `_sector_display_name` | **維持** — カテゴリ名→表示名変換 |

**v2.2 の関数一覧:**

| 関数 | シグネチャ | 説明 |
|------|-----------|------|
| `get_current_status` | `(df: DataFrame) -> MarketStatus` | 最新行のステータス抽出（空 DF 対応） |
| `build_sector_summary` | `(all_data: Dict) -> DataFrame` | 全セクターサマリー構築（空データ対応） |
| `get_sector_display_name` | `(name: str) -> str` | カテゴリ名→表示名変換（public API） |
| `filter_by_date_range` | `(df, start, end) -> DataFrame` | 日付範囲フィルター |

**MarketStatus dataclass（v2.2 新規）:**

```python
@dataclass
class MarketStatus:
    date: str
    ratio: float
    ratio_10ma: Optional[float]
    trend: str
    slope: float
    is_overbought: bool
    is_oversold: bool
```

dict 互換の `__getitem__`, `__contains__`, `keys()` メソッドを提供。既存コードを破壊せずに型安全性を向上。

**get_current_status 戻り値（v1 から変更なし）:**

```python
{
    "date": str,           # "2024-01-08"
    "ratio": float,        # 0.29
    "ratio_10ma": float,   # 0.288
    "trend": str,          # "up" | "down"
    "slope": float,        # 0.001
    "is_overbought": bool, # False
    "is_oversold": bool,   # False
}
```

> **注記:** `get_current_status` が参照するカラム名は v2 で変更。`"10MA ratio"` → `"ma_10"`, `"Trend Up ratio"` → `"trend_up"` 等。indicator_calculator の出力カラム名に合わせる。

**build_sector_summary 出力カラム（v1 から変更なし）:**

| カラム | 型 | 説明 |
|--------|-----|------|
| Sector | str | 表示名 |
| Ratio | float | 最新 ratio |
| 10MA | float | 最新 ma_10 |
| Trend | str | "Up" / "Down" |
| Slope | float | 最新 slope |
| Status | str | "Overbought" / "Oversold" / "Normal" |

### 4.4 chart_builder.py — チャート生成層

v2.1 でシグナルマーカーを廃止し、Ratio ラインのカラーコーディングに変更。v2.2 で `build_ratio_chart` を 5 つのヘルパー関数に分割。

**Public 関数:**

| 関数 | シグネチャ | 説明 |
|------|-----------|------|
| `build_ratio_chart` | `(df, title) -> go.Figure` | Ratio 時系列チャート（下記ヘルパーを呼び出し） |
| `build_sector_summary_chart` | `(summary_df) -> go.Figure` | セクター横棒グラフ |
| `build_sector_comparison_chart` | `(all_data, selected, use_ma=True) -> go.Figure` | セクター比較オーバーレイ（v2.3 改修） |

**build_ratio_chart 内部ヘルパー（v2.2 分割）:**

| 関数 | 説明 |
|------|------|
| `_add_ratio_segments(fig, df)` | トレンド状態別にカラーコーディングされた Ratio セグメントを追加 |
| `_add_moving_average(fig, df)` | 10MA ラインを追加 |
| `_add_peaks_and_troughs(fig, df)` | 10MA のピーク・トラフマーカーを追加 |
| `_add_threshold_lines(fig, df)` | Upper/Lower 閾値線を追加 |
| `_apply_chart_layout(fig, df, title)` | レイアウト設定（タイトル、軸、高さ等）を適用 |

**カラム名マッピング（v1 → v2）:**

| v1（Google Sheets 由来） | v2（indicator_calculator 出力） |
|--------------------------|-------------------------------|
| Ratio | ratio |
| 10MA ratio | ma_10 |
| Trend Up ratio | trend_up |
| Trend Down ratio | trend_down |
| Upper ratio | upper |
| Lower ratio | lower |
| Slope | slope |
**build_ratio_chart トレース構成（v2.1: シグナルマーカー廃止、カラーセグメント化）:**

| # | トレース | 種類 | 色 | スタイル |
|---|---------|------|-----|---------|
| 1~N | Ratio (セグメント) | Scatter line | 緑 `#00cc96` / 赤 `#ef553b` / 灰 `#636efa` | 実線 width=2、トレンド状態で色分け |
| N+1 | 10MA | Scatter line | `#ff7f0e` (オレンジ) | 破線 width=1.5 |
| N+2 | Upper | Scatter line | `#d62728` (赤) | 点線 width=1 |
| N+3 | Lower | Scatter line | `#2ca02c` (緑) | 点線 width=1 |

> Ratio ラインは同一トレンド状態が続く区間ごとにセグメント分割。各セグメントの色がトレンド方向（上昇=緑、下降=赤、データ不足=灰色）を表す。凡例にはセグメントごとではなく "Ratio (Up)" / "Ratio (Down)" のみ表示し、`showlegend=False` で重複凡例を抑制する。

**build_sector_comparison_chart トレース構成（v2.3 改修）:**

| # | トレース | 種類 | 色 | スタイル |
|---|---------|------|-----|---------|
| 1~11 | セクター線 (ma_10 or ratio) | Scatter line | `SECTOR_PALETTE` の 11 色 | 実線 width=2、最新値降順で凡例ソート |
| 12 | Upper (0.37) | hline + legend trace | `#d62728` (赤) | 破線 width=1 |
| 13 | Lower (0.097) | hline + legend trace | `#2ca02c` (緑) | 破線 width=1 |

`SECTOR_PALETTE`（chart_builder.py に定義）:

| Index | 色 | カラーコード |
|-------|-----|------------|
| 0 | Blue | `#1f77b4` |
| 1 | Orange | `#ff7f0e` |
| 2 | Green | `#2ca02c` |
| 3 | Red | `#d62728` |
| 4 | Purple | `#9467bd` |
| 5 | Brown | `#8c564b` |
| 6 | Pink | `#e377c2` |
| 7 | Gray | `#7f7f7f` |
| 8 | Olive | `#bcbd22` |
| 9 | Cyan | `#17becf` |
| 10 | Dark Orange | `#ff6600` |

> `use_ma=True`（デフォルト）では `ma_10` カラムをプロット。ノイズを削減し滑らかな線を表示。`use_ma=False` では生 `ratio` を表示。各セクター線の右端には `セクター名 XX%` のアノテーションを表示。Y 軸は `tickformat=".0%"` でパーセント表記。

### 4.5 import_excel.py — Excel インポートツール（新規）

**用途:** Google Sheets からエクスポートした Excel ファイルの過去データを SQLite に取り込む。

**CLI インターフェース:**

```bash
# 単一ファイル（全シート読み込み）
python import_excel.py data/export.xlsx

# 特定シートのみ
python import_excel.py data/export.xlsx --sheet all --sheet sec_technology

# DB パス指定
python import_excel.py data/export.xlsx --db data/uptrend.db

# ドライラン（INSERT せず件数のみ表示）
python import_excel.py data/export.xlsx --dry-run
```

**処理フロー:**

```
1. Excel ファイルを pd.read_excel(sheet_name=None) で全シート読み込み
   → Dict[str, DataFrame] を取得

2. 各シートについて:
   a. シート名が有効な worksheet 値か検証
   b. Date, Count, Total カラムを抽出
   c. Date を YYYY-MM-DD 形式に変換
   d. 空行・無効行を除去

3. db_client.upsert_bulk(df) で SQLite に一括書き込み
   → INSERT OR REPLACE で既存データは上書き

4. 結果レポート表示:
   - シートごとのインポート行数
   - スキップ行数（日付なし等）
   - 重複上書き行数
```

**Excel ファイルの想定フォーマット:**

Google Sheets からダウンロードした `.xlsx` ファイル。各シートに以下のカラムを含む:

| カラム | 必須 | 説明 |
|--------|------|------|
| Date | Yes | 日付（M/D/YYYY 等、pandas が解釈可能な形式） |
| Count | Yes | 上昇トレンド銘柄数 |
| Total | Yes | 全体銘柄数 |
| その他 | No | 無視される（Ratio, 10MA 等の計算済み列） |

---

## 5. 画面設計

v1 から画面構成は変更なし。データソースが変わるだけで UI は同一。

### 5.1 メインページ (app.py)

```
┌─────────────────────────────────────────────────────────────┐
│ Sidebar                │ US Market Uptrend Stock Ratio       │
│ ┌───────────────────┐  │                                     │
│ │ [Settings]        │  │ ┌──────┐┌──────┐┌──────┐┌────────┐│
│ │                   │  │ │Ratio ││ 10MA ││Trend ││ Status ││
│ │ [Refresh Data]    │  │ │29.0% ││28.8% ││ Up   ││ Normal ││
│ │                   │  │ └──────┘└──────┘└──────┘└────────┘│
│ │ Date Range:       │  │ Last updated: 2024-01-08            │
│ │ [2023-08-11]      │  │                                     │
│ │ [2024-01-08]      │  │ Full Market Ratio                   │
│ │                   │  │ ┌─────────────────────────────────┐ │
│ └───────────────────┘  │ │    [Ratio Chart]                │ │
│                        │ └─────────────────────────────────┘ │
│                        │                                     │
│                        │ Sector Summary                      │
│                        │ ┌───────────────────┐┌────────────┐│
│                        │ │ [Horizontal Bar]  ││ [Table]    ││
│                        │ │  Chart            ││ Sector ... ││
│                        │ └───────────────────┘└────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Sector Detail ページ (pages/1_Sector_Detail.py)

```
┌─────────────────────────────────────────────────────────────┐
│ Sector Detail                                               │
│                                                             │
│ Select Sector: [Technology ▼]                               │
│                                                             │
│ ┌──────┐┌──────┐┌──────┐┌──────┐┌────────┐                │
│ │Ratio ││ 10MA ││Trend ││Slope ││ Status │                │
│ └──────┘└──────┘└──────┘└──────┘└────────┘                │
│                                                             │
│ Date Range: [start] ~ [end]                                 │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │    [Ratio Chart — 緑/赤/灰色トレンドカラー]             │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 Sector Comparison ページ (pages/2_Sector_Comparison.py)

```
┌─────────────────────────────────────────────────────────────┐
│ Sector Comparison                                           │
│                                                             │
│ Select Sectors: [x] Basic Materials  [x] Technology  ...    │
│                                                             │
│ Date Range: [start] ~ [end]                                 │
│                                                             │
│ Display Mode: (●) Smoothed (10MA)  ( ) Raw Ratio            │
│                                                             │
│ ┌─────────────────────────────────────────────────────┬───┐ │
│ │                                          Upper 37%  │   │ │
│ │    [Multi-line Overlay Chart]            ─ ─ ─ ─ ─  │ L │ │
│ │    - 11色カスタムパレット                             │ e │ │
│ │    - MA10 or Raw Ratio 切替                          │ g │ │
│ │    - Y軸: 0% ~ 60%                      Lower 10%   │ e │ │
│ │                                          ─ ─ ─ ─ ─  │ n │ │
│ │                              Tech 42% ←(最新値ラベル)│ d │ │
│ │                          Financial 38%               │   │ │
│ └─────────────────────────────────────────────────────┴───┘ │
└─────────────────────────────────────────────────────────────┘
```

v2.3 改修: 表示モードラジオボタン、10MA/Raw切替、閾値破線、最新値アノテーション、Y軸%表記、凡例ソート（最新値降順）。

---

## 6. 非機能要件

### 6.1 パフォーマンス

| 項目 | v1 (Google Sheets) | v2 (SQLite) |
|------|-------------------|-------------|
| 初回ロード | 20~30 秒 | < 1 秒（ローカル DB） |
| キャッシュ TTL | 1 時間 | 1 時間（同一） |
| キャッシュヒット | ほぼ即時 | ほぼ即時 |
| API レート制限 | 1 秒/ワークシート | 不要 |
| 派生指標計算 | 不要（シート数式） | ~数ミリ秒（35,000 行でも） |

### 6.2 信頼性

| 項目 | 仕様 |
|------|------|
| DB ファイル破損対策 | SQLite の WAL モードを検討（並行読み取り改善） |
| データ不在時 | `st.error` / `st.warning` で表示 |
| UPSERT による冪等性 | 同一 (date, worksheet) の再投入は上書き |

### 6.3 デプロイ

| 環境 | DB パス | 設定 |
|------|--------|------|
| ローカル | `data/uptrend.db` | `.env` で `DB_PATH` を指定可 |
| Streamlit Cloud | `/mount/data/uptrend.db` 等 | 永続ストレージ要検討 |

> **注記:** Streamlit Cloud はファイルシステムが揮発性のため、SQLite ファイルの永続化には追加対応が必要（git に DB を含める、外部ストレージ連携等）。ローカル運用を主用途とする。

### 6.4 UI テーマ（v1 から変更なし）

| プロパティ | 値 |
|-----------|-----|
| primaryColor | `#1f77b4` |
| backgroundColor | `#0e1117` |
| secondaryBackgroundColor | `#262730` |
| textColor | `#fafafa` |
| font | sans serif |
| チャートテンプレート | `plotly_dark` |

---

## 7. ファイル構成

```
uptrend-dashboard/
├── .streamlit/
│   └── config.toml                    # Streamlit テーマ設定
├── data/
│   └── uptrend.db                     # SQLite DB（gitignore 対象）
├── docs/
│   └── design.md                      # 本設計書
├── src/
│   ├── __init__.py
│   ├── constants.py                   # 定数定義（v2.2 新規）
│   ├── db_client.py                   # SQLite 読み書き（旧 sheets_client.py）
│   ├── indicator_calculator.py        # 派生指標計算（新規）
│   ├── data_processor.py             # ステータス集計
│   ├── chart_builder.py              # Plotly チャート生成
│   └── data_collector.py             # Finviz データ取得（Phase 3）
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # 共通テストフィクスチャ
│   ├── test_db_client.py             # db_client テスト
│   ├── test_indicator_calculator.py  # 派生指標計算テスト
│   ├── test_data_processor.py        # data_processor テスト
│   ├── test_chart_builder.py         # chart_builder テスト
│   ├── test_integration.py          # 統合テスト（v2.2 新規）
│   └── test_data_collector.py        # data_collector テスト（Phase 3）
├── pages/
│   ├── 1_Sector_Detail.py            # セクター詳細ページ
│   └── 2_Sector_Comparison.py        # セクター比較ページ
├── app.py                            # メインページ
├── import_excel.py                   # Excel インポート CLI ツール（Phase 1）
├── collect.py                        # Finviz データ収集 CLI ツール（Phase 3）
├── requirements.txt
├── .env.sample
├── .gitignore
└── README.md
```

### v1 → v2 ファイル変更まとめ

| 変更種別 | ファイル | 説明 |
|---------|----------|------|
| 削除 | `src/sheets_client.py` | Google Sheets 依存を廃止 |
| 新規 | `src/db_client.py` | SQLite データアクセス |
| 新規 | `src/indicator_calculator.py` | 派生指標計算ロジック |
| 新規 | `import_excel.py` | Excel → SQLite インポートツール（Phase 1） |
| 新規 | `src/data_collector.py` | Finviz データ取得・SQLite 書き込み（Phase 3） |
| 新規 | `collect.py` | Finviz データ収集 CLI エントリポイント（Phase 3） |
| 新規 | `tests/test_data_collector.py` | data_collector テスト（Phase 3） |
| 新規 | `data/` ディレクトリ | SQLite DB 格納先 |
| 変更 | `src/data_processor.py` | 型変換処理を削除、カラム名更新 |
| 変更 | `src/chart_builder.py` | カラム名を v2 に更新 |
| 変更 | `app.py`, `pages/*.py` | データソースを db_client に変更 |
| 削除 | `tests/test_sheets_client.py` | sheets_client 廃止に伴い削除 |
| 新規 | `tests/test_db_client.py` | db_client テスト |
| 新規 | `tests/test_indicator_calculator.py` | 派生指標計算テスト |
| 変更 | `tests/conftest.py` | フィクスチャを v2 カラム名に更新 |
| 新規 | `src/constants.py` | 定数一元管理（v2.2） |
| 新規 | `tests/test_integration.py` | 統合テスト（v2.2） |

---

## 8. 依存パッケージ

| パッケージ | バージョン | 用途 | v1→v2 |
|-----------|-----------|------|--------|
| streamlit | >= 1.30.0 | Web フレームワーク | 維持 |
| plotly | >= 5.18.0 | インタラクティブチャート | 維持 |
| pandas | >= 2.0.0 | データ操作 | 維持 |
| openpyxl | >= 3.1.0 | Excel ファイル読み込み | **新規** |
| requests | >= 2.31.0 | Finviz API HTTP リクエスト（Phase 3） | **新規** |
| python-dotenv | >= 1.0.0 | 環境変数読み込み | 維持 |
| pytest | >= 8.0.0 | テストフレームワーク | 維持 |
| pytest-mock | >= 3.12.0 | モックライブラリ | 維持 |
| ~~gspread~~ | — | — | **削除** |
| ~~oauth2client~~ | — | — | **削除** |

> `sqlite3` は Python 標準ライブラリのため依存に含めない。

---

## 9. テスト設計

### 9.1 テスト方針

TDD で実装。テストを先に書き、実装はテストをパスするように記述。

### 9.2 テスト一覧

**test_db_client.py:**

| テスト | 説明 |
|--------|------|
| test_init_creates_table | テーブル自動作成 |
| test_upsert_inserts_new_row | 新規行の挿入 |
| test_upsert_replaces_existing | 同一キーの上書き |
| test_upsert_bulk | DataFrame 一括投入 |
| test_fetch_raw_data | 単一カテゴリの取得 |
| test_fetch_raw_data_empty | データなしカテゴリ |
| test_fetch_all_raw_data | 全カテゴリ一括取得 |
| test_get_worksheets | 登録済みカテゴリ一覧 |
| test_get_date_range | 日付範囲取得 |
| test_context_manager_closes_connection | コンテキストマネージャで接続が閉じられる |
| test_context_manager_commits_on_success | 正常時に commit |
| test_context_manager_rollbacks_on_error | 例外時に rollback |
| test_bulk_upsert_executemany | executemany による一括挿入 |
| test_bulk_upsert_atomicity | トランザクション原子性（不正行でロールバック） |
| test_upsert_rejects_invalid_worksheet | 不正 worksheet の拒否 |
| test_upsert_accepts_valid_worksheet | 有効 worksheet の受付 |
| test_bulk_upsert_rejects_invalid_worksheet | 一括挿入での不正 worksheet 拒否 |

**test_indicator_calculator.py:**

| テスト | 説明 |
|--------|------|
| test_ratio_values | count/total の計算（public API 経由） |
| test_ratio_zero_total | total=0 の除算ゼロ対応 |
| test_ma_10_leading_nans | 10MA の先頭 NaN |
| test_ma_10_value | 10MA の計算値 |
| test_ma_insufficient_data | 10 行未満のデータ（NaN 期間） |
| test_slope_is_ma_diff | MA の差分が slope |
| test_trend_up_matches_positive_slope | slope > 0 → trend_up に値 |
| test_trend_down_matches_nonpositive_slope | slope <= 0 → trend_down に値 |
| test_calculate_indicators_full | 全指標の統合テスト |
| test_custom_config | IndicatorConfig でパラメータ変更 |
| test_peaks_detected_in_sine_wave | 正弦波データでのピーク検出 |
| test_troughs_detected_in_sine_wave | 正弦波データでのトラフ検出 |
| test_peaks_troughs_boolean_columns | is_peak/is_trough の boolean カラム |
| test_strict_config_fewer_detections | 厳格設定での検出数減少 |
| test_calculate_indicators_empty_df | 空 DataFrame の処理 |
| test_ratio_with_nan_count | NaN count の fillna(0) 処理 |
| test_ratio_with_nan_total | NaN total の fillna(0) 処理 |

**test_data_processor.py:**

| テスト | 説明 |
|--------|------|
| test_get_current_status_uptrend | 上昇トレンド時のステータス |
| test_get_current_status_downtrend | 下降トレンド時のステータス |
| test_get_current_status_overbought | 買われすぎ判定 |
| test_get_current_status_oversold | 売られすぎ判定 |
| test_build_sector_summary | セクターサマリー生成 |
| test_build_sector_summary_excludes_all | "all" 除外 |
| test_sector_display_name | カテゴリ名変換 |
| test_get_current_status_empty_df | 空 DataFrame でデフォルト値返却 |
| test_build_sector_summary_empty | 空データでカラム付き空 DF 返却 |
| test_filter_by_date_range | 日付範囲フィルター |

**test_chart_builder.py（v1 から継続）:**

| テスト | 説明 |
|--------|------|
| test_ratio_chart_returns_figure | Figure 型の確認 |
| test_ratio_chart_title | タイトル設定 |
| test_ratio_chart_traces | トレース構成 |
| test_ratio_chart_color_segments | トレンドカラーセグメント（緑/赤/灰色） |
| test_sector_summary_chart | サマリーチャート |
| test_sector_comparison_chart | 比較チャート（11セクター + 2閾値 = 13 trace） |
| test_sector_comparison_selected | フィルタ付き比較（選択セクター + 2閾値） |
| test_sector_comparison_uses_ma_by_default | デフォルトで 10MA 表示 |
| test_sector_comparison_raw_ratio_mode | Raw Ratio モード切替 |
| test_sector_comparison_has_threshold_traces | Upper/Lower 閾値の凡例表示 |
| test_sector_comparison_y_axis_percent | Y 軸パーセント表記 |
| test_sector_comparison_annotations | 最新値アノテーション（セクター数分） |
| test_sector_comparison_legend_sorted_by_latest_value | 凡例が最新値降順でソート |
| test_sector_comparison_custom_colors | カスタムパレット使用の確認 |

**test_integration.py（v2.2 新規）:**

| テスト | 説明 |
|--------|------|
| test_full_pipeline | Excel → DB → 計算 → ステータス → チャートのエンドツーエンド |
| test_multi_sector_pipeline | 複数セクター → DB → 計算 → サマリー → サマリーチャート |
| test_empty_db_pipeline | 空 DB でのパイプライン全体のグレースフル処理 |

**test_data_collector.py（Phase 3 + v3.1 コードレビュー修正）:**

| テスト | 説明 |
|--------|------|
| test_build_uptrend_url | 上昇トレンドスクリーナー URL 構築 |
| test_build_uptrend_url_with_sector | セクター指定付き URL 構築 |
| test_build_total_url | 全体スクリーナー URL 構築 |
| test_fetch_stock_count_success | 正常レスポンスの銘柄数取得 |
| test_fetch_stock_count_retry | リトライロジック |
| test_fetch_stock_count_zero | 0 件レスポンス |
| test_make_request_empty_csv_body | 200 + 空ボディ → 空 DataFrame（v3.1） |
| test_make_request_retries_on_500 | 5xx エラーでリトライ（v3.1） |
| test_make_request_jitter_applied | リトライ遅延に jitter 含有（v3.1） |
| test_session_closed | close() で Session.close() 呼出（v3.1） |
| test_collect_worksheet | 単一カテゴリの取得→DB 書き込み |
| test_collect_all | 全 12 カテゴリの一括取得 |
| test_collect_skip_zero_total | total=0 の場合 UPSERT スキップ |
| test_validate_counts_negative | 負の値 → ValueError（v3.1） |
| test_validate_counts_count_exceeds_total | count > total → ValueError（v3.1） |
| test_collect_worksheet_dry_run | dry_run=True で DB 書込みスキップ（v3.1） |
| test_collect_all_dry_run | collect_all dry_run=True（v3.1） |
| test_cli_exit_code_complete_failure | 全失敗 → exit 1（v3.1） |
| test_cli_exit_code_partial_failure | 部分失敗 → exit 2（v3.1） |
| test_cli_worksheet_error_exit_code | --worksheet 失敗 → exit 1（v3.1） |
| test_cli_invalid_date_format | 不正日付 → exit 1（v3.1） |

### 9.3 テストフィクスチャ (conftest.py)

| フィクスチャ | 型 | 説明 |
|-------------|-----|------|
| `tmp_db` | `str` | `tmp_path` を使った一時 DB パス |
| `sample_raw_df` | `DataFrame` | date, count, total の 20 行サンプル |
| `sample_calculated_df` | `DataFrame` | calculate_indicators 適用済みの DataFrame（シグナルなし） |
| `sample_all_data` | `Dict[str, DataFrame]` | 全 12 カテゴリ分 |

### 9.4 モック対象

| モック対象 | 理由 |
|-----------|------|
| `sqlite3.connect` | テスト用一時 DB を使用するため直接モックは不要（`tmp_path` で対応） |
| `streamlit` (st) | `st.cache_data` のテスト |
| `requests.Session.get` | Finviz API レスポンスのモック（Phase 3: data_collector テスト） |

---

## 10. 既存システムとの関係

### 10.1 最終形のシステム構成（Phase 4 完了後）

```
uptrend-dashboard（自己完結型）
┌──────────────────────────────────────────────┐
│                                              │
│  [Finviz Elite API]                          │
│        │                                     │
│        │ Scrape (collect.py / cron)           │
│        ▼                                     │
│  ┌──────────────────────┐                    │
│  │  data/uptrend.db     │  ← SQLite          │
│  │  (ローカルファイル)    │                    │
│  └─────────┬────────────┘                    │
│            │ Read                             │
│            ▼                                  │
│  ┌──────────────────────┐                    │
│  │  app.py              │  ← Streamlit App    │
│  │  (ダッシュボード表示)  │                    │
│  └──────────────────────┘                    │
└──────────────────────────────────────────────┘

stocktrading (既存・変更なし)
┌──────────────────────────┐
│ uptrend_stocks.py        │  ← 定期実行を停止するのみ
│ uptrend_count_sector.py  │    コードはそのまま残存
└──────────────────────────┘
```

### 10.2 移行ロードマップ

| Phase | 内容 | 対象 | 実装優先度 |
|-------|------|------|-----------|
| Phase 1 | Excel から過去データを SQLite にインポート | uptrend-dashboard | **今回実装** |
| Phase 2 | ダッシュボードを SQLite 読み取りに切り替え | uptrend-dashboard | **今回実装** |
| Phase 3 | stocktrading の書き込み先を SQLite に変更 | stocktrading | 次回対応 |
| Phase 4 | Google Sheets 依存を完全廃止 | 両プロジェクト | Phase 3 完了後 |

### 10.3 Phase 1〜2（今回スコープ）

**Phase 1: Excel インポート**
- `import_excel.py` を実装
- Google Sheets → Excel ダウンロード → SQLite 一括投入
- 過去データ（all: 2023-08-11〜、セクター: 2024-07-21〜）を移行

**Phase 2: ダッシュボード SQLite 化**
- `db_client.py`, `indicator_calculator.py` を実装
- `sheets_client.py` を削除し、全ページのデータソースを SQLite に切り替え
- `gspread`, `oauth2client` 依存を削除

**Phase 1〜2 期間中の運用:**

Phase 3 完了まで、stocktrading は引き続き Google Sheets に書き込む。
ダッシュボード用データは以下のいずれかで SQLite を更新する:

1. **手動**: 定期的に Google Sheets → Excel エクスポート → `import_excel.py`
2. **自動化（オプション）**: stocktrading 側に SQLite 書き込みを追加（Phase 3 の前倒し）

### 10.4 Phase 3: uptrend-dashboard にデータ収集機能を追加

**目的:** uptrend-dashboard 自身が Finviz からデータを取得し SQLite に書き込む機能を実装する。手動 Excel インポートを不要にし、uptrend-dashboard を自己完結型アプリケーションにする。

**方針:** stocktrading 側のコードは変更しない。stocktrading の `uptrend_stocks.py` / `uptrend_count_sector.py` の定期実行（cron 等）を停止し、データ取得の責務を uptrend-dashboard に移管する。

**新規モジュール:**

| ファイル | 説明 |
|---------|------|
| `src/data_collector.py` | Finviz からの Count/Total 取得 + SQLite 書き込み |
| `collect.py` | CLI エントリポイント（cron から呼び出す） |

#### data_collector.py 設計

```python
class DataCollector:
    """Finviz スクリーナーから上昇トレンド銘柄数を取得し SQLite に保存"""

    def __init__(self, db_client: DBClient, config: CollectorConfig):
        ...

    def collect_all(self, date=None, dry_run=False) -> Dict[str, Tuple[int, int]]:
        """全市場 + 全 11 セクターのデータを取得し DB に保存
        dry_run=True 時は DB 書込みスキップ（バリデーションは実行）"""
        ...

    def collect_worksheet(self, worksheet, date=None, dry_run=False) -> Tuple[int, int]:
        """単一カテゴリの Count/Total を取得し DB に UPSERT
        dry_run=True 時は DB 書込みスキップ（バリデーションは実行）"""
        ...

    def close(self) -> None:
        """HTTP Session をクローズ"""
        ...

    def _validate_counts(self, worksheet, count, total) -> None:
        """count/total の整合性検証（負の値、count > total）"""
        ...

    def _fetch_stock_count(self, sector: str = None) -> Tuple[int, int]:
        """Finviz API から (uptrend_count, total_count) を取得"""
        ...

    def _build_uptrend_url(self, sector: str = None) -> str:
        """上昇トレンドスクリーナー URL を構築"""
        ...

    def _build_total_url(self, sector: str = None) -> str:
        """全体スクリーナー URL を構築"""
        ...
```

**CollectorConfig:**

```python
@dataclass
class CollectorConfig:
    finviz_api_key: str           # FINVIZ_API_KEY 環境変数から取得
    base_url: str = "https://elite.finviz.com"
    max_retries: int = 5          # 最大リトライ回数
    retry_delay: float = 2.0      # 初回リトライ待機（秒）、jitter 付き指数バックオフ
    request_interval: float = 2.0 # API リクエスト間隔（秒、レート制限対応）
    http_timeout: float = 30.0    # HTTP タイムアウト（秒）
```

**Finviz スクリーナーフィルター（stocktrading の既存ロジックを移植）:**

上昇トレンド条件:
```
cap=microover, sh_avgvol=o100, sh_price=o10,
ta_highlow52w=a30h, ta_perf2=4wup, ta_sma20=pa,
ta_sma200=pa, ta_sma50=sa200
```

全体条件:
```
cap=microover, sh_avgvol=o100, sh_price=o10
```

セクターフィルター: 各 worksheet 名をそのままフィルターキーとして追加（例: `sec_technology`）。

**取得フロー:**

```
collect.py (CLI)
  │
  │ DataCollector.collect_all()
  │
  ├── _fetch_stock_count(sector=None)        → all の count, total
  │     ├── GET uptrend URL → len(CSV) = uptrend_count
  │     └── GET total URL   → len(CSV) = total_count
  │
  ├── _fetch_stock_count(sector="sec_basicmaterials") → count, total
  │     :  (1 秒間隔で API 呼び出し)
  ├── _fetch_stock_count(sector="sec_utilities")      → count, total
  │
  └── db_client.upsert_raw_data(date, worksheet, count, total) × 12
```

#### collect.py CLI 設計

```bash
# 全カテゴリ取得（デフォルト）
python collect.py

# 特定カテゴリのみ
python collect.py --worksheet all

# 日付指定（過去日のデータ修正用）— YYYY-MM-DD 形式を検証
python collect.py --date 2026-02-07

# ドライラン（collect_all/collect_worksheet の dry_run=True で実行）
python collect.py --dry-run

# デバッグログ付き
python collect.py --verbose
```

**Exit code（v3.1）:**

| コード | 意味 |
|--------|------|
| 0 | 全 12 ワークシート成功 |
| 1 | 全失敗（結果 0 件）、API キー未設定、日付フォーマット不正、`--worksheet` モードでの例外 |
| 2 | 部分失敗（1〜11 ワークシート成功） |

**定期実行（cron 設定例）:**

```bash
# 毎営業日 16:05 ET（クローズ後）に実行
# ※営業日判定はスクリプト内で実施（Alpaca カレンダー API または日付ベース）
5 16 * * 1-5 cd /path/to/uptrend-dashboard && /path/to/python collect.py >> logs/collect.log 2>&1
```

> ログフォーマット: `%(asctime)s %(levelname)s: %(message)s`。RotatingFileHandler は不要（cron のリダイレクトで十分）。

**営業日判定:**

stocktrading では Alpaca API のカレンダーを使用しているが、uptrend-dashboard では Alpaca 依存を避けるため、以下のいずれかで判定:

| 方式 | メリット | デメリット |
|------|---------|-----------|
| A: 単純な平日判定 | 依存なし | 祝日は取得試行→結果0の可能性 |
| B: `exchange_calendars` パッケージ | NYSE 祝日も正確に判定 | 追加依存 |
| C: 実行は毎日、データが 0 件なら UPSERT しない | 最もシンプル | 不要な API コールが発生 |

→ **推奨: C**（シンプルさ優先。Finviz API コールは軽量で、結果が 0 件の場合 UPSERT をスキップすればよい）

**依存パッケージ追加:**

| パッケージ | 用途 |
|-----------|------|
| `requests` | Finviz API への HTTP リクエスト |

> `requests` のみ追加。stocktrading の `FinvizClient` が持つサーキットブレーカー等の高度な機能は不要。指数バックオフ + jitter 付きリトライで十分。

**リトライ・エラーハンドリング仕様（v3.1）:**

| 仕様 | 詳細 |
|------|------|
| リトライ対象 | 429, 500, 502, 503, 504, ConnectionError, Timeout |
| バックオフ | 指数バックオフ（2s → 4s → 8s …）+ jitter（`delay * 0~25%`） |
| EmptyDataError | 200 + 空ボディ → 空 DataFrame 返却（クラッシュ防止） |
| データバリデーション | `_validate_counts()`: 負の値、count > total を検証 |
| 例外限定 | `collect_all()` は `RequestException`, `ValueError`, `EmptyDataError` のみキャッチ |
| Session 管理 | `close()` メソッドで `requests.Session` を確実にクローズ |

**テスト計画（32 件: Phase 3 初期 20 件 + v3.1 追加 12 件）:**

上記「9.2 テスト一覧」の test_data_collector.py セクションを参照。

### 10.5 Phase 4: stocktrading 側の定期実行停止・Google Sheets アーカイブ

**目的:** データ取得の責務が uptrend-dashboard に完全移管されたことを確認し、stocktrading 側の Uptrend 関連定期実行を停止する。

**前提条件:** Phase 3 完了後、uptrend-dashboard の `collect.py` が安定稼働していることを十分な期間（最低 2 週間推奨）検証済みであること。具体的には:

- 毎営業日のデータが SQLite に正しく記録されている
- stocktrading の Google Sheets データと uptrend-dashboard の SQLite データが同一日で一致する

**作業内容:**

| # | 作業 | 対象 |
|---|------|------|
| 1 | stocktrading 側の `uptrend_stocks.py` / `uptrend_count_sector.py` の定期実行（cron）を停止 | stocktrading のスケジューラ設定 |
| 2 | Google Sheets "US Market - Uptrend Stocks" を読み取り専用に変更（アーカイブ） | Google Sheets |
| 3 | stocktrading 側のコードは**そのまま残す**（将来の参照用・フォールバック用） | — |

> **注記:** stocktrading 側の `uptrend_stocks.py` の `is_uptrend()` / `is_downtrend()` / `is_overbought()` は他のトレーディングスクリプトから呼び出されている（例: `orb.py:187`）。これらの関数の Google Sheets 依存については、必要に応じて別途対応する。Phase 4 では定期実行の停止のみをスコープとし、既存トレーディングロジックの改修は行わない。

**Phase 4 完了後のアーキテクチャ:**

```
                    ┌─────────────────────────────┐
                    │     uptrend-dashboard        │
                    │                              │
[Finviz] ─Scrape─→ │  collect.py (cron)           │
                    │     │                        │
                    │     ▼ Write                   │
                    │  data/uptrend.db (SQLite)    │
                    │     │                        │
                    │     ▼ Read                    │
                    │  app.py (Streamlit)          │
                    └─────────────────────────────┘

stocktrading: Uptrend 定期実行を停止（コードは残存）
Google Sheets: 読み取り専用アーカイブ
```

uptrend-dashboard が「データ取得 → 保存 → 可視化」を単体で完結する自己完結型アプリケーションとなる。

---

## 11. Excel インポート仕様

### 11.1 対応フォーマット

| 項目 | 仕様 |
|------|------|
| ファイル形式 | `.xlsx`（Google Sheets からダウンロード） |
| シート構造 | Google Sheets と同一（シート名がカテゴリ名に対応） |
| 必須カラム | Date, Count, Total |
| 日付形式 | `M/D/YYYY`, `YYYY-MM-DD`, Excel シリアル値 等（pandas が解釈可能な形式） |
| 文字コード | UTF-8 |

### 11.2 シート名マッピング

Excel のシート名から worksheet 値への変換:

| Excel シート名 | worksheet 値 |
|---------------|-------------|
| `all` | `all` |
| `sec_basicmaterials` | `sec_basicmaterials` |
| ... | ... |

シート名が worksheet 値と一致しない場合はスキップ（警告ログ出力）。

### 11.3 エラーハンドリング

| ケース | 挙動 |
|--------|------|
| Date が空の行 | スキップ（警告ログ） |
| Count/Total が非数値 | スキップ（警告ログ） |
| 不明なシート名 | スキップ（警告ログ） |
| ファイルが見つからない | エラー終了 |
| DB 書き込み失敗 | トランザクション ROLLBACK、エラー表示 |

---

## 12. 起動・運用手順

### 12.1 初期セットアップ

```bash
cd uptrend-dashboard
pip install -r requirements.txt

# 過去データのインポート
# 1. Google Sheets から Excel をダウンロード
# 2. import_excel.py で SQLite に投入
python import_excel.py path/to/export.xlsx
```

### 12.2 ダッシュボード起動

```bash
streamlit run app.py
```

### 12.3 テスト実行

```bash
pytest tests/ -v
```

### 12.4 データ追加（手動）

```bash
# 新しい Excel ファイルをインポート（既存データは UPSERT で上書き）
python import_excel.py path/to/new_export.xlsx
```
