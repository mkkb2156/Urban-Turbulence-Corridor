"""OSM 建築物資料下載與處理。

從 OpenStreetMap 取得建築物 footprint，估算高度，
供替代 NLSC 3D 建物資料使用。

在 sandbox 環境中無法連線至 Overpass API，請在本機執行：
    python scripts/download_osm_buildings.py --city taipei
"""

from __future__ import annotations

import logging
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from config.settings import (
    BUILDING_HEIGHT_DEFAULT,
    BUILDING_HEIGHT_MAX,
    BUILDING_HEIGHT_MIN,
    CRS_INTERNAL,
    PROCESSED_DIR,
    get_city_config,
)

logger = logging.getLogger(__name__)

# 每層樓預設高度（公尺）
FLOOR_HEIGHT_M = 3.0


def download_osm_buildings(
    city: str = "taipei",
    output_path: Path | str | None = None,
) -> gpd.GeoDataFrame:
    """從 OSM 下載建築物 footprint 並估算高度。

    高度估算策略（依優先順序）：
    1. OSM `height` 標籤 → 直接使用
    2. OSM `building:levels` 標籤 → 層數 × 3.0m
    3. 無標籤 → 用周邊中位數填補，最終 fallback 12m

    Args:
        city: 城市名稱。
        output_path: 輸出 GeoPackage 路徑。

    Returns:
        含有 geometry, height, height_source 的 GeoDataFrame (EPSG:3826)。
    """
    try:
        import osmnx as ox
    except ImportError:
        raise ImportError("osmnx is required: pip install osmnx")

    config = get_city_config(city)
    minx, miny, maxx, maxy = config.bounds_4326

    logger.info("Downloading OSM buildings for %s (bbox: %s)", city, config.bounds_4326)

    # 下載建築物 footprint
    tags = {"building": True}
    gdf = ox.features_from_bbox(bbox=(maxy, miny, maxx, minx), tags=tags)

    # 只保留 Polygon/MultiPolygon
    gdf = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
    logger.info("Downloaded %d building footprints from OSM", len(gdf))

    # 估算高度
    gdf = _estimate_heights(gdf)

    # 轉換座標系
    gdf = gdf.to_crs(CRS_INTERNAL)

    # 只保留需要的欄位
    keep_cols = ["geometry", "height", "height_source"]
    if "name" in gdf.columns:
        keep_cols.append("name")
    gdf = gdf[keep_cols].copy()

    # 移除無效幾何
    gdf = gdf[gdf.geometry.is_valid & ~gdf.geometry.is_empty].copy()

    # 輸出
    if output_path is None:
        output_path = PROCESSED_DIR / "buildings" / f"{city}_buildings.gpkg"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(output_path, driver="GPKG")
    logger.info("Saved %d buildings to %s", len(gdf), output_path)

    _log_height_stats(gdf)
    return gdf


def _estimate_heights(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """從 OSM 標籤估算建物高度。"""
    gdf = gdf.copy()
    gdf["height"] = np.nan
    gdf["height_source"] = "estimated"

    # 策略 1: 使用 `height` 標籤
    if "height" in gdf.columns:
        h = pd.to_numeric(
            gdf["height"].astype(str).str.replace(r"[^\d.]", "", regex=True),
            errors="coerce",
        )
        valid = h.between(BUILDING_HEIGHT_MIN, BUILDING_HEIGHT_MAX)
        gdf.loc[valid, "height"] = h[valid]
        gdf.loc[valid, "height_source"] = "osm_height"
        logger.info("Height from OSM `height` tag: %d buildings", valid.sum())

    # 策略 2: 使用 `building:levels` 標籤
    if "building:levels" in gdf.columns:
        still_missing = gdf["height"].isna()
        levels = pd.to_numeric(gdf["building:levels"], errors="coerce")
        valid_levels = levels.notna() & (levels >= 1) & (levels <= 100) & still_missing
        gdf.loc[valid_levels, "height"] = levels[valid_levels] * FLOOR_HEIGHT_M
        gdf.loc[valid_levels, "height_source"] = "osm_levels"
        logger.info("Height from OSM `building:levels`: %d buildings", valid_levels.sum())

    # 策略 3: 用全域中位數填補
    still_missing = gdf["height"].isna()
    if still_missing.any():
        median_h = gdf["height"].median()
        fill_val = median_h if pd.notna(median_h) else BUILDING_HEIGHT_DEFAULT
        gdf.loc[still_missing, "height"] = fill_val
        gdf.loc[still_missing, "height_source"] = "estimated"
        logger.info(
            "Filled %d missing heights with %.1f m", still_missing.sum(), fill_val
        )

    return gdf


def _log_height_stats(gdf: gpd.GeoDataFrame) -> None:
    """記錄高度統計。"""
    logger.info(
        "Height stats: min=%.1f, max=%.1f, mean=%.1f, median=%.1f",
        gdf["height"].min(),
        gdf["height"].max(),
        gdf["height"].mean(),
        gdf["height"].median(),
    )
    for source in gdf["height_source"].unique():
        cnt = (gdf["height_source"] == source).sum()
        logger.info("  %s: %d (%.1f%%)", source, cnt, cnt / len(gdf) * 100)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    city = sys.argv[sys.argv.index("--city") + 1] if "--city" in sys.argv else "taipei"
    download_osm_buildings(city)
