"""Sky View Factor（SVF）計算。

SVF 衡量某一點「看到天空的比例」（0-1），
SVF 低表示被建物/地形遮蔽嚴重，與通風潛力負相關。
"""

from __future__ import annotations

import logging

import geopandas as gpd
import numpy as np

from config.settings import CRS_INTERNAL

logger = logging.getLogger(__name__)


def estimate_svf_from_morphology(
    grid: gpd.GeoDataFrame,
    buildings: gpd.GeoDataFrame,
    search_radius: float = 100.0,
) -> gpd.GeoDataFrame:
    """從建物形態學估算 SVF（簡化方法）。

    使用建物覆蓋率與平均高度的經驗公式估算。
    精確 SVF 計算需要 QGIS UMEP 外掛或光線追蹤。

    SVF ≈ 1 - (BCR × mean_height / (mean_height + search_radius × tan(45°)))

    Args:
        grid: 分析網格（EPSG:3826），需含 'bcr' 欄位。
        buildings: 建物資料（EPSG:3826），需含 'height' 欄位。
        search_radius: 搜尋半徑（公尺）。

    Returns:
        grid GeoDataFrame 新增 'svf' 欄位（float, 0-1）。
    """
    for name, gdf in [("buildings", buildings), ("grid", grid)]:
        if gdf.crs is None or gdf.crs.to_epsg() != 3826:
            raise ValueError(f"{name} CRS must be EPSG:3826, got {gdf.crs}")

    grid = grid.copy()

    # 計算每個網格的平均建物高度
    intersected = gpd.sjoin(
        buildings[["geometry", "height"]],
        grid[["grid_id", "geometry"]],
        how="inner",
        predicate="intersects",
    )

    mean_heights = intersected.groupby("grid_id")["height"].mean().reset_index()
    mean_heights.columns = ["grid_id", "mean_building_height"]

    grid = grid.merge(mean_heights, on="grid_id", how="left")
    grid["mean_building_height"] = grid["mean_building_height"].fillna(0.0)

    # SVF 經驗估算
    if "bcr" not in grid.columns:
        logger.warning("BCR not found, computing basic SVF estimate")
        grid["bcr"] = 0.0

    h = grid["mean_building_height"]
    bcr = grid["bcr"]

    # Johnson & Watson (1984) 簡化公式
    # SVF ≈ 1 - bcr × (2/π) × arctan(h / search_radius)
    grid["svf"] = 1.0 - bcr * (2 / np.pi) * np.arctan(h / search_radius)
    grid["svf"] = grid["svf"].clip(0, 1)

    grid = grid.drop(columns=["mean_building_height"])

    logger.info(
        "SVF stats: min=%.4f, max=%.4f, mean=%.4f",
        grid["svf"].min(),
        grid["svf"].max(),
        grid["svf"].mean(),
    )

    return grid
