"""Tests for constants module — industry definitions and helpers."""

from src.constants import (
    DEFAULT_DISPLAY_YEARS,
    INDUSTRIES,
    INDUSTRY_DISPLAY_NAMES,
    INDUSTRY_TO_SECTOR,
    MAX_INDUSTRY_COMPARISON,
    SECTOR_INDUSTRIES,
    SECTORS,
    VALID_WORKSHEETS,
    is_industry,
    is_sector,
)


class TestIndustryConstants:
    """Tests for INDUSTRIES list and related mappings."""

    def test_industries_count(self):
        assert len(INDUSTRIES) == 149

    def test_valid_worksheets_count(self):
        # 1 (all) + 11 (sectors) + 149 (industries) = 161
        assert len(VALID_WORKSHEETS) == 161

    def test_all_industries_have_display_names(self):
        for ind in INDUSTRIES:
            suffix = ind.replace("ind_", "", 1)
            assert suffix in INDUSTRY_DISPLAY_NAMES, f"Missing display name for {ind}"

    def test_all_industries_in_exactly_one_sector(self):
        for ind in INDUSTRIES:
            sectors_containing = [
                sec for sec, inds in SECTOR_INDUSTRIES.items() if ind in inds
            ]
            assert len(sectors_containing) == 1, (
                f"{ind} found in {len(sectors_containing)} sectors: {sectors_containing}"
            )

    def test_industry_to_sector_matches_industries(self):
        assert set(INDUSTRY_TO_SECTOR.keys()) == set(INDUSTRIES)

    def test_no_duplicate_industries(self):
        assert len(INDUSTRIES) == len(set(INDUSTRIES))

    def test_sector_industries_keys_are_valid_sectors(self):
        for key in SECTOR_INDUSTRIES:
            assert key in SECTORS, f"{key} not in SECTORS"

    def test_sector_industries_covers_all_sectors(self):
        assert set(SECTOR_INDUSTRIES.keys()) == set(SECTORS)

    def test_max_industry_comparison(self):
        assert MAX_INDUSTRY_COMPARISON == 15

    def test_default_display_years(self):
        assert DEFAULT_DISPLAY_YEARS == 2


class TestHelperFunctions:
    """Tests for is_sector() and is_industry() helpers."""

    def test_is_sector_true(self):
        assert is_sector("sec_technology") is True
        assert is_sector("sec_financial") is True

    def test_is_sector_false(self):
        assert is_sector("all") is False
        assert is_sector("ind_semiconductors") is False

    def test_is_industry_true(self):
        assert is_industry("ind_semiconductors") is True
        assert is_industry("ind_banksregional") is True

    def test_is_industry_false(self):
        assert is_industry("all") is False
        assert is_industry("sec_technology") is False
