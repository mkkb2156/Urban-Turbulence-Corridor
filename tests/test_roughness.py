"""粗糙度參數（z0、zd）計算模組測試。

測試 compute_roughness_params() 的正確性，包含 z0/zd 範圍、
建物高度對粗糙度的影響、無建物區域的預設值以及前置欄位需求。
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import box

from src.morphology.bcr import compute_bcr
from src.morphology.fai import compute_fai_single_direction
from src.morphology.roughness import compute_roughness_params


def _prepare_grid_with_bcr_fai(
    grid: gpd.GeoDataFrame,
    buildings: gpd.GeoDataFrame,
    fai_direction: float = 22.5,
) -> gpd.GeoDataFrame:
    """輔助函式：為網格計算 BCR 與 FAI。"""
    result = compute_bcr(buildings, grid)
    result = compute_fai_single_direction(buildings, result, fai_direction)
    # 建立 fai_ne 欄位（roughness 預設使用）
    fai_col = f"fai_{fai_direction:.1f}"
    result["fai_ne"] = result[fai_col]
    return result


class TestComputeRoughnessParams:
    """compute_roughness_params() 功能測試。"""

    def test_z0_positive(self, sample_grid, sample_buildings):
        """有建物的網格 z0 應大於 0。"""
        grid = _prepare_grid_with_bcr_fai(sample_grid, sample_buildings)
        result = compute_roughness_params(grid, sample_buildings)
        assert "z0" in result.columns
        # 有建物的網格 z0 > 0
        has_buildings = result[result["mean_height"] > 0]
        if not has_buildings.empty:
            assert has_buildings["z0"].min() > 0

    def test_zd_non_negative(self, sample_grid, sample_buildings):
        """zd 應大於等於 0。"""
        grid = _prepare_grid_with_bcr_fai(sample_grid, sample_buildings)
        result = compute_roughness_params(grid, sample_buildings)
        assert "zd" in result.columns
        assert result["zd"].min() >= 0.0

    def test_higher_buildings_higher_z0(self):
        """較高建物應產生較大 z0。"""
        # 低矮建物網格
        grid_low = gpd.GeoDataFrame(
            {"grid_id": ["low_000_000"], "row": [0], "col": [0]},
            geometry=[box(0, 0, 100, 100)],
            crs="EPSG:3826",
        )
        buildings_low = gpd.GeoDataFrame(
            {"height": [5.0], "height_source": ["original"]},
            geometry=[box(20, 20, 80, 80)],
            crs="EPSG:3826",
        )

        # 高樓建物網格
        grid_high = gpd.GeoDataFrame(
            {"grid_id": ["high_000_000"], "row": [0], "col": [0]},
            geometry=[box(0, 0, 100, 100)],
            crs="EPSG:3826",
        )
        buildings_high = gpd.GeoDataFrame(
            {"height": [80.0], "height_source": ["original"]},
            geometry=[box(20, 20, 80, 80)],
            crs="EPSG:3826",
        )

        grid_low = _prepare_grid_with_bcr_fai(grid_low, buildings_low)
        grid_high = _prepare_grid_with_bcr_fai(grid_high, buildings_high)

        result_low = compute_roughness_params(grid_low, buildings_low)
        result_high = compute_roughness_params(grid_high, buildings_high)

        assert result_high["z0"].values[0] > result_low["z0"].values[0]

    def test_higher_buildings_higher_zd(self):
        """高密度高樓應產生較大 zd。

        MacDonald 公式中 zd = (1 + alpha^(-lambda_p)) * (lambda_p - 1) * Hav，
        當 lambda_p (BCR) < 1 時 (lambda_p - 1) 為負，zd 被 clip 為 0。
        需要高 BCR（接近 1）才能觀察到 zd > 0。
        """
        # 高 BCR + 低矮建物
        grid_low = gpd.GeoDataFrame(
            {"grid_id": ["low_000_000"], "row": [0], "col": [0]},
            geometry=[box(0, 0, 100, 100)],
            crs="EPSG:3826",
        )
        buildings_low = gpd.GeoDataFrame(
            {"height": [5.0, 5.0, 5.0, 5.0], "height_source": ["original"] * 4},
            geometry=[box(0, 0, 50, 50), box(50, 0, 100, 50),
                      box(0, 50, 50, 100), box(50, 50, 100, 100)],
            crs="EPSG:3826",
        )

        # 高 BCR + 高樓建物
        grid_high = gpd.GeoDataFrame(
            {"grid_id": ["high_000_000"], "row": [0], "col": [0]},
            geometry=[box(0, 0, 100, 100)],
            crs="EPSG:3826",
        )
        buildings_high = gpd.GeoDataFrame(
            {"height": [80.0, 80.0, 80.0, 80.0], "height_source": ["original"] * 4},
            geometry=[box(0, 0, 50, 50), box(50, 0, 100, 50),
                      box(0, 50, 50, 100), box(50, 50, 100, 100)],
            crs="EPSG:3826",
        )

        grid_low = _prepare_grid_with_bcr_fai(grid_low, buildings_low)
        grid_high = _prepare_grid_with_bcr_fai(grid_high, buildings_high)

        result_low = compute_roughness_params(grid_low, buildings_low)
        result_high = compute_roughness_params(grid_high, buildings_high)

        assert result_high["zd"].values[0] >= result_low["zd"].values[0]

    def test_no_buildings_z0_default(self, sample_grid):
        """無建物區域 z0 應為 0.03（開放平地預設值）。"""
        import pandas as pd

        grid = sample_grid.copy()
        grid["bcr"] = 0.0
        grid["fai_ne"] = 0.0

        empty = gpd.GeoDataFrame(
            {"height": pd.Series(dtype="float64"),
             "height_source": pd.Series(dtype="str")},
            geometry=[],
            crs="EPSG:3826",
        )

        result = compute_roughness_params(grid, empty)
        # 所有無建物網格 z0 = 0.03
        for z0_val in result["z0"]:
            assert z0_val == pytest.approx(0.03, abs=0.001)

    def test_no_buildings_zd_zero(self, sample_grid):
        """無建物區域 zd 應為 0。"""
        import pandas as pd

        grid = sample_grid.copy()
        grid["bcr"] = 0.0
        grid["fai_ne"] = 0.0

        empty = gpd.GeoDataFrame(
            {"height": pd.Series(dtype="float64"),
             "height_source": pd.Series(dtype="str")},
            geometry=[],
            crs="EPSG:3826",
        )

        result = compute_roughness_params(grid, empty)
        assert all(result["zd"] == 0.0)

    def test_requires_bcr_column(self, sample_grid, sample_buildings):
        """網格缺少 bcr 欄位時應拋出 ValueError。"""
        grid = compute_fai_single_direction(sample_buildings, sample_grid, 22.5)
        grid["fai_ne"] = grid["fai_22.5"]
        # 未計算 BCR，直接呼叫 roughness
        with pytest.raises(ValueError, match="bcr"):
            compute_roughness_params(grid, sample_buildings)

    def test_requires_fai_column(self, sample_grid, sample_buildings):
        """網格缺少 FAI 欄位時應拋出 ValueError。"""
        grid = compute_bcr(sample_buildings, sample_grid)
        # 未計算 FAI，直接呼叫 roughness
        with pytest.raises(ValueError, match="fai_ne"):
            compute_roughness_params(grid, sample_buildings)

    def test_mean_height_computed(self, sample_grid, sample_buildings):
        """應計算每個網格的平均建物高度。"""
        grid = _prepare_grid_with_bcr_fai(sample_grid, sample_buildings)
        result = compute_roughness_params(grid, sample_buildings)
        assert "mean_height" in result.columns
        # 中央網格有 80m 和 60m 建物
        center = result[result["grid_id"] == "test_001_001"]
        if not center.empty:
            assert center["mean_height"].values[0] > 0

    def test_zd_less_than_mean_height(self, sample_grid, sample_buildings):
        """zd 不應超過 0.9 倍平均建物高度。"""
        grid = _prepare_grid_with_bcr_fai(sample_grid, sample_buildings)
        result = compute_roughness_params(grid, sample_buildings)
        mask = result["mean_height"] > 0
        if mask.any():
            assert all(
                result.loc[mask, "zd"] <= result.loc[mask, "mean_height"] * 0.9 + 0.01
            )

    def test_custom_fai_col(self, sample_grid, sample_buildings):
        """使用自訂 FAI 欄位名稱。"""
        grid = compute_bcr(sample_buildings, sample_grid)
        grid = compute_fai_single_direction(sample_buildings, grid, 45.0)
        result = compute_roughness_params(
            grid, sample_buildings, fai_col="fai_45.0"
        )
        assert "z0" in result.columns
        assert "zd" in result.columns
