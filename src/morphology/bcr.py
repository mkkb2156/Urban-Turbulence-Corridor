"""Building Coverage Ratio（BCR）計算。

BCR = 建物投影面積 / 網格面積
非方向性指標，衡量建物覆蓋密度。
"""

from __future__ import annotations

import logging

import geopandas as gpd

from config.settings import CRS_INTERNAL

logger = logging.getLogger(__name__)


def compute_bcr(
    buildings: gpd.GeoDataFrame,
    grid: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """計算 Building Coverage Ratio。

    Args:
        buildings: 建物資料（EPSG:3826）。
        grid: 分析網格（EPSG:3826），需含 'grid_id' 欄位。

    Returns:
        grid GeoDataFrame 新增 'bcr' 欄位（float, 0-1）。
    """
    for name, gdf in [("buildings", buildings), ("grid", grid)]:
        if gdf.crs is None or gdf.crs.to_epsg() != 3826:
            raise ValueError(f"{name} CRS must be EPSG:3826, got {gdf.crs}")

    # 空間交叉裁切
    intersected = gpd.overlay(
        grid[["grid_id", "geometry"]],
        buildings[["geometry"]],
        how="intersection",
    )

    if intersected.empty:
        grid = grid.copy()
        grid["bcr"] = 0.0
        return grid

    # 計算每個裁切片段的面積
    intersected["building_area"] = intersected.geometry.area

    # 按網格聚合
    bcr_by_grid = intersected.groupby("grid_id")["building_area"].sum().reset_index()
    bcr_by_grid.columns = ["grid_id", "total_building_area"]

    grid = grid.copy()
    grid = grid.merge(bcr_by_grid, on="grid_id", how="left")
    grid["total_building_area"] = grid["total_building_area"].fillna(0.0)

    # BCR = 建物面積 / 網格面積
    grid["bcr"] = grid["total_building_area"] / grid.geometry.area
    grid = grid.drop(columns=["total_building_area"])

    # BCR 應介於 0-1，超過 1 表示幾何重疊問題
    grid["bcr"] = grid["bcr"].clip(0, 1)

    logger.info(
        "BCR stats: min=%.4f, max=%.4f, mean=%.4f",
        grid["bcr"].min(),
        grid["bcr"].max(),
        grid["bcr"].mean(),
    )

    return grid
