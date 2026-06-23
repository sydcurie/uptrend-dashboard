# 美国市场上升趋势股票比例仪表盘

[English](README.md) | **简体中文**

基于 Streamlit + Plotly 的仪表盘，用于可视化美国市场处于上升趋势的股票比例。数据采集自 Finviz Elite 并存储于 SQLite。

**在线应用**：https://uptrend-dashboard.streamlit.app/

## 功能特性

- **全市场概览**：比例时间序列，含 10 日均线、上限/下限阈值、波峰/波谷标记
- **板块详情**：单个板块分析，含趋势信号 + 行业下钻
- **板块比较**：叠加多个板块比例（10 日均线平滑），带阈值标注
- **行业详情**：单个行业分析，并显示所属板块上下文
- **行业比较**：在板块内或跨板块比较行业（最多 15 个）
- **双语界面**：侧边栏提供 英文 / 简体中文 语言切换
- **自动刷新**：1 小时缓存，并提供手动刷新按钮
- **自包含数据采集**：Finviz Elite CSV 抓取器，附带可用于 cron 的命令行工具（161 个工作表）
- **面向 LLM 的 CSV 导出**：通过 GitHub Actions 自动生成 CSV，可经 raw URL 访问

## 安装与配置

### 前置条件

- Python 3.9+
- Finviz Elite API key（用于数据采集）

### 安装

```bash
git clone https://github.com/sydcurie/uptrend-dashboard.git
cd uptrend-dashboard
pip install -r requirements.txt
```

### 配置

```bash
cp .env.sample .env
# 编辑 .env 并设置 FINVIZ_API_KEY
```

### 数据采集

```bash
# 采集全部工作表（161 个：全市场 + 板块 + 行业）
python collect.py

# 仅采集板块（12 个工作表）
python collect.py --scope sectors

# 仅采集行业（149 个工作表）
python collect.py --scope industries

# 试运行（仅抓取，不写入数据库）
python collect.py --dry-run

# 指定日期
python collect.py --date 2026-02-07

# 单个工作表
python collect.py --worksheet ind_semiconductors

# 从 Excel 导入（历史数据迁移）
python import_excel.py path/to/export.xlsx

# 导出 CSV 文件（采集后在 GitHub Actions 中自动运行）
python export_csv.py --verbose
```

### 运行仪表盘

```bash
streamlit run app.py
```

### 运行测试

```bash
pytest tests/ -v
```

## 项目结构

```
uptrend-dashboard/
├── .streamlit/config.toml          # 主题设置
├── src/
│   ├── constants.py                # 板块、阈值、共享常量
│   ├── db_client.py                # SQLite 增删改查（通过 INSERT OR REPLACE 实现 UPSERT）
│   ├── data_loader.py              # 数据加载、缓存、CSV→DB 引导
│   ├── indicator_calculator.py     # 比例、10 日均线、斜率、趋势、波峰/波谷
│   ├── data_processor.py           # 状态聚合、板块汇总
│   ├── data_collector.py           # Finviz Elite CSV 抓取器
│   ├── i18n.py                     # 国际化（英文/简体中文）
│   └── chart_builder.py            # Plotly 图表生成
├── tests/
│   ├── conftest.py                 # 共享 fixture（tmp_db、示例数据）
│   ├── test_db_client.py
│   ├── test_indicator_calculator.py
│   ├── test_data_processor.py
│   ├── test_chart_builder.py
│   ├── test_data_collector.py
│   ├── test_export_csv.py
│   ├── test_import_excel.py
│   ├── test_i18n.py
│   └── test_integration.py
├── pages/
│   ├── 1_Sector_Detail.py          # 板块详情 + 行业下钻
│   ├── 2_Sector_Comparison.py      # 板块比较页
│   ├── 3_Industry_Detail.py        # 行业详情页
│   └── 4_Industry_Comparison.py    # 行业比较页
├── app.py                          # 主页
├── collect.py                      # 数据采集命令行工具（可用于 cron）
├── export_csv.py                   # CSV 导出命令行工具（在 CI 中自动运行）
├── import_excel.py                 # Excel 导入工具
├── data/
│   ├── uptrend.db                  # SQLite 数据库
│   ├── uptrend_ratio_timeseries.csv # 全部工作表时间序列（自动生成）
│   ├── sector_summary.csv          # 板块汇总快照（自动生成）
│   └── industry_summary.csv        # 行业汇总快照（自动生成）
└── docs/design.md                  # 设计文档
```

## 上升趋势定义

当一只股票在 Finviz 筛选器上**同时**满足以下**全部**条件时，被归类为「上升趋势」：

| 条件 | 说明 |
|------|------|
| 价格 > $10 | 排除仙股 |
| 平均成交量 > 10 万 | 流动性充足 |
| 市值 > $5000 万 | 微型股及以上 |
| 价格 > SMA20 | 短期上升趋势 |
| 价格 > SMA200 | 长期上升趋势 |
| SMA50 > SMA200 | 黄金交叉（多头结构） |
| 较 52 周低点上涨 > 30% | 自底部回升 |
| 4 周表现：上涨 | 近期动量为正 |

**上升趋势比例** =（满足全部条件的股票数）/（仅满足基础筛选条件的股票数：价格、成交量、市值）。该比例按板块每日跟踪，用于衡量市场广度。

## 数据来源

Finviz Elite CSV 导出 API。采集以下对象的上升趋势数量与总数：
- `all` —— 全市场汇总
- `sec_*` —— 11 个板块工作表（基础材料、科技、金融等）
- `ind_*` —— 149 个行业工作表（半导体、软件应用、区域性银行等）

数据以原始计数（count、total）存储于 SQLite（`data/uptrend.db`）。各项指标（比例、10 日均线、斜率、趋势）在读取时实时计算。合计每日采集 161 个工作表。

## CSV 访问（面向 LLM / 程序化使用）

每次数据采集后，CSV 文件会自动生成并提交至 git。可通过 GitHub raw URL 访问：

| 文件 | URL | 说明 |
|------|-----|------|
| 时间序列 | `https://raw.githubusercontent.com/sydcurie/uptrend-dashboard/main/data/uptrend_ratio_timeseries.csv` | 全部 161 个工作表，字段：`worksheet, date, count, total, ratio, ma_10, slope, trend` |
| 板块汇总 | `https://raw.githubusercontent.com/sydcurie/uptrend-dashboard/main/data/sector_summary.csv` | 最新快照：`Sector, Ratio, 10MA, Trend, Slope, Status` |
| 行业汇总 | `https://raw.githubusercontent.com/sydcurie/uptrend-dashboard/main/data/industry_summary.csv` | 最新快照：`Industry, Ratio, 10MA, Trend, Slope, Status` |

- 数值为原始小数（0.29，而非 29%）
- 日期格式为 `YYYY-MM-DD`
- NaN 导出为空字符串
