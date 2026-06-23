"""Tests for the i18n module and localized display helpers."""

import pytest

from src import i18n
from src.constants import (
    INDUSTRIES,
    INDUSTRY_DISPLAY_NAMES_ZH,
    SECTORS,
    SECTOR_DISPLAY_NAMES_ZH,
)
from src.data_processor import get_industry_display_name, get_sector_display_name


class TestTranslationCompleteness:
    def test_zh_covers_all_en_keys(self):
        en_keys = set(i18n.TRANSLATIONS["en"])
        zh_keys = set(i18n.TRANSLATIONS["zh"])
        missing = en_keys - zh_keys
        assert not missing, f"zh missing keys: {sorted(missing)}"

    def test_no_extra_zh_keys(self):
        en_keys = set(i18n.TRANSLATIONS["en"])
        zh_keys = set(i18n.TRANSLATIONS["zh"])
        extra = zh_keys - en_keys
        assert not extra, f"zh has keys absent from en: {sorted(extra)}"

    def test_regime_actions_parity(self):
        en = i18n.REGIME_ACTIONS["en"]
        zh = i18n.REGIME_ACTIONS["zh"]
        assert set(en) == set(zh)
        for key in en:
            assert len(en[key]) == len(zh[key]), f"action count mismatch for {key}"


class TestNameDictionaries:
    def test_all_sectors_have_zh(self):
        for sec in SECTORS:
            suffix = sec.replace("sec_", "", 1)
            assert suffix in SECTOR_DISPLAY_NAMES_ZH, f"missing zh sector: {suffix}"

    def test_all_industries_have_zh(self):
        for ind in INDUSTRIES:
            suffix = ind.replace("ind_", "", 1)
            assert suffix in INDUSTRY_DISPLAY_NAMES_ZH, f"missing zh industry: {suffix}"


class TestTranslateHelpers:
    def test_default_lang_is_en(self):
        assert i18n.get_lang() == "en"

    def test_t_returns_english_by_default(self):
        assert i18n.t("common.settings") == "Settings"

    def test_t_missing_key_falls_back_to_key(self):
        assert i18n.t("nonexistent.key") == "nonexistent.key"

    def test_t_formats_kwargs(self):
        assert i18n.t("p1.no_data_for", name="Energy") == "No data available for Energy."

    def test_col_and_val(self):
        assert i18n.col("Ratio") == "Ratio"
        assert i18n.val("Overbought") == "Overbought"

    def test_zh_when_lang_set(self, monkeypatch):
        monkeypatch.setattr(i18n, "get_lang", lambda: "zh")
        assert i18n.t("common.settings") == "设置"
        assert i18n.val("Overbought") == "超买"
        assert i18n.col("Ratio") == "比例"


class TestLocalizedDisplayNames:
    def test_sector_name_english_by_default(self):
        assert get_sector_display_name("sec_basicmaterials") == "Basic Materials"

    def test_industry_name_english_by_default(self):
        assert get_industry_display_name("ind_semiconductors") == "Semiconductors"

    def test_sector_name_zh(self, monkeypatch):
        # data_processor imported get_lang by name, so patch it there
        monkeypatch.setattr("src.data_processor.get_lang", lambda: "zh")
        assert get_sector_display_name("sec_technology") == "科技"

    def test_industry_name_zh(self, monkeypatch):
        monkeypatch.setattr("src.data_processor.get_lang", lambda: "zh")
        assert get_industry_display_name("ind_semiconductors") == "半导体"
