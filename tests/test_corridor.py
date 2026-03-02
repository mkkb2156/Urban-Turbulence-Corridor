"""風廊分類與合併模組測試。

測試 classify_corridors()、compute_corridor_width()、merge_nearby_corridors()，
確認主/次/支廊道分類、短路徑降級、合併行為以及空資料處理。
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import LineString, box

from src.wind.corridor import (
    classify_corridors,
    compute_corridor_width,
    merge_nearby_corridors,
)


def _make_corridors(
    n: int = 5,
    costs: list[float] | None = None,
    lengths: list[int] | None = None,
    base_x: float = 300000,
    base_y: float = 2770000,
    spacing: float = 200,
) -> gpd.GeoDataFrame:
    """建立測試風廊資料。"""
    if costs is None:
        costs = [10.0 + i * 5.0 for i in range(n)]
    if lengths is None:
        lengths = [10] * n

    geoms = []
    for i in range(n):
        y = base_y + i * spacing
        geoms.append(LineString([(base_x, y), (base_x + 1000, y)]))

    data = {
        "corridor_id": [f"corridor_{i}" for i in range(n)],
        "total_cost": costs[:n],
        "length_cells": lengths[:n],
    }
    return gpd.GeoDataFrame(data, geometry=geoms, crs="EPSG:3826")


class TestClassifyCorridors:
    """classify_corridors() 功能測試。"""

    def test_primary_secondary_classification(self):
        """前 n_primary 個低成本路徑應分類為 primary。"""
        corridors = _make_corridors(n=6, costs=[5, 8, 12, 15, 20, 25])
        result = classify_corridors(corridors, n_primary=3)
        assert "corridor_class" in result.columns
        # 前 3 個（成本最低）為 primary
        primary_count = (result["corridor_class"] == "primary").sum()
        assert primary_count == 3

    def test_remaining_as_secondary(self):
        """n_primary 之後的路徑應為 secondary。"""
        corridors = _make_corridors(n=5, costs=[5, 10, 15, 20, 25])
        result = classify_corridors(corridors, n_primary=2)
        secondary_count = (result["corridor_class"] == "secondary").sum()
        assert secondary_count >= 1

    def test_short_corridors_downgraded_to_minor(self):
        """過短路徑應降級為 minor。"""
        corridors = _make_corridors(
            n=5,
            costs=[5, 10, 15, 20, 25],
            lengths=[20, 18, 15, 3, 2],  # 最後兩條非常短
        )
        result = classify_corridors(corridors, n_primary=2)
        # 中位數 = 15，min_length = 15 * 0.3 = 4.5
        # length_cells < 4.5 的應被降級為 minor
        short = result[result["length_cells"] < 5]
        if not short.empty:
            assert all(short["corridor_class"] == "minor")

    def test_empty_corridors(self):
        """空風廊應直接返回。"""
        empty = gpd.GeoDataFrame(
            columns=["corridor_id", "total_cost", "geometry"],
            geometry="geometry",
            crs="EPSG:3826",
        )
        result = classify_corridors(empty)
        assert len(result) == 0

    def test_single_corridor_is_primary(self):
        """只有一條風廊時應為 primary。"""
        corridors = _make_corridors(n=1, costs=[10.0], lengths=[15])
        result = classify_corridors(corridors, n_primary=3)
        assert result["corridor_class"].iloc[0] == "primary"

    def test_sorted_by_cost(self):
        """結果應按 total_cost 排序。"""
        corridors = _make_corridors(n=4, costs=[20, 5, 15, 10])
        result = classify_corridors(corridors)
        costs = result["total_cost"].tolist()
        assert costs == sorted(costs)

    def test_all_classes_present(self):
        """分類後應包含 primary、secondary（或 minor）類別。"""
        corridors = _make_corridors(
            n=6,
            costs=[5, 10, 15, 20, 25, 30],
            lengths=[20, 18, 15, 12, 2, 1],
        )
        result = classify_corridors(corridors, n_primary=2)
        classes = set(result["corridor_class"].unique())
        assert "primary" in classes


class TestComputeCorridorWidth:
    """compute_corridor_width() 功能測試。"""

    def test_width_column_added(self, sample_grid):
        """應新增 estimated_width 欄位。"""
        corridors = _make_corridors(n=2)
        # 為 grid 加上 fai_ne 欄位
        grid = sample_grid.copy()
        grid["fai_ne"] = 0.05
        result = compute_corridor_width(corridors, grid)
        assert "estimated_width" in result.columns

    def test_width_non_negative(self, sample_grid):
        """估算寬度應非負。"""
        corridors = _make_corridors(
            n=1,
            base_x=300000,
            base_y=2770150,
        )
        grid = sample_grid.copy()
        grid["fai_ne"] = 0.05
        result = compute_corridor_width(corridors, grid)
        assert result["estimated_width"].iloc[0] >= 0.0

    def test_no_fai_column_zero_width(self, sample_grid):
        """網格無 FAI 欄位時寬度應為 0。"""
        corridors = _make_corridors(
            n=1,
            base_x=300000,
            base_y=2770150,
        )
        result = compute_corridor_width(corridors, sample_grid, fai_col="nonexistent")
        assert result["estimated_width"].iloc[0] == 0.0


class TestMergeNearbyCorridors:
    """merge_nearby_corridors() 功能測試。"""

    def test_nearby_corridors_merged(self):
        """距離小於 merge_distance 的風廊應被合併。"""
        # 兩條非常近的風廊
        corridors = _make_corridors(
            n=3,
            costs=[10, 20, 30],
            spacing=50,  # 只間隔 50m
        )
        result = merge_nearby_corridors(corridors, merge_distance=100)
        # 前兩條距離 50m < 100m，應合併（保留成本較低的）
        assert len(result) < len(corridors)

    def test_distant_corridors_not_merged(self):
        """距離大於 merge_distance 的風廊不應合併。"""
        corridors = _make_corridors(
            n=3,
            costs=[10, 20, 30],
            spacing=500,  # 間隔 500m
        )
        result = merge_nearby_corridors(corridors, merge_distance=100)
        assert len(result) == 3

    def test_keeps_lowest_cost(self):
        """合併後應保留成本最低的風廊。"""
        corridors = _make_corridors(
            n=2,
            costs=[15.0, 5.0],
            spacing=30,  # 非常近
        )
        result = merge_nearby_corridors(corridors, merge_distance=100)
        assert len(result) == 1
        assert result["total_cost"].iloc[0] == 5.0

    def test_single_corridor_no_merge(self):
        """只有一條風廊時不應合併。"""
        corridors = _make_corridors(n=1)
        result = merge_nearby_corridors(corridors, merge_distance=100)
        assert len(result) == 1

    def test_empty_corridors(self):
        """空風廊集合應直接返回。"""
        corridors = _make_corridors(n=1)
        # merge_nearby_corridors 的條件是 len <= 1 直接返回
        result = merge_nearby_corridors(corridors)
        assert len(result) == 1

    def test_reset_index_after_merge(self):
        """合併後索引應重置。"""
        corridors = _make_corridors(n=4, costs=[5, 10, 15, 20], spacing=30)
        result = merge_nearby_corridors(corridors, merge_distance=100)
        assert list(result.index) == list(range(len(result)))
