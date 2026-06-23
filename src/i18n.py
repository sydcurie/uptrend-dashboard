"""Lightweight internationalization (i18n) for the uptrend dashboard.

Design notes:
- Internal DataFrame column names and categorical values (e.g. "Up", "Overbought",
  "converged") stay in English and act as logic keys throughout the codebase.
  Localization happens only at the rendering boundary via t() / col() / val().
- Language is resolved from the Streamlit language-selector widget's session_state
  value (key "_lang_radio"). When Streamlit is unavailable (e.g. unit tests) or no
  language is selected, the default is English — so existing tests remain unaffected.
"""

from typing import List

# Map of selector labels -> language codes
_LANG_LABELS = {"English": "en", "简体中文": "zh"}
DEFAULT_LANG = "en"


def get_lang() -> str:
    """Return the current language code ('en' or 'zh').

    Reads the language-selector widget value from Streamlit session_state when
    available; otherwise falls back to the default ('en').
    """
    try:
        import streamlit as st

        label = st.session_state.get("_lang_radio")
        return _LANG_LABELS.get(label, DEFAULT_LANG)
    except Exception:
        return DEFAULT_LANG


def t(key: str, **kwargs) -> str:
    """Translate a key for the current language, with optional str.format kwargs.

    Falls back to English, then to the key itself, when a translation is missing.
    """
    lang = get_lang()
    table = TRANSLATIONS.get(lang, {})
    text = table.get(key)
    if text is None:
        text = TRANSLATIONS[DEFAULT_LANG].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def col(name: str) -> str:
    """Localize a DataFrame column header (English column name as key)."""
    return t(f"col.{name}")


def val(name: str) -> str:
    """Localize a categorical cell value (English value as key)."""
    return t(f"val.{name}")


def localize_columns(columns: List[str]) -> List[str]:
    """Return localized labels for a list of (English) column names, in order."""
    return [col(c) for c in columns]


def actions(regime_key: str) -> List[str]:
    """Return the localized list of action bullet points for a regime guide key."""
    lang = get_lang()
    table = REGIME_ACTIONS.get(lang, REGIME_ACTIONS[DEFAULT_LANG])
    return table.get(regime_key, REGIME_ACTIONS[DEFAULT_LANG].get(regime_key, []))


def render_language_selector() -> None:
    """Render the language selector radio in the current container (sidebar).

    The widget persists its value in session_state across pages via its key,
    so get_lang() reflects the selection on the very next script run.
    """
    import streamlit as st

    st.radio(
        "Language / 语言",
        list(_LANG_LABELS.keys()),
        key="_lang_radio",
        horizontal=True,
    )


# --- Translation tables --------------------------------------------------------

TRANSLATIONS = {
    "en": {
        # Common / sidebar
        "common.settings": "Settings",
        "common.refresh": "Refresh Data",
        "common.date_range": "Date Range",
        "common.data_download": "Data Download",
        "common.no_data_import": "No data available. Import data using import_excel.py first.",
        "common.display_mode": "Display Mode",
        "opt.smoothed": "Smoothed (10MA)",
        "opt.raw": "Raw Ratio",
        # Metrics
        "metric.current_ratio": "Current Ratio",
        "metric.ratio": "Ratio",
        "metric.10ma": "10MA",
        "metric.trend": "Trend",
        "metric.slope": "Slope",
        "metric.status": "Status",
        "metric.last_updated": "**Last updated:** {date}",
        "metric.dispersion_sigma": "Dispersion (σ)",
        "metric.mean_ratio": "Mean Ratio",
        "metric.regime": "Regime",
        "metric.level": "Level",
        # Categorical values (also used for .title()-style displays)
        "val.Overbought": "Overbought",
        "val.Oversold": "Oversold",
        "val.Normal": "Normal",
        "val.Up": "Up",
        "val.Down": "Down",
        "val.Neutral": "Neutral",
        "val.Converged": "Converged",
        "val.Diverged": "Diverged",
        "val.Low": "Low",
        "val.Mid": "Mid",
        "val.High": "High",
        "val.converged": "Converged",
        "val.diverged": "Diverged",
        "val.normal": "Normal",
        "val.low": "Low",
        "val.mid": "Mid",
        "val.high": "High",
        # Column headers
        "col.Sector": "Sector",
        "col.Industry": "Industry",
        "col.Ratio": "Ratio",
        "col.10MA": "10MA",
        "col.Trend": "Trend",
        "col.Slope": "Slope",
        "col.Status": "Status",
        "col.Total": "Total",
        "col.Current Ratio": "Current Ratio",
        "col.Historical Edge": "Historical Edge",
        "col.regime": "Regime",
        "col.level_regime": "Level",
        "col.window": "Window",
        "col.mean_return": "Mean Return",
        "col.win_rate": "Win Rate",
        "col.count": "Count",
        # Charts
        "chart.date": "Date",
        "chart.ratio": "Ratio",
        "legend.ratio_up": "Ratio (Up)",
        "legend.ratio_down": "Ratio (Down)",
        "legend.ratio_na": "Ratio (N/A)",
        "legend.10ma": "10MA",
        "legend.10ma_peak": "10MA Peak",
        "legend.10ma_trough": "10MA Trough",
        "legend.upper": "Upper",
        "legend.lower": "Lower",
        "legend.dispersion_sigma": "Dispersion (σ)",
        "legend.dispersion_ma10": "Dispersion MA10",
        "legend.p25": "P25 Threshold",
        "legend.p75": "P75 Threshold",
        "legend.mean_ratio": "Mean Ratio",
        "chart.sector_ratio_summary": "Sector Ratio Summary",
        "chart.industry_ratio_summary": "Industry Ratio Summary",
        "chart.industry_ratio_summary_for": "Industry Ratio Summary — {name}",
        "chart.sector_comparison": "Sector Comparison",
        "chart.industry_comparison": "Industry Comparison",
        "chart.suffix_ma": " (10MA)",
        "chart.suffix_raw": " (Raw Ratio)",
        "chart.industry_heatmap": "Industry Heatmap",
        "chart.uptrend_ratio": "Uptrend Ratio",
        "chart.uptrend_ratio_for": "{name} Uptrend Ratio",
        "hover.ratio": "Ratio",
        "hover.10ma": "10MA",
        "hover.trend": "Trend",
        "hover.slope": "Slope",
        "hover.status": "Status",
        # app.py
        "app.page_title": "US Market Uptrend Ratio",
        "app.title": "US Market Uptrend Stock Ratio",
        "app.sidebar_desc": (
            "Tracks the percentage of US stocks in an uptrend across the full market "
            "and 11 sectors. Data is collected daily from "
            '<a href="https://finviz.com/?affilId=279192576" target="_blank" '
            'rel="noopener noreferrer">Finviz</a>.'
        ),
        "app.full_market_ratio": "Full Market Ratio",
        "app.chart_title": "US Market Uptrend Ratio",
        "app.sector_summary": "Sector Summary",
        "dl.ratio_timeseries": "Download Ratio Time Series",
        "dl.sector_summary": "Download Sector Summary",
        # page 1 — Sector Detail
        "p1.page_title": "Sector Detail",
        "p1.title": "Sector Detail",
        "p1.sidebar_desc": (
            "Deep dive into individual sector uptrend ratios with trend direction, "
            "10-day moving average, and overbought/oversold indicators."
        ),
        "p1.select_sector": "Select Sector",
        "p1.no_data_for": "No data available for {name}.",
        "p1.industries_in": "Industries in {name}",
        "p1.no_industry_data": "No industry data available for this sector yet.",
        "dl.timeseries_for": "Download {name} Time Series",
        "dl.industry_summary_for": "Download {name} Industry Summary",
        # page 2 — Sector Comparison
        "p2.page_title": "Sector Comparison",
        "p2.title": "Sector Comparison",
        "p2.sidebar_desc": (
            "Compare uptrend ratios across multiple sectors side by side. "
            "Identify which sectors are leading or lagging the market."
        ),
        "p2.dispersion_link": "📡 Dispersion Monitor",
        "p2.dispersion_label": "**Dispersion**: σ={sigma:.3f} {icon}",
        "p2.dispersion_na": "**Dispersion**: N/A (insufficient data)",
        "p2.select_sectors": "Select Sectors",
        "p2.select_one_sector": "Please select at least one sector.",
        # page 3 — Industry Detail
        "p3.page_title": "Industry Detail",
        "p3.title": "Industry Detail",
        "p3.sidebar_desc": (
            "Deep dive into individual industry uptrend ratios with trend direction, "
            "10-day moving average, and overbought/oversold indicators."
        ),
        "p3.filter_by_sector": "Filter by Sector",
        "p3.all_sectors": "All Sectors",
        "p3.select_industry": "Select Industry",
        "p3.no_industries": "No industries available.",
        "p3.parent_sector": "Parent Sector: {name}",
        # page 4 — Industry Comparison
        "p4.page_title": "Industry Comparison",
        "p4.title": "Industry Comparison",
        "p4.sidebar_desc": (
            "Compare uptrend ratios across multiple industries side by side. "
            "Use Within Sector mode for focused analysis or Cross-Sector for broader comparison."
        ),
        "p4.compare_mode": "Compare Mode",
        "p4.within_sector": "Within Sector",
        "p4.cross_sector": "Cross-Sector",
        "p4.select_sector": "Select Sector",
        "p4.select_industries": "Select Industries",
        "p4.select_industries_max": "Select Industries (max {n})",
        "p4.select_one_industry": "Please select at least one industry.",
        "p4.no_data_selected": "No data available for the selected industries.",
        # page 5 — Industry Heatmap
        "p5.page_title": "Industry Heatmap",
        "p5.title": "Industry Heatmap",
        "p5.sidebar_desc": (
            "Treemap overview of all 149 industries grouped by sector. "
            "Color indicates uptrend ratio strength."
        ),
        "p5.color_mode": "Color Mode",
        "p5.opt_ratio": "Ratio",
        "p5.opt_trend_status": "Trend Status",
        "p5.size_mode": "Size Mode",
        "p5.opt_uniform": "Uniform",
        "p5.opt_stock_count": "Stock Count",
        "p5.no_industry_data": "No industry data available.",
        "p5.kpi_trend_up": "Trend Up",
        "p5.kpi_trend_down": "Trend Down",
        "p5.industry_summary": "Industry Summary",
        # page 6 — Dispersion Monitor
        "p6.page_title": "Dispersion Monitor",
        "p6.title": "Sector Dispersion Monitor",
        "p6.sidebar_desc": (
            "Monitor cross-sectional dispersion of sector uptrend ratios. "
            "Detect convergence (capitulation) and divergence signals."
        ),
        "p6.insufficient": (
            "Insufficient dispersion data. Monitoring features will become available "
            "once enough history accumulates."
        ),
        "p6.signal_normal": (
            "NORMAL — Sector dispersion within normal range (σ={disp:.3f}, mean={mean:.1%})"
        ),
        "p6.signal_capitulation": (
            "CAPITULATION ACTIVE — All sectors converged at low levels "
            "(σ={disp:.3f}, mean={mean:.1%})"
        ),
        "p6.signal_divergence": "DIVERGENCE WARNING — Sector dispersion expanding (σ={disp:.3f})",
        "p6.signal_breakout": "BREAKOUT VELOCITY — Convergence breakout signal (σ={disp:.3f})",
        "p6.dispersion_chart": "Dispersion Chart",
        "p6.regime_timeline": "Regime Timeline",
        "p6.sector_ranking": "Sector Ranking",
        "p6.cap_caption": "CAPITULATION regime: Ranked by historical recovery leaders",
        "p6.div_caption": "DIVERGENCE regime: Ranked by historical defensive leaders",
        "p6.normal_caption": "NORMAL regime: Ranked by current ratio",
        "p6.hist_stats": "Historical Stats (Regime Transition Events)",
        "p6.hist_samples_caption": (
            "Samples are regime transition days only "
            "(consecutive same-regime days count as 1 event)"
        ),
        "p6.forward_stats_pending": "Forward return stats will appear once enough data accumulates.",
        "p6.action_guide": "Regime Action Guide",
        "p6.action_disclaimer": (
            "For decision support only — not investment advice. Always apply your own judgment."
        ),
        "p6.all_regime_actions": "All Regime Actions (Reference)",
        "p6.current_prefix": "**Current: {label}**",
        "p6.current_badge": "CURRENT",
        "guide.converged_low": "Converged + Low (Capitulation)",
        "guide.converged_mid": "Converged + Mid",
        "guide.converged_high": "Converged + High",
        "guide.normal": "Normal",
        "guide.diverged": "Diverged",
    },
    "zh": {
        # Common / sidebar
        "common.settings": "设置",
        "common.refresh": "刷新数据",
        "common.date_range": "日期范围",
        "common.data_download": "数据下载",
        "common.no_data_import": "暂无数据。请先使用 import_excel.py 导入数据。",
        "common.display_mode": "显示模式",
        "opt.smoothed": "平滑（10日均线）",
        "opt.raw": "原始比例",
        # Metrics
        "metric.current_ratio": "当前比例",
        "metric.ratio": "比例",
        "metric.10ma": "10日均线",
        "metric.trend": "趋势",
        "metric.slope": "斜率",
        "metric.status": "状态",
        "metric.last_updated": "**最后更新：** {date}",
        "metric.dispersion_sigma": "离散度 (σ)",
        "metric.mean_ratio": "平均比例",
        "metric.regime": "状态机制",
        "metric.level": "水平",
        # Categorical values
        "val.Overbought": "超买",
        "val.Oversold": "超卖",
        "val.Normal": "正常",
        "val.Up": "上升",
        "val.Down": "下降",
        "val.Neutral": "中性",
        "val.Converged": "收敛",
        "val.Diverged": "发散",
        "val.Low": "低",
        "val.Mid": "中",
        "val.High": "高",
        "val.converged": "收敛",
        "val.diverged": "发散",
        "val.normal": "正常",
        "val.low": "低",
        "val.mid": "中",
        "val.high": "高",
        # Column headers
        "col.Sector": "板块",
        "col.Industry": "行业",
        "col.Ratio": "比例",
        "col.10MA": "10日均线",
        "col.Trend": "趋势",
        "col.Slope": "斜率",
        "col.Status": "状态",
        "col.Total": "总数",
        "col.Current Ratio": "当前比例",
        "col.Historical Edge": "历史优势",
        "col.regime": "状态机制",
        "col.level_regime": "水平",
        "col.window": "窗口",
        "col.mean_return": "平均收益",
        "col.win_rate": "胜率",
        "col.count": "样本数",
        # Charts
        "chart.date": "日期",
        "chart.ratio": "比例",
        "legend.ratio_up": "比例（上升）",
        "legend.ratio_down": "比例（下降）",
        "legend.ratio_na": "比例（无）",
        "legend.10ma": "10日均线",
        "legend.10ma_peak": "10日均线峰值",
        "legend.10ma_trough": "10日均线谷值",
        "legend.upper": "上限",
        "legend.lower": "下限",
        "legend.dispersion_sigma": "离散度 (σ)",
        "legend.dispersion_ma10": "离散度 MA10",
        "legend.p25": "P25 阈值",
        "legend.p75": "P75 阈值",
        "legend.mean_ratio": "平均比例",
        "chart.sector_ratio_summary": "板块比例汇总",
        "chart.industry_ratio_summary": "行业比例汇总",
        "chart.industry_ratio_summary_for": "行业比例汇总 — {name}",
        "chart.sector_comparison": "板块比较",
        "chart.industry_comparison": "行业比较",
        "chart.suffix_ma": "（10日均线）",
        "chart.suffix_raw": "（原始比例）",
        "chart.industry_heatmap": "行业热力图",
        "chart.uptrend_ratio": "上升趋势比例",
        "chart.uptrend_ratio_for": "{name} 上升趋势比例",
        "hover.ratio": "比例",
        "hover.10ma": "10日均线",
        "hover.trend": "趋势",
        "hover.slope": "斜率",
        "hover.status": "状态",
        # app.py
        "app.page_title": "美股上升趋势比例",
        "app.title": "美国市场上升趋势股票比例",
        "app.sidebar_desc": (
            "追踪美国全市场及 11 个板块中处于上升趋势的股票占比。数据每日采集自 "
            '<a href="https://finviz.com/?affilId=279192576" target="_blank" '
            'rel="noopener noreferrer">Finviz</a>。'
        ),
        "app.full_market_ratio": "全市场比例",
        "app.chart_title": "美国市场上升趋势比例",
        "app.sector_summary": "板块汇总",
        "dl.ratio_timeseries": "下载比例时间序列",
        "dl.sector_summary": "下载板块汇总",
        # page 1 — Sector Detail
        "p1.page_title": "板块详情",
        "p1.title": "板块详情",
        "p1.sidebar_desc": (
            "深入分析各板块的上升趋势比例，包含趋势方向、10 日移动平均线以及超买/超卖指标。"
        ),
        "p1.select_sector": "选择板块",
        "p1.no_data_for": "暂无 {name} 的数据。",
        "p1.industries_in": "{name} 所属行业",
        "p1.no_industry_data": "该板块暂无行业数据。",
        "dl.timeseries_for": "下载 {name} 时间序列",
        "dl.industry_summary_for": "下载 {name} 行业汇总",
        # page 2 — Sector Comparison
        "p2.page_title": "板块比较",
        "p2.title": "板块比较",
        "p2.sidebar_desc": (
            "并排比较多个板块的上升趋势比例，识别领先或落后于市场的板块。"
        ),
        "p2.dispersion_link": "📡 离散度监控",
        "p2.dispersion_label": "**离散度**：σ={sigma:.3f} {icon}",
        "p2.dispersion_na": "**离散度**：暂无（数据不足）",
        "p2.select_sectors": "选择板块",
        "p2.select_one_sector": "请至少选择一个板块。",
        # page 3 — Industry Detail
        "p3.page_title": "行业详情",
        "p3.title": "行业详情",
        "p3.sidebar_desc": (
            "深入分析各行业的上升趋势比例，包含趋势方向、10 日移动平均线以及超买/超卖指标。"
        ),
        "p3.filter_by_sector": "按板块筛选",
        "p3.all_sectors": "所有板块",
        "p3.select_industry": "选择行业",
        "p3.no_industries": "暂无可用行业。",
        "p3.parent_sector": "所属板块：{name}",
        # page 4 — Industry Comparison
        "p4.page_title": "行业比较",
        "p4.title": "行业比较",
        "p4.sidebar_desc": (
            "并排比较多个行业的上升趋势比例。使用「板块内」模式进行聚焦分析，"
            "或「跨板块」模式进行更广泛的比较。"
        ),
        "p4.compare_mode": "比较模式",
        "p4.within_sector": "板块内",
        "p4.cross_sector": "跨板块",
        "p4.select_sector": "选择板块",
        "p4.select_industries": "选择行业",
        "p4.select_industries_max": "选择行业（最多 {n} 个）",
        "p4.select_one_industry": "请至少选择一个行业。",
        "p4.no_data_selected": "所选行业暂无数据。",
        # page 5 — Industry Heatmap
        "p5.page_title": "行业热力图",
        "p5.title": "行业热力图",
        "p5.sidebar_desc": (
            "按板块分组展示全部 149 个行业的树状图。颜色表示上升趋势比例的强弱。"
        ),
        "p5.color_mode": "颜色模式",
        "p5.opt_ratio": "比例",
        "p5.opt_trend_status": "趋势状态",
        "p5.size_mode": "大小模式",
        "p5.opt_uniform": "统一",
        "p5.opt_stock_count": "股票数量",
        "p5.no_industry_data": "暂无行业数据。",
        "p5.kpi_trend_up": "上升趋势",
        "p5.kpi_trend_down": "下降趋势",
        "p5.industry_summary": "行业汇总",
        # page 6 — Dispersion Monitor
        "p6.page_title": "离散度监控",
        "p6.title": "板块离散度监控",
        "p6.sidebar_desc": (
            "监控板块上升趋势比例的横截面离散度。检测收敛（投降）与发散信号。"
        ),
        "p6.insufficient": (
            "离散度数据不足。待累积足够的历史数据后，监控功能将可用。"
        ),
        "p6.signal_normal": (
            "正常 — 板块离散度处于正常范围（σ={disp:.3f}，均值={mean:.1%}）"
        ),
        "p6.signal_capitulation": (
            "投降信号触发 — 所有板块在低位收敛（σ={disp:.3f}，均值={mean:.1%}）"
        ),
        "p6.signal_divergence": "发散预警 — 板块离散度扩大（σ={disp:.3f}）",
        "p6.signal_breakout": "突破速度 — 收敛突破信号（σ={disp:.3f}）",
        "p6.dispersion_chart": "离散度图表",
        "p6.regime_timeline": "状态机制时间线",
        "p6.sector_ranking": "板块排名",
        "p6.cap_caption": "投降机制：按历史复苏领涨板块排名",
        "p6.div_caption": "发散机制：按历史防御性领涨板块排名",
        "p6.normal_caption": "正常机制：按当前比例排名",
        "p6.hist_stats": "历史统计（机制转换事件）",
        "p6.hist_samples_caption": (
            "样本仅为机制转换日（连续相同机制的天数计为 1 个事件）"
        ),
        "p6.forward_stats_pending": "待累积足够数据后，前瞻收益统计将显示。",
        "p6.action_guide": "机制操作指南",
        "p6.action_disclaimer": (
            "仅供决策参考，并非投资建议。请始终独立判断。"
        ),
        "p6.all_regime_actions": "所有机制操作（参考）",
        "p6.current_prefix": "**当前：{label}**",
        "p6.current_badge": "当前",
        "guide.converged_low": "收敛 + 低位（投降）",
        "guide.converged_mid": "收敛 + 中位",
        "guide.converged_high": "收敛 + 高位",
        "guide.normal": "正常",
        "guide.diverged": "发散",
    },
}


# Regime action bullet lists (page 6). English keys match _REGIME_GUIDE entries.
REGIME_ACTIONS = {
    "en": {
        "converged_low": [
            "Watch for reversal candidates — historically strong bounce zone",
            "Avoid initiating new short positions",
            "Prioritize sector_edge top-ranked sectors for early entry",
            "Position sizing: start small, scale in on confirmation",
        ],
        "converged_mid": [
            "Risk-on bias — sectors tightly grouped and rising",
            "Favor trend-following in leading sectors",
            "Standard position sizing",
        ],
        "converged_high": [
            "Risk-on bias — broad participation at elevated levels",
            "Favor momentum in strongest sectors",
            "Watch for divergence onset as a potential distribution signal",
        ],
        "normal": [
            "Standard operations — follow individual stock/sector signals",
            "Standard position sizing, no regime-driven adjustment needed",
            "Monitor for regime transitions at P25/P75 boundaries",
        ],
        "diverged": [
            "Tighten new long entry criteria — selectivity over aggression",
            "Reduce position sizes or add hedges",
            "Favor defensive sectors and relative strength leaders",
            "Energy & Utilities have historically tended to outperform in this regime",
        ],
    },
    "zh": {
        "converged_low": [
            "关注反转候选标的 — 历史上的强势反弹区域",
            "避免新建空头仓位",
            "优先布局 sector_edge 排名靠前的板块以提早入场",
            "仓位管理：先小仓试探，确认后逐步加仓",
        ],
        "converged_mid": [
            "偏向风险偏好（Risk-on）— 各板块紧密聚集且上行",
            "在领涨板块中倾向趋势跟随",
            "采用标准仓位规模",
        ],
        "converged_high": [
            "偏向风险偏好（Risk-on）— 在高位呈现广泛参与",
            "在最强板块中倾向动量策略",
            "警惕发散的出现，其可能是派发（distribution）信号",
        ],
        "normal": [
            "常规操作 — 跟随个股/板块信号",
            "采用标准仓位规模，无需基于机制进行调整",
            "在 P25/P75 边界处关注机制转换",
        ],
        "diverged": [
            "收紧新建多头的入场标准 — 重选择性而非激进",
            "减小仓位或增加对冲",
            "倾向防御性板块与相对强度领涨者",
            "历史上能源与公用事业板块在该机制下往往表现更优",
        ],
    },
}
