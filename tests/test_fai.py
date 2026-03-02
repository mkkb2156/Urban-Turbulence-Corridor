"""FAI 計算模組測試。"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import box

from src.morphology.fai import (
    _projected_width,
    compute_fai_all_directions,
    compute_fai_single_direction,
)


class TestProjectedWidth:
    """建物投影寬度計算測試。"""

    def test_north_wind_square_building(self):
        """正北風（0°），正方形建物。投影寬度 = 建物寬度。"""
        building = box(0, 0, 10, 10)
        direction_rad = 0.0  # 北風
        width = _projected_width(building, direction_rad)
        assert abs(width - 10.0) < 0.1

    def test_east_wind_square_building(self):
        """正東風（90°），正方形建物。投影寬度 = 建物寬度。"""
        building = box(0, 0, 10, 10)
        direction_rad = np.pi / 2  # 東風
        width = _projected_width(building, direction_rad)
        assert abs(width - 10.0) < 0.1

    def test_diagonal_wind_square_building(self):
        """45° 風，正方形建物。投影寬度 ≈ 寬度 × √2。"""
        building = box(0, 0, 10, 10)
        direction_rad = np.pi / 4  # 45°（NE）
        width = _projected_width(building, direction_rad)
        expected = 10.0 * np.sqrt(2)
        assert abs(width - expected) < 0.5

    def test_rectangular_building_north(self):
        """正北風，長方形建物。投影寬度 = 東西向寬度。"""
        building = box(0, 0, 20, 10)  # 20m 寬, 10m 深
        direction_rad = 0.0
        width = _projected_width(building, direction_rad)
        assert abs(width - 20.0) < 0.1


class TestFAISingleDirection:
    """單方向 FAI 計算測試。"""

    def test_empty_buildings(self, sample_grid, empty_buildings):
        """無建物時 FAI 應為 0。"""
        result = compute_fai_single_direction(empty_buildings, sample_grid, 0.0)
        assert "fai_0.0" in result.columns
        assert result["fai_0.0"].sum() == 0.0

    def test_fai_range(self, sample_grid, sample_buildings):
        """FAI 值應在合理範圍。"""
        result = compute_fai_single_direction(sample_buildings, sample_grid, 22.5)
        fai_col = "fai_22.5"
        assert fai_col in result.columns
        assert result[fai_col].min() >= 0.0

    def test_crs_validation(self, sample_grid, sample_buildings):
        """CRS 不符應拋出 ValueError。"""
        bad_buildings = sample_buildings.to_crs("EPSG:4326")
        with pytest.raises(ValueError, match="EPSG:3826"):
            compute_fai_single_direction(bad_buildings, sample_grid, 0.0)

    def test_missing_height_column(self, sample_grid):
        """缺少 height 欄位應拋出 ValueError。"""
        no_height = gpd.GeoDataFrame(
            {"geometry": [box(0, 0, 10, 10)]},
            crs="EPSG:3826",
        )
        with pytest.raises(ValueError, match="height"):
            compute_fai_single_direction(no_height, sample_grid, 0.0)

    def test_high_fai_in_dense_grid(self, sample_grid, sample_buildings):
        """密集建物的網格應有較高 FAI。"""
        result = compute_fai_single_direction(sample_buildings, sample_grid, 0.0)
        # 中央網格 (1,1) 有最高建物，FAI 應最高
        center = result[result["grid_id"] == "test_001_001"]
        corner = result[result["grid_id"] == "test_000_000"]
        # 中央有 80m+60m 高樓，左上只有 12m 住宅
        if not center.empty and not corner.empty:
            assert center["fai_0.0"].values[0] >= corner["fai_0.0"].values[0]


class TestFAIAllDirections:
    """多方向 FAI 計算測試。"""

    def test_16_directions(self, sample_grid, sample_buildings):
        """應產生 16 個 FAI 欄位。"""
        result = compute_fai_all_directions(sample_buildings, sample_grid)
        fai_cols = [c for c in result.columns if c.startswith("fai_") and c[4:].replace(".", "").isdigit()]
        assert len(fai_cols) == 16

    def test_fai_max_column(self, sample_grid, sample_buildings):
        """應計算 fai_max 與 fai_max_direction。"""
        result = compute_fai_all_directions(sample_buildings, sample_grid)
        assert "fai_max" in result.columns
        assert "fai_max_direction" in result.columns

    def test_ne_sw_aggregation(self, sample_grid, sample_buildings):
        """應計算 fai_ne 與 fai_sw 聚合欄位。"""
        result = compute_fai_all_directions(sample_buildings, sample_grid)
        assert "fai_ne" in result.columns
        assert "fai_sw" in result.columns
