"""NLSC 3D 建物下載與解析。

從國土測繪中心取得建物資料，清洗高度欄位，轉換座標系。
"""

from __future__ import annotations

import logging
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from config.settings import (
    BUILDING_HEIGHT_CM_THRESHOLD,
    BUILDING_HEIGHT_DEFAULT,
    BUILDING_HEIGHT_MAX,
    BUILDING_HEIGHT_MIN,
    CRS_INTERNAL,
    PROCESSED_DIR,
    RAW_DIR,
)

logger = logging.getLogger(__name__)


def load_buildings(path: Path | str) -> gpd.GeoDataFrame:
    """讀取建物資料（SHP/GML/GPKG 格式）。

    Args:
        path: 建物資料檔案路徑。

    Returns:
        含有 geometry 與原始欄位的 GeoDataFrame。
    """
    path = Path(path)
    logger.info("Loading buildings from %s", path)

    if path.is_dir():
        shp_files = list(path.glob("*.shp"))
        if not shp_files:
            shp_files = list(path.glob("*.gml"))
        if not shp_files:
            raise FileNotFoundError(f"No SHP/GML files found in {path}")
        gdf = gpd.pd.concat(
            [gpd.read_file(f) for f in shp_files], ignore_index=True
        )
        gdf = gpd.GeoDataFrame(gdf, geometry="geometry")
    else:
        gdf = gpd.read_file(path)

    logger.info("Loaded %d buildings", len(gdf))
    return gdf


def _extract_height_column(gdf: gpd.GeoDataFrame) -> str:
    """找出高度欄位名稱。"""
    candidates = ["BHEIGHT", "HEIGHT", "bheight", "height", "建物高度", "樓高"]
    for col in candidates:
        if col in gdf.columns:
            return col
    raise ValueError(
        f"No height column found. Available columns: {list(gdf.columns)}"
    )


def clean_building_heights(
    gdf: gpd.GeoDataFrame,
    height_col: str | None = None,
) -> gpd.GeoDataFrame:
    """清洗建物高度資料。

    處理策略：
    1. 高於 BUILDING_HEIGHT_CM_THRESHOLD 的值視為公分誤植，除以 100
    2. 超出合理範圍的值標記為缺失
    3. 缺失值用周邊同類型建物平均高度填補
    4. 仍無法推估時使用預設值 12m
    5. 標記 height_source 欄位區分原始/推估

    Args:
        gdf: 含建物高度的 GeoDataFrame。
        height_col: 高度欄位名稱，None 時自動偵測。

    Returns:
        新增 'height' 與 'height_source' 欄位的 GeoDataFrame。
    """
    gdf = gdf.copy()

    if height_col is None:
        height_col = _extract_height_column(gdf)

    gdf["height"] = pd.to_numeric(gdf[height_col], errors="coerce")
    gdf["height_source"] = "original"

    # 修正公分誤植
    cm_mask = gdf["height"] > BUILDING_HEIGHT_CM_THRESHOLD
    if cm_mask.any():
        logger.warning(
            "Found %d buildings with height > %.0f (likely in cm), dividing by 100",
            cm_mask.sum(),
            BUILDING_HEIGHT_CM_THRESHOLD,
        )
        gdf.loc[cm_mask, "height"] = gdf.loc[cm_mask, "height"] / 100
        gdf.loc[cm_mask, "height_source"] = "corrected_cm"

    # 標記超出範圍的值
    out_of_range = (gdf["height"] < BUILDING_HEIGHT_MIN) | (
        gdf["height"] > BUILDING_HEIGHT_MAX
    )
    gdf.loc[out_of_range, "height"] = np.nan

    # 缺失值填補：先用空間鄰近平均，再用全域預設
    missing_mask = gdf["height"].isna()
    missing_count = missing_mask.sum()

    if missing_count > 0:
        logger.info("Filling %d missing building heights", missing_count)
        # 用全域中位數填補（簡化版，完整版應用空間鄰近）
        median_height = gdf["height"].median()
        fill_value = median_height if pd.notna(median_height) else BUILDING_HEIGHT_DEFAULT
        gdf.loc[missing_mask, "height"] = fill_value
        gdf.loc[missing_mask, "height_source"] = "estimated"

    logger.info(
        "Height stats: min=%.1f, max=%.1f, mean=%.1f, estimated=%d/%d",
        gdf["height"].min(),
        gdf["height"].max(),
        gdf["height"].mean(),
        (gdf["height_source"] == "estimated").sum(),
        len(gdf),
    )

    return gdf


def preprocess_buildings(
    input_path: Path | str,
    output_path: Path | str | None = None,
    city: str = "taipei",
) -> gpd.GeoDataFrame:
    """完整建物預處理 pipeline。

    1. 讀取原始建物資料
    2. 轉換座標至 EPSG:3826
    3. 清洗高度
    4. 輸出至 processed 目錄

    Args:
        input_path: 原始建物資料路徑。
        output_path: 輸出路徑，None 時自動產生。
        city: 城市名稱。

    Returns:
        清洗後的 GeoDataFrame。
    """
    gdf = load_buildings(input_path)

    # 轉換座標系
    if gdf.crs is None:
        logger.warning("No CRS detected, assuming EPSG:3826")
        gdf = gdf.set_crs(CRS_INTERNAL)
    elif gdf.crs.to_epsg() != 3826:
        logger.info("Converting CRS from %s to %s", gdf.crs, CRS_INTERNAL)
        gdf = gdf.to_crs(CRS_INTERNAL)

    # 清洗高度
    gdf = clean_building_heights(gdf)

    # 只保留有效幾何
    gdf = gdf[gdf.geometry.is_valid & ~gdf.geometry.is_empty].copy()

    # 輸出
    if output_path is None:
        output_path = PROCESSED_DIR / "buildings" / f"{city}_buildings.gpkg"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(output_path, driver="GPKG")
    logger.info("Saved %d buildings to %s", len(gdf), output_path)

    return gdf


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    city = sys.argv[sys.argv.index("--city") + 1] if "--city" in sys.argv else "taipei"
    input_dir = RAW_DIR / "buildings"
    if "--output" in sys.argv:
        output = Path(sys.argv[sys.argv.index("--output") + 1])
    else:
        output = None
    preprocess_buildings(input_dir, output, city)
