"""Building Coverage Ratio（BCR）計算模組測試。

測試 compute_bcr() 的正確性，包含 BCR 值域、空建物處理、
CRS 驗證、密集建物覆蓋率以及跨網格建物處理。
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import box

from src.morphology.bcr import compute_bcr


class TestComputeBCR:
    """compute_bcr() 功能測試。"""

    def test_bcr_in_valid_range(self, sample_grid, sample_buildings):
        """BCR 值應介於 [0, 1] 之間。"""
        result = compute_bcr(sample_buildings, sample_grid)
        assert "bcr" in result.columns
        assert result["bcr"].min() >= 0.0
        assert result["bcr"].max() <= 1.0

    def test_empty_buildings_bcr_zero(self, sample_grid, empty_buildings):
        """無建物時 BCR 應為 0。"""
        result = compute_bcr(empty_buildings, sample_grid)
        assert "bcr" in result.columns
        assert result["bcr"].sum() == 0.0

    def test_crs_validation_buildings(self, sample_grid, sample_buildings):
        """建物 CRS 不為 EPSG:3826 時應拋出 ValueError。"""
        bad_buildings = sample_buildings.to_crs("EPSG:4326")
        with pytest.raises(ValueError, match="EPSG:3826"):
            compute_bcr(bad_buildings, sample_grid)

    def test_crs_validation_grid(self, sample_grid, sample_buildings):
        """網格 CRS 不為 EPSG:3826 時應拋出 ValueError。"""
        bad_grid = sample_grid.to_crs("EPSG:4326")
        with pytest.raises(ValueError, match="EPSG:3826"):
            compute_bcr(sample_buildings, bad_grid)

    def test_crs_validation_none(self, sample_grid, sample_buildings):
        """CRS 為 None 時應拋出 ValueError。"""
        no_crs = sample_buildings.copy()
        no_crs.crs = None
        with pytest.raises(ValueError, match="EPSG:3826"):
            compute_bcr(no_crs, sample_grid)

    def test_dense_buildings_higher_bcr(self, sample_grid):
        """密集建物應產生較高 BCR。"""
        origin_x, origin_y = 300000, 2770000

        # 稀疏建物：只在左上角放一棟小建物
        sparse = gpd.GeoDataFrame(
            {"height": [10.0], "height_source": ["original"]},
            geometry=[box(origin_x + 10, origin_y + 10, origin_x + 20, origin_y + 20)],
            crs="EPSG:3826",
        )

        # 密集建物：在同一網格放很多建物
        dense_geoms = []
        dense_heights = []
        for i in range(5):
            for j in range(5):
                x0 = origin_x + i * 18
                y0 = origin_y + j * 18
                dense_geoms.append(box(x0, y0, x0 + 15, y0 + 15))
                dense_heights.append(20.0)

        dense = gpd.GeoDataFrame(
            {"height": dense_heights, "height_source": ["original"] * len(dense_heights)},
            geometry=dense_geoms,
            crs="EPSG:3826",
        )

        sparse_result = compute_bcr(sparse, sample_grid)
        dense_result = compute_bcr(dense, sample_grid)

        # 左上角網格 (0,0) 的 BCR 比較
        sparse_bcr = sparse_result[sparse_result["grid_id"] == "test_000_000"]["bcr"].values[0]
        dense_bcr = dense_result[dense_result["grid_id"] == "test_000_000"]["bcr"].values[0]
        assert dense_bcr > sparse_bcr

    def test_full_coverage_bcr_near_one(self):
        """建物完全覆蓋網格時 BCR 應接近 1。"""
        grid = gpd.GeoDataFrame(
            {"grid_id": ["cell_000_000"], "row": [0], "col": [0]},
            geometry=[box(0, 0, 100, 100)],
            crs="EPSG:3826",
        )
        buildings = gpd.GeoDataFrame(
            {"height": [20.0], "height_source": ["original"]},
            geometry=[box(0, 0, 100, 100)],  # 完全覆蓋
            crs="EPSG:3826",
        )
        result = compute_bcr(buildings, grid)
        assert result["bcr"].values[0] == pytest.approx(1.0, abs=0.01)

    def test_cross_grid_building(self, sample_grid):
        """跨網格建物應在多個網格貢獻面積。"""
        origin_x, origin_y = 300000, 2770000
        # 建物橫跨 (0,0) 和 (0,1) 兩個網格
        building = gpd.GeoDataFrame(
            {"height": [30.0], "height_source": ["original"]},
            geometry=[box(origin_x + 80, origin_y + 40, origin_x + 120, origin_y + 60)],
            crs="EPSG:3826",
        )
        result = compute_bcr(building, sample_grid)
        # (0,0) 和 (0,1) 兩個網格都應有非零 BCR
        bcr_00 = result[result["grid_id"] == "test_000_000"]["bcr"].values[0]
        bcr_01 = result[result["grid_id"] == "test_000_001"]["bcr"].values[0]
        assert bcr_00 > 0
        assert bcr_01 > 0

    def test_preserves_grid_columns(self, sample_grid, sample_buildings):
        """計算後應保留原始網格欄位。"""
        result = compute_bcr(sample_buildings, sample_grid)
        for col in ["grid_id", "row", "col"]:
            assert col in result.columns
        assert len(result) == len(sample_grid)

    def test_no_buildings_outside_grid(self):
        """建物不在網格範圍內時 BCR 應為 0。"""
        grid = gpd.GeoDataFrame(
            {"grid_id": ["cell_000_000"], "row": [0], "col": [0]},
            geometry=[box(0, 0, 100, 100)],
            crs="EPSG:3826",
        )
        buildings = gpd.GeoDataFrame(
            {"height": [20.0], "height_source": ["original"]},
            geometry=[box(500, 500, 550, 550)],  # 完全在網格外
            crs="EPSG:3826",
        )
        result = compute_bcr(buildings, grid)
        assert result["bcr"].values[0] == 0.0
