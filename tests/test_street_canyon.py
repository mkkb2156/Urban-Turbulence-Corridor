"""街谷 H/W 比與分類模組測試。

測試 compute_street_canyon_ratio() 與 assign_canyon_to_grid()，
確認 H/W 比計算、街谷分類（isolated/wake/skimming）以及 CRS 驗證。
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import LineString, box

from src.morphology.street_canyon import (
    assign_canyon_to_grid,
    compute_street_canyon_ratio,
)


class TestComputeStreetCanyonRatio:
    """compute_street_canyon_ratio() 功能測試。"""

    def test_hw_ratio_calculated(self, sample_buildings, sample_roads):
        """應計算 hw_ratio 欄位。"""
        result = compute_street_canyon_ratio(sample_buildings, sample_roads)
        assert "hw_ratio" in result.columns
        assert "canyon_type" in result.columns

    def test_canyon_type_classification(self, sample_buildings, sample_roads):
        """canyon_type 應為 isolated/wake_interference/skimming 之一。"""
        result = compute_street_canyon_ratio(sample_buildings, sample_roads)
        valid_types = {"isolated", "wake_interference", "skimming"}
        assert set(result["canyon_type"].unique()).issubset(valid_types)

    def test_isolated_canyon_low_hw(self):
        """H/W < 0.5 應分類為 isolated（淺谷）。"""
        # 低矮建物、寬闊道路
        buildings = gpd.GeoDataFrame(
            {"height": [5.0], "height_source": ["original"]},
            geometry=[box(10, 10, 30, 30)],
            crs="EPSG:3826",
        )
        roads = gpd.GeoDataFrame(
            {
                "highway": ["primary"],
                "name": ["Wide Road"],
                "road_width": [30.0],
            },
            geometry=[LineString([(0, 20), (100, 20)])],
            crs="EPSG:3826",
        )
        result = compute_street_canyon_ratio(buildings, roads, buffer_distance=50)
        assert result["canyon_type"].iloc[0] == "isolated"
        assert result["hw_ratio"].iloc[0] < 0.5

    def test_skimming_canyon_high_hw(self):
        """H/W > 2 應分類為 skimming（深谷）。"""
        # 高樓、窄道路
        buildings = gpd.GeoDataFrame(
            {"height": [60.0, 55.0], "height_source": ["original", "original"]},
            geometry=[box(5, 5, 15, 30), box(25, 5, 35, 30)],
            crs="EPSG:3826",
        )
        roads = gpd.GeoDataFrame(
            {
                "highway": ["residential"],
                "name": ["Narrow Alley"],
                "road_width": [8.0],
            },
            geometry=[LineString([(0, 15), (40, 15)])],
            crs="EPSG:3826",
        )
        result = compute_street_canyon_ratio(buildings, roads, buffer_distance=20)
        assert result["canyon_type"].iloc[0] == "skimming"
        assert result["hw_ratio"].iloc[0] >= 2.0

    def test_wake_interference_canyon(self):
        """0.5 <= H/W < 2 應分類為 wake_interference。"""
        buildings = gpd.GeoDataFrame(
            {"height": [15.0], "height_source": ["original"]},
            geometry=[box(10, 5, 30, 25)],
            crs="EPSG:3826",
        )
        roads = gpd.GeoDataFrame(
            {
                "highway": ["secondary"],
                "name": ["Medium Road"],
                "road_width": [12.0],
            },
            geometry=[LineString([(0, 15), (50, 15)])],
            crs="EPSG:3826",
        )
        result = compute_street_canyon_ratio(buildings, roads, buffer_distance=30)
        # H/W = 15/12 = 1.25，屬於 wake_interference
        assert result["canyon_type"].iloc[0] == "wake_interference"

    def test_crs_validation_buildings(self, sample_buildings, sample_roads):
        """建物 CRS 不符時應拋出 ValueError。"""
        bad_buildings = sample_buildings.to_crs("EPSG:4326")
        with pytest.raises(ValueError, match="EPSG:3826"):
            compute_street_canyon_ratio(bad_buildings, sample_roads)

    def test_crs_validation_roads(self, sample_buildings, sample_roads):
        """道路 CRS 不符時應拋出 ValueError。"""
        bad_roads = sample_roads.to_crs("EPSG:4326")
        with pytest.raises(ValueError, match="EPSG:3826"):
            compute_street_canyon_ratio(sample_buildings, bad_roads)

    def test_no_adjacent_buildings(self):
        """道路附近無建物時 hw_ratio 應為 0。"""
        buildings = gpd.GeoDataFrame(
            {"height": [20.0], "height_source": ["original"]},
            geometry=[box(500, 500, 520, 520)],  # 遠離道路
            crs="EPSG:3826",
        )
        roads = gpd.GeoDataFrame(
            {
                "highway": ["primary"],
                "name": ["Lonely Road"],
                "road_width": [20.0],
            },
            geometry=[LineString([(0, 50), (100, 50)])],
            crs="EPSG:3826",
        )
        result = compute_street_canyon_ratio(buildings, roads, buffer_distance=30)
        assert result["hw_ratio"].iloc[0] == 0.0
        assert result["canyon_type"].iloc[0] == "isolated"

    def test_preserves_road_columns(self, sample_buildings, sample_roads):
        """計算後應保留道路原始欄位。"""
        result = compute_street_canyon_ratio(sample_buildings, sample_roads)
        for col in ["highway", "name", "road_width"]:
            assert col in result.columns

    def test_multiple_roads(self, sample_buildings, sample_roads):
        """多條道路應各自計算 hw_ratio。"""
        result = compute_street_canyon_ratio(sample_buildings, sample_roads)
        assert len(result) == len(sample_roads)


class TestAssignCanyonToGrid:
    """assign_canyon_to_grid() 功能測試。"""

    def test_assigns_hw_to_grid(self, sample_grid, sample_buildings, sample_roads):
        """應將 mean_hw_ratio 指派至網格。"""
        roads = compute_street_canyon_ratio(sample_buildings, sample_roads)
        result = assign_canyon_to_grid(sample_grid, roads)
        assert "mean_hw_ratio" in result.columns
        assert "dominant_canyon" in result.columns

    def test_no_roads_in_grid(self):
        """網格內無道路時應填入預設值。"""
        grid = gpd.GeoDataFrame(
            {"grid_id": ["cell_000_000"], "row": [0], "col": [0]},
            geometry=[box(0, 0, 100, 100)],
            crs="EPSG:3826",
        )
        roads = gpd.GeoDataFrame(
            {
                "hw_ratio": [1.5],
                "canyon_type": ["wake_interference"],
            },
            geometry=[LineString([(500, 500), (600, 500)])],
            crs="EPSG:3826",
        )
        result = assign_canyon_to_grid(grid, roads)
        assert result["mean_hw_ratio"].iloc[0] == 0.0
        assert result["dominant_canyon"].iloc[0] == "isolated"

    def test_preserves_grid_size(self, sample_grid, sample_buildings, sample_roads):
        """聚合後網格數量不變。"""
        roads = compute_street_canyon_ratio(sample_buildings, sample_roads)
        result = assign_canyon_to_grid(sample_grid, roads)
        assert len(result) == len(sample_grid)

    def test_dominant_canyon_is_valid(self, sample_grid, sample_buildings, sample_roads):
        """dominant_canyon 應為有效類型。"""
        roads = compute_street_canyon_ratio(sample_buildings, sample_roads)
        result = assign_canyon_to_grid(sample_grid, roads)
        valid_types = {"isolated", "wake_interference", "skimming"}
        assert set(result["dominant_canyon"].unique()).issubset(valid_types)
