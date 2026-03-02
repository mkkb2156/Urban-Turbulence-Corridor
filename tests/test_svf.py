"""Sky View Factor（SVF）計算模組測試。

測試 estimate_svf_from_morphology() 的正確性，包含 SVF 值域、
空建物處理、高密度高樓的低 SVF 效應以及 CRS 驗證。
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import box

from src.morphology.bcr import compute_bcr
from src.morphology.svf import estimate_svf_from_morphology


class TestEstimateSVF:
    """estimate_svf_from_morphology() 功能測試。"""

    def test_svf_in_valid_range(self, sample_grid, sample_buildings):
        """SVF 值應介於 [0, 1] 之間。"""
        grid = compute_bcr(sample_buildings, sample_grid)
        result = estimate_svf_from_morphology(grid, sample_buildings)
        assert "svf" in result.columns
        assert result["svf"].min() >= 0.0
        assert result["svf"].max() <= 1.0

    def test_empty_buildings_svf_near_one(self, sample_grid):
        """無建物時 SVF 應接近 1（完全開放天空）。

        注意：使用帶有正確 dtype 的空建物 GeoDataFrame，
        因為完全空的 GeoDataFrame 的 height 欄位為 object 型態，
        會造成 numpy arctan 計算錯誤。
        """
        import pandas as pd

        # 建立 height 為 float64 的空建物（避免 object dtype 問題）
        empty = gpd.GeoDataFrame(
            {"height": pd.Series(dtype="float64"),
             "height_source": pd.Series(dtype="str")},
            geometry=[],
            crs="EPSG:3826",
        )
        grid = compute_bcr(empty, sample_grid)
        result = estimate_svf_from_morphology(grid, empty)
        assert "svf" in result.columns
        # 所有網格 SVF 應為 1.0（無遮蔽）
        assert result["svf"].min() == pytest.approx(1.0, abs=0.01)

    def test_high_bcr_and_height_lower_svf(self, sample_grid, sample_buildings):
        """高 BCR 且高建物的網格 SVF 應較低。"""
        grid = compute_bcr(sample_buildings, sample_grid)
        result = estimate_svf_from_morphology(grid, sample_buildings)

        # 中央網格 (1,1) 有高樓（80m, 60m），BCR 也高
        center_svf = result[result["grid_id"] == "test_001_001"]["svf"].values[0]
        # 右上角 (0,2) 沒有建物
        empty_cell = result[result["grid_id"] == "test_000_002"]["svf"].values[0]

        assert center_svf < empty_cell

    def test_crs_validation_buildings(self, sample_grid, sample_buildings):
        """建物 CRS 不符時應拋出 ValueError。"""
        grid = compute_bcr(sample_buildings, sample_grid)
        bad_buildings = sample_buildings.to_crs("EPSG:4326")
        with pytest.raises(ValueError, match="EPSG:3826"):
            estimate_svf_from_morphology(grid, bad_buildings)

    def test_crs_validation_grid(self, sample_grid, sample_buildings):
        """網格 CRS 不符時應拋出 ValueError。"""
        grid = compute_bcr(sample_buildings, sample_grid)
        bad_grid = grid.to_crs("EPSG:4326")
        with pytest.raises(ValueError, match="EPSG:3826"):
            estimate_svf_from_morphology(bad_grid, sample_buildings)

    def test_svf_without_bcr_column(self, sample_grid, sample_buildings):
        """網格缺少 bcr 欄位時應自動填入 0（並記錄警告）。"""
        # 不先計算 BCR，直接傳入原始 grid
        result = estimate_svf_from_morphology(sample_grid, sample_buildings)
        assert "svf" in result.columns
        # 由於 BCR 被填為 0，SVF 應都接近 1
        assert result["svf"].min() >= 0.9

    def test_tall_buildings_reduce_svf(self):
        """建物越高，SVF 應越低。"""
        grid = gpd.GeoDataFrame(
            {"grid_id": ["low_cell", "high_cell"], "row": [0, 0], "col": [0, 1]},
            geometry=[box(0, 0, 100, 100), box(100, 0, 200, 100)],
            crs="EPSG:3826",
        )

        # 兩個建物面積相同但高度不同
        buildings = gpd.GeoDataFrame(
            {"height": [10.0, 100.0], "height_source": ["original", "original"]},
            geometry=[box(20, 20, 80, 80), box(120, 20, 180, 80)],
            crs="EPSG:3826",
        )

        grid = compute_bcr(buildings, grid)
        result = estimate_svf_from_morphology(grid, buildings)

        svf_low = result[result["grid_id"] == "low_cell"]["svf"].values[0]
        svf_high = result[result["grid_id"] == "high_cell"]["svf"].values[0]
        assert svf_low > svf_high

    def test_custom_search_radius(self, sample_grid, sample_buildings):
        """自訂搜尋半徑不應導致錯誤。"""
        grid = compute_bcr(sample_buildings, sample_grid)
        result_50 = estimate_svf_from_morphology(grid, sample_buildings, search_radius=50.0)
        result_200 = estimate_svf_from_morphology(grid, sample_buildings, search_radius=200.0)
        assert "svf" in result_50.columns
        assert "svf" in result_200.columns
        # 較小搜尋半徑應使高樓效應更強（SVF 更低）
        center_50 = result_50[result_50["grid_id"] == "test_001_001"]["svf"].values[0]
        center_200 = result_200[result_200["grid_id"] == "test_001_001"]["svf"].values[0]
        assert center_50 <= center_200

    def test_preserves_grid_columns(self, sample_grid, sample_buildings):
        """計算後應保留原始網格欄位。"""
        grid = compute_bcr(sample_buildings, sample_grid)
        result = estimate_svf_from_morphology(grid, sample_buildings)
        for col in ["grid_id", "row", "col", "bcr"]:
            assert col in result.columns
        assert len(result) == len(sample_grid)
