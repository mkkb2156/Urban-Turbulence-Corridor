"""街谷 H/W 比與方向分析。

街谷效應是影響城市風場的關鍵因子：
- H/W > 2: 深谷，渦流區（skimming flow）
- 0.5 < H/W < 2: 一般街谷（wake interference）
- H/W < 0.5: 淺谷，通風良好（isolated roughness）
"""

from __future__ import annotations

import logging

import geopandas as gpd
import numpy as np

from config.settings import CRS_INTERNAL

logger = logging.getLogger(__name__)


def compute_street_canyon_ratio(
    buildings: gpd.GeoDataFrame,
    roads: gpd.GeoDataFrame,
    buffer_distance: float = 30.0,
) -> gpd.GeoDataFrame:
    """計算街谷 H/W 比。

    沿道路兩側搜尋建物，計算平均建物高度(H) / 道路寬度(W)。

    Args:
        buildings: 建物資料（EPSG:3826），需含 'height' 欄位。
        roads: 道路資料（EPSG:3826），需含 'road_width' 欄位。
        buffer_distance: 沿道路搜尋建物的距離（公尺）。

    Returns:
        roads GeoDataFrame 新增 'hw_ratio' 與 'canyon_type' 欄位。
    """
    for name, gdf in [("buildings", buildings), ("roads", roads)]:
        if gdf.crs is None or gdf.crs.to_epsg() != 3826:
            raise ValueError(f"{name} CRS must be EPSG:3826, got {gdf.crs}")

    roads = roads.copy()

    # 建立道路緩衝區
    road_buffers = roads.copy()
    road_buffers["geometry"] = roads.geometry.buffer(buffer_distance)

    # 空間結合找出每段道路附近的建物
    joined = gpd.sjoin(
        buildings[["geometry", "height"]],
        road_buffers[["geometry"]],
        how="inner",
        predicate="intersects",
    )

    # 計算每段道路附近的平均建物高度
    mean_heights = joined.groupby("index_right")["height"].mean()

    roads["adjacent_height"] = roads.index.map(mean_heights).fillna(0.0)

    # H/W ratio
    road_width = roads["road_width"] if "road_width" in roads.columns else 10.0
    roads["hw_ratio"] = roads["adjacent_height"] / road_width

    # 街谷分類
    def _classify_canyon(hw: float) -> str:
        if hw < 0.5:
            return "isolated"  # 淺谷，通風良好
        elif hw < 2.0:
            return "wake_interference"  # 一般街谷
        else:
            return "skimming"  # 深谷，渦流區

    roads["canyon_type"] = roads["hw_ratio"].apply(_classify_canyon)

    logger.info(
        "Canyon stats: mean H/W=%.2f, isolated=%d, wake=%d, skimming=%d",
        roads["hw_ratio"].mean(),
        (roads["canyon_type"] == "isolated").sum(),
        (roads["canyon_type"] == "wake_interference").sum(),
        (roads["canyon_type"] == "skimming").sum(),
    )

    return roads


def assign_canyon_to_grid(
    grid: gpd.GeoDataFrame,
    roads_with_canyon: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """將街谷資訊聚合至網格。

    Args:
        grid: 分析網格。
        roads_with_canyon: 含街谷分析結果的道路資料。

    Returns:
        grid GeoDataFrame 新增 'mean_hw_ratio' 與 'dominant_canyon' 欄位。
    """
    joined = gpd.sjoin(
        roads_with_canyon[["geometry", "hw_ratio", "canyon_type"]],
        grid[["grid_id", "geometry"]],
        how="inner",
        predicate="intersects",
    )

    # 每網格平均 H/W
    mean_hw = joined.groupby("grid_id")["hw_ratio"].mean().reset_index()
    mean_hw.columns = ["grid_id", "mean_hw_ratio"]

    # 每網格主要街谷類型（眾數）
    dominant = joined.groupby("grid_id")["canyon_type"].agg(
        lambda x: x.mode().iloc[0] if len(x) > 0 else "isolated"
    ).reset_index()
    dominant.columns = ["grid_id", "dominant_canyon"]

    grid = grid.copy()
    grid = grid.merge(mean_hw, on="grid_id", how="left")
    grid = grid.merge(dominant, on="grid_id", how="left")
    grid["mean_hw_ratio"] = grid["mean_hw_ratio"].fillna(0.0)
    grid["dominant_canyon"] = grid["dominant_canyon"].fillna("isolated")

    return grid
