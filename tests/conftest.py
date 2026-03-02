"""測試共用 fixtures。

提供小範圍建物、網格、道路等測試資料。
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import LineString, Polygon, box

# 自動載入 JSON 報告 plugin
pytest_plugins = ["tests.pytest_json_report"]


@pytest.fixture
def sample_grid() -> gpd.GeoDataFrame:
    """3×3 的 100m 網格（EPSG:3826）。

    覆蓋 300m × 300m 區域，起始座標 (300000, 2770000)。
    """
    cells = []
    ids = []
    rows = []
    cols = []

    origin_x, origin_y = 300000, 2770000
    size = 100

    for r in range(3):
        for c in range(3):
            x0 = origin_x + c * size
            y0 = origin_y + r * size
            cells.append(box(x0, y0, x0 + size, y0 + size))
            ids.append(f"test_{r:03d}_{c:03d}")
            rows.append(r)
            cols.append(c)

    return gpd.GeoDataFrame(
        {"grid_id": ids, "row": rows, "col": cols},
        geometry=cells,
        crs="EPSG:3826",
    )


@pytest.fixture
def sample_buildings() -> gpd.GeoDataFrame:
    """測試用建物資料（EPSG:3826）。

    在 3×3 網格中放置不同大小與高度的建物：
    - 中央網格(1,1)：大型高樓 (60m×60m, 高 80m)
    - 左上(0,0)：小型住宅 (20m×20m, 高 12m)
    - 右下(2,2)：中型建物 (30m×30m, 高 30m)
    - 跨網格(0,1)-(1,1)：橫跨兩個網格的建物
    """
    origin_x, origin_y = 300000, 2770000

    buildings = [
        # 中央高樓
        {
            "geometry": box(origin_x + 120, origin_y + 120, origin_x + 180, origin_y + 180),
            "height": 80.0,
            "height_source": "original",
        },
        # 左上住宅
        {
            "geometry": box(origin_x + 10, origin_y + 10, origin_x + 30, origin_y + 30),
            "height": 12.0,
            "height_source": "original",
        },
        # 右下中型建物
        {
            "geometry": box(origin_x + 210, origin_y + 210, origin_x + 240, origin_y + 240),
            "height": 30.0,
            "height_source": "original",
        },
        # 跨網格建物（橫跨 row 0-1, col 1）
        {
            "geometry": box(origin_x + 110, origin_y + 80, origin_x + 140, origin_y + 120),
            "height": 25.0,
            "height_source": "original",
        },
        # 另一棟高樓（中央附近）
        {
            "geometry": box(origin_x + 150, origin_y + 150, origin_x + 190, origin_y + 190),
            "height": 60.0,
            "height_source": "original",
        },
    ]

    return gpd.GeoDataFrame(buildings, crs="EPSG:3826")


@pytest.fixture
def sample_roads() -> gpd.GeoDataFrame:
    """測試用道路資料（EPSG:3826）。"""
    from shapely.geometry import LineString

    origin_x, origin_y = 300000, 2770000

    roads = [
        {
            "geometry": LineString(
                [(origin_x, origin_y + 150), (origin_x + 300, origin_y + 150)]
            ),
            "highway": "primary",
            "name": "Test Road E-W",
            "road_width": 20.0,
        },
        {
            "geometry": LineString(
                [(origin_x + 150, origin_y), (origin_x + 150, origin_y + 300)]
            ),
            "highway": "secondary",
            "name": "Test Road N-S",
            "road_width": 15.0,
        },
    ]

    return gpd.GeoDataFrame(roads, crs="EPSG:3826")


@pytest.fixture
def empty_buildings() -> gpd.GeoDataFrame:
    """空的建物 GeoDataFrame。"""
    return gpd.GeoDataFrame(
        columns=["geometry", "height", "height_source"],
        geometry="geometry",
        crs="EPSG:3826",
    )


@pytest.fixture
def grid_with_bcr(sample_grid, sample_buildings) -> gpd.GeoDataFrame:
    """含 BCR 的網格（供需要 BCR 的測試使用）。"""
    from src.morphology.bcr import compute_bcr

    return compute_bcr(sample_buildings, sample_grid)


@pytest.fixture
def grid_with_fai(sample_grid, sample_buildings) -> gpd.GeoDataFrame:
    """含 FAI 的網格。"""
    from src.morphology.fai import compute_fai_all_directions

    return compute_fai_all_directions(sample_buildings, sample_grid)


@pytest.fixture
def grid_with_morphology(sample_grid, sample_buildings) -> gpd.GeoDataFrame:
    """含完整形態學指標的網格（BCR + FAI + roughness）。"""
    from src.morphology.bcr import compute_bcr
    from src.morphology.fai import compute_fai_all_directions
    from src.morphology.roughness import compute_roughness_params

    grid = compute_bcr(sample_buildings, sample_grid)
    grid = compute_fai_all_directions(sample_buildings, grid)
    grid = compute_roughness_params(grid, sample_buildings, fai_col="fai_ne")
    return grid


@pytest.fixture
def sample_wind_data() -> pd.DataFrame:
    """測試用風場觀測資料（模擬台北站 1 年資料）。"""
    np.random.seed(42)
    n = 1000
    # 台北東北季風為主
    directions = np.concatenate([
        np.random.normal(35, 20, n // 2) % 360,  # NE monsoon
        np.random.normal(210, 30, n // 4) % 360,  # SW monsoon
        np.random.uniform(0, 360, n // 4),  # transition
    ])
    speeds = np.abs(np.random.normal(4.5, 2.5, n))
    months = np.concatenate([
        np.random.choice([10, 11, 12, 1, 2, 3, 4], n // 2),
        np.random.choice([6, 7, 8, 9], n // 4),
        np.random.choice([5, 9, 10], n // 4),
    ])
    dates = pd.to_datetime([f"2024-{m:02d}-15 12:00" for m in months])

    return pd.DataFrame({
        "wind_speed": speeds,
        "wind_direction": directions,
        "observation_time": dates,
        "station_id": "466920",
    })


@pytest.fixture
def sample_corridors() -> gpd.GeoDataFrame:
    """測試用風廊資料。"""
    origin_x, origin_y = 300000, 2770000

    corridors = gpd.GeoDataFrame(
        {
            "corridor_id": ["c001", "c002", "c003"],
            "total_cost": [10.5, 25.3, 50.0],
            "length_cells": [8, 6, 3],
            "wind_direction": ["northeast", "northeast", "southwest"],
        },
        geometry=[
            LineString([(origin_x, origin_y + 50), (origin_x + 200, origin_y + 50)]),
            LineString([(origin_x + 50, origin_y), (origin_x + 50, origin_y + 250)]),
            LineString([(origin_x + 250, origin_y + 200), (origin_x + 100, origin_y + 250)]),
        ],
        crs="EPSG:3826",
    )
    return corridors
