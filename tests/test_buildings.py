"""建物資料清洗模組測試。

測試 _extract_height_column()、clean_building_heights()，
確認高度欄位偵測、公分修正、缺失值填補、height_source 追蹤以及異常值處理。
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

from config.settings import (
    BUILDING_HEIGHT_CM_THRESHOLD,
    BUILDING_HEIGHT_DEFAULT,
    BUILDING_HEIGHT_MAX,
    BUILDING_HEIGHT_MIN,
)
from src.ingest.nlsc_buildings import _extract_height_column, clean_building_heights


def _make_building_gdf(
    heights: list[float | None],
    height_col: str = "BHEIGHT",
) -> gpd.GeoDataFrame:
    """建立含高度欄位的測試建物資料。"""
    n = len(heights)
    geoms = [box(i * 20, 0, (i + 1) * 20, 20) for i in range(n)]
    data = {height_col: heights}
    return gpd.GeoDataFrame(data, geometry=geoms, crs="EPSG:3826")


class TestExtractHeightColumn:
    """_extract_height_column() 功能測試。"""

    def test_detect_bheight(self):
        """應偵測 'BHEIGHT' 欄位。"""
        gdf = _make_building_gdf([10.0], height_col="BHEIGHT")
        assert _extract_height_column(gdf) == "BHEIGHT"

    def test_detect_height(self):
        """應偵測 'HEIGHT' 欄位。"""
        gdf = _make_building_gdf([10.0], height_col="HEIGHT")
        assert _extract_height_column(gdf) == "HEIGHT"

    def test_detect_lowercase_height(self):
        """應偵測小寫 'height' 欄位。"""
        gdf = _make_building_gdf([10.0], height_col="height")
        assert _extract_height_column(gdf) == "height"

    def test_detect_chinese_column(self):
        """應偵測中文 '建物高度' 欄位。"""
        gdf = gpd.GeoDataFrame(
            {"建物高度": [15.0]},
            geometry=[box(0, 0, 20, 20)],
            crs="EPSG:3826",
        )
        assert _extract_height_column(gdf) == "建物高度"

    def test_detect_floor_height(self):
        """應偵測 '樓高' 欄位。"""
        gdf = gpd.GeoDataFrame(
            {"樓高": [12.0]},
            geometry=[box(0, 0, 20, 20)],
            crs="EPSG:3826",
        )
        assert _extract_height_column(gdf) == "樓高"

    def test_no_height_column_raises_error(self):
        """無高度欄位時應拋出 ValueError。"""
        gdf = gpd.GeoDataFrame(
            {"area": [100.0]},
            geometry=[box(0, 0, 20, 20)],
            crs="EPSG:3826",
        )
        with pytest.raises(ValueError, match="No height column"):
            _extract_height_column(gdf)

    def test_priority_order(self):
        """有多個候選欄位時應依優先順序選擇。"""
        gdf = gpd.GeoDataFrame(
            {"BHEIGHT": [10.0], "HEIGHT": [12.0], "height": [8.0]},
            geometry=[box(0, 0, 20, 20)],
            crs="EPSG:3826",
        )
        # BHEIGHT 排在最前面，應被選中
        assert _extract_height_column(gdf) == "BHEIGHT"


class TestCleanBuildingHeights:
    """clean_building_heights() 功能測試。"""

    def test_normal_heights_preserved(self):
        """正常高度值應保留不變。"""
        gdf = _make_building_gdf([10.0, 20.0, 50.0])
        result = clean_building_heights(gdf)
        assert "height" in result.columns
        assert result["height"].tolist() == [10.0, 20.0, 50.0]

    def test_cm_correction(self):
        """大於 CM_THRESHOLD 的值應除以 100。"""
        # 1200 > 500 => 應修正為 12.0
        gdf = _make_building_gdf([1200.0, 5000.0])
        result = clean_building_heights(gdf)
        assert result["height"].iloc[0] == pytest.approx(12.0)
        assert result["height"].iloc[1] == pytest.approx(50.0)

    def test_cm_correction_source_tracking(self):
        """公分修正的建物 height_source 應為 'corrected_cm'。"""
        gdf = _make_building_gdf([1200.0, 20.0])
        result = clean_building_heights(gdf)
        assert result["height_source"].iloc[0] == "corrected_cm"
        assert result["height_source"].iloc[1] == "original"

    def test_missing_heights_filled_with_default(self):
        """缺失高度應用預設值（或中位數）填補。"""
        gdf = _make_building_gdf([None, None, None])
        result = clean_building_heights(gdf)
        # 所有值都缺失，中位數也是 NaN，所以用 BUILDING_HEIGHT_DEFAULT
        for h in result["height"]:
            assert h == pytest.approx(BUILDING_HEIGHT_DEFAULT)

    def test_missing_heights_source_estimated(self):
        """填補的建物 height_source 應為 'estimated'。"""
        gdf = _make_building_gdf([None, 20.0])
        result = clean_building_heights(gdf)
        assert result["height_source"].iloc[0] == "estimated"
        assert result["height_source"].iloc[1] == "original"

    def test_out_of_range_low_replaced(self):
        """低於 BUILDING_HEIGHT_MIN 的值應標記為 NaN 並填補。"""
        gdf = _make_building_gdf([1.0, 20.0])  # 1.0 < 3.0 最低值
        result = clean_building_heights(gdf)
        # 1.0 被標記為 NaN，然後用中位數或預設值填補
        assert result["height"].iloc[0] >= BUILDING_HEIGHT_MIN

    def test_out_of_range_high_replaced(self):
        """超過 BUILDING_HEIGHT_MAX 的值應標記為 NaN 並填補。"""
        gdf = _make_building_gdf([350.0, 20.0])  # 350 > 300 最大值
        result = clean_building_heights(gdf)
        assert result["height"].iloc[0] <= BUILDING_HEIGHT_MAX

    def test_height_source_column_created(self):
        """應建立 height_source 欄位。"""
        gdf = _make_building_gdf([10.0, 20.0])
        result = clean_building_heights(gdf)
        assert "height_source" in result.columns

    def test_all_original_source(self):
        """正常值的 height_source 應為 'original'。"""
        gdf = _make_building_gdf([10.0, 30.0, 50.0])
        result = clean_building_heights(gdf)
        assert all(result["height_source"] == "original")

    def test_mixed_scenarios(self):
        """混合情境：正常、公分誤植、缺失、超限。"""
        gdf = _make_building_gdf(
            [20.0, 1500.0, None, 1.0, 350.0],
        )
        result = clean_building_heights(gdf)
        assert len(result) == 5
        # 20.0: 正常
        assert result["height"].iloc[0] == 20.0
        assert result["height_source"].iloc[0] == "original"
        # 1500.0: 除以 100 = 15.0
        assert result["height"].iloc[1] == pytest.approx(15.0)
        assert result["height_source"].iloc[1] == "corrected_cm"

    def test_custom_height_col(self):
        """支援指定高度欄位名稱。"""
        gdf = gpd.GeoDataFrame(
            {"my_height": [25.0, 30.0]},
            geometry=[box(0, 0, 20, 20), box(20, 0, 40, 20)],
            crs="EPSG:3826",
        )
        result = clean_building_heights(gdf, height_col="my_height")
        assert result["height"].iloc[0] == 25.0
        assert result["height"].iloc[1] == 30.0

    def test_auto_detect_height_column(self):
        """未指定高度欄位時應自動偵測。"""
        gdf = gpd.GeoDataFrame(
            {"BHEIGHT": [15.0, 25.0]},
            geometry=[box(0, 0, 20, 20), box(20, 0, 40, 20)],
            crs="EPSG:3826",
        )
        result = clean_building_heights(gdf)
        assert "height" in result.columns
        assert result["height"].iloc[0] == 15.0

    def test_string_heights_coerced(self):
        """字串型態的高度應被轉換為數值。"""
        gdf = gpd.GeoDataFrame(
            {"BHEIGHT": ["15.5", "abc", "25"]},
            geometry=[box(i * 20, 0, (i + 1) * 20, 20) for i in range(3)],
            crs="EPSG:3826",
        )
        result = clean_building_heights(gdf)
        assert result["height"].iloc[0] == pytest.approx(15.5)
        # "abc" 無法轉換，應被填為估計值
        assert result["height_source"].iloc[1] == "estimated"

    def test_preserves_geometry(self):
        """清洗後應保留原始幾何。"""
        gdf = _make_building_gdf([10.0, 20.0])
        original_geoms = gdf.geometry.tolist()
        result = clean_building_heights(gdf)
        for orig, cleaned in zip(original_geoms, result.geometry.tolist()):
            assert orig.equals(cleaned)

    def test_cm_threshold_boundary(self):
        """恰好等於 CM_THRESHOLD 的值不應修正。"""
        # 500.0 > 500 threshold is >, not >=; but 500 > 500 is False
        gdf = _make_building_gdf([BUILDING_HEIGHT_CM_THRESHOLD])
        result = clean_building_heights(gdf)
        # 500 不大於 500，但 500 > 300 (MAX)，所以會被標記為超限
        # 這取決於 CM_THRESHOLD 和 MAX 的關係
        # CM_THRESHOLD=500, MAX=300: 500 > 500 is False => 不做 CM 修正
        # 但 500 > 300 => 超限 => NaN => 填補
        assert result["height_source"].iloc[0] == "estimated"

    def test_just_above_cm_threshold(self):
        """剛超過 CM_THRESHOLD 的值應除以 100。"""
        gdf = _make_building_gdf([501.0])
        result = clean_building_heights(gdf)
        # 501 > 500 => 修正為 5.01
        assert result["height"].iloc[0] == pytest.approx(5.01)
        assert result["height_source"].iloc[0] == "corrected_cm"
