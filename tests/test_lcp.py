"""LCP 風廊辨識模組測試。"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import box

from src.wind.lcp import (
    compute_cost_distance,
    corridors_to_grid_mask,
    fai_to_cost_surface,
    identify_wind_corridors,
    trace_least_cost_path,
)


class TestCostSurface:
    """阻力面轉換測試。"""

    def test_basic_conversion(self, sample_grid, sample_buildings):
        """FAI 應成功轉換為阻力面。"""
        from src.morphology.fai import compute_fai_single_direction

        grid = compute_fai_single_direction(sample_buildings, sample_grid, 22.5)
        cost, index_map = fai_to_cost_surface(grid, "fai_22.5")

        assert cost.shape == (3, 3)
        assert cost.min() >= 1.0  # 最小阻力 >= min_cost
        assert len(index_map) > 0

    def test_high_fai_high_cost(self, sample_grid, sample_buildings):
        """高 FAI 網格應有較高阻力。"""
        from src.morphology.fai import compute_fai_single_direction

        grid = compute_fai_single_direction(sample_buildings, sample_grid, 0.0)
        cost, _ = fai_to_cost_surface(grid, "fai_0.0")

        # 中央網格 (1,1) 有高樓，阻力應最高
        # 左上 (0,0) 只有小住宅
        assert cost[1, 1] >= cost[0, 0]


class TestCostDistance:
    """成本距離計算測試。"""

    def test_source_cell_zero_distance(self):
        """源點的成本距離應為 0。"""
        cost = np.ones((3, 3))
        sources = [(0, 0)]
        dist = compute_cost_distance(cost, sources)
        assert dist[0, 0] == 0.0

    def test_distance_increases(self):
        """距離源點越遠，成本距離越大。"""
        cost = np.ones((5, 5))
        sources = [(0, 0)]
        dist = compute_cost_distance(cost, sources)
        assert dist[0, 0] < dist[2, 2] < dist[4, 4]

    def test_high_cost_barrier(self):
        """高阻力區域應增加路徑成本。"""
        cost = np.ones((5, 5))
        cost[2, :] = 100.0  # 中間橫列設為高阻力
        sources = [(0, 2)]
        dist = compute_cost_distance(cost, sources)

        # 高阻力阻擋下，穿過 row 2 的路徑成本應很高
        assert dist[4, 2] > dist[1, 2]


class TestLCPTrace:
    """最低成本路徑回溯測試。"""

    def test_simple_path(self):
        """簡單 3×3 網格的 LCP。"""
        cost_surface = np.ones((3, 3))
        # 建立明確的成本距離梯度
        cost_distance = np.array([
            [0.0, 1.0, 2.0],
            [1.0, 1.5, 2.5],
            [2.0, 2.5, 3.0],
        ])
        path = trace_least_cost_path(cost_distance, cost_surface, (2, 2))
        assert len(path) >= 2
        assert path[0] == (2, 2)
        assert path[-1] == (0, 0)  # 到達源點


class TestCorridorIdentification:
    """風廊辨識整合測試。"""

    def test_corridors_from_grid(self, sample_grid, sample_buildings):
        """應能從網格辨識風廊。"""
        from src.morphology.fai import compute_fai_single_direction

        grid = compute_fai_single_direction(sample_buildings, sample_grid, 22.5)
        corridors = identify_wind_corridors(grid, fai_col="fai_22.5", n_corridors=3)

        assert isinstance(corridors, gpd.GeoDataFrame)
        if not corridors.empty:
            assert "corridor_id" in corridors.columns
            assert "total_cost" in corridors.columns

    def test_corridor_grid_mask(self, sample_grid, sample_buildings):
        """風廊標記應正確應用至網格。"""
        from src.morphology.fai import compute_fai_single_direction

        grid = compute_fai_single_direction(sample_buildings, sample_grid, 22.5)
        corridors = identify_wind_corridors(grid, fai_col="fai_22.5")
        result = corridors_to_grid_mask(grid, corridors)

        assert "is_corridor" in result.columns
        assert "corridor_rank" in result.columns
