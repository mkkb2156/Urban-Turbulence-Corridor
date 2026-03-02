"""國土利用分類資料處理。"""

from __future__ import annotations

import logging
from pathlib import Path

import geopandas as gpd

from config.settings import CRS_INTERNAL, PROCESSED_DIR

logger = logging.getLogger(__name__)

# 國土利用分類與粗糙度對照
LANDUSE_ROUGHNESS: dict[str, float] = {
    "建築用地": 1.0,    # z₀ = 1.0m（密集市區）
    "交通用地": 0.5,
    "公共設施": 0.8,
    "遊憩用地": 0.1,
    "農業用地": 0.03,
    "森林用地": 1.0,
    "水利用地": 0.001,
    "其他用地": 0.3,
}


def load_landuse(path: Path | str) -> gpd.GeoDataFrame:
    """讀取國土利用分類資料。

    Args:
        path: 資料檔案路徑。

    Returns:
        國土利用 GeoDataFrame（EPSG:3826）。
    """
    gdf = gpd.read_file(path)
    if gdf.crs is None or gdf.crs.to_epsg() != 3826:
        gdf = gdf.to_crs(CRS_INTERNAL)
    logger.info("Loaded %d landuse polygons", len(gdf))
    return gdf


def assign_roughness(gdf: gpd.GeoDataFrame, type_col: str = "LTYPE") -> gpd.GeoDataFrame:
    """根據國土利用類型指定粗糙度長度。

    Args:
        gdf: 國土利用 GeoDataFrame。
        type_col: 土地利用類型欄位名稱。

    Returns:
        新增 'roughness_z0' 欄位的 GeoDataFrame。
    """
    gdf = gdf.copy()
    gdf["roughness_z0"] = gdf[type_col].map(LANDUSE_ROUGHNESS).fillna(0.3)
    return gdf
