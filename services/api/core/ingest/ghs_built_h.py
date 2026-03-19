"""GHS-BUILT-H 全球建築高度資料下載與處理。

從 GHSL (Global Human Settlement Layer) 取得 100m 網格建築高度，
用於填補 OSM 建築缺失的高度資訊。

來源: https://ghsl.jrc.ec.europa.eu/ghs_buH2023.php
格式: GeoTIFF (100m grid)
座標系: Mollweide → 需轉換至 EPSG:3826

Usage:
    python -m src.ingest.ghs_built_h --city taipei
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.mask import mask as rasterio_mask
from shapely.geometry import box

from config.settings import CRS_INTERNAL, PROCESSED_DIR, RAW_DIR, get_city_config

logger = logging.getLogger(__name__)

# GHS-BUILT-H R2023A tiles — 台灣所在 tile
# 格式: GHS_BUILT_H_ANBH_E2018_GLOBE_R2023A_54009_100_V1_0_R{row}_C{col}.tif
GHS_BASE_URL = (
    "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/"
    "GHS_BUILT_H_GLOBE_R2023A/GHS_BUILT_H_ANBH_E2018_GLOBE_R2023A_54009_100/V1-0/tiles/"
)

# 台灣大致落在 Mollweide 投影的 R4_C22 tile（ZIP 格式）
TAIWAN_TILE = "GHS_BUILT_H_ANBH_E2018_GLOBE_R2023A_54009_100_V1_0_R4_C22.zip"


def download_ghs_built_h(
    output_dir: Path | str | None = None,
    tile_name: str = TAIWAN_TILE,
) -> Path:
    """下載 GHS-BUILT-H tile。

    Args:
        output_dir: 下載目標目錄。
        tile_name: tile 檔案名稱。

    Returns:
        下載的 GeoTIFF 路徑。
    """
    if output_dir is None:
        output_dir = RAW_DIR / "buildings" / "ghs_built_h"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check for already-extracted TIF
    tif_name = tile_name.replace(".zip", ".tif")
    tif_path = output_dir / tif_name
    if tif_path.exists():
        logger.info("GHS-BUILT-H already extracted: %s", tif_path)
        return tif_path

    zip_path = output_dir / tile_name
    if not zip_path.exists():
        url = f"{GHS_BASE_URL}{tile_name}"
        logger.info("Downloading GHS-BUILT-H from %s", url)

        import requests
        response = requests.get(url, timeout=300, stream=True)
        response.raise_for_status()

        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=16384):
                f.write(chunk)

        logger.info(
            "Downloaded GHS-BUILT-H: %s (%.1f MB)",
            tile_name, zip_path.stat().st_size / 1e6
        )

    # Extract TIF from ZIP
    import zipfile
    with zipfile.ZipFile(zip_path, "r") as zf:
        tif_members = [m for m in zf.namelist() if m.endswith(".tif")]
        if not tif_members:
            raise FileNotFoundError(f"No .tif found in {tile_name}")
        zf.extract(tif_members[0], output_dir)
        extracted = output_dir / tif_members[0]
        if extracted != tif_path:
            extracted.rename(tif_path)
        logger.info("Extracted: %s", tif_path.name)

    return tif_path


def process_ghs_built_h(
    input_path: Path | str,
    city: str = "taipei",
    output_path: Path | str | None = None,
) -> Path:
    """處理 GHS-BUILT-H: 重投影 → 裁切 → 輸出 EPSG:3826 GeoTIFF。

    Args:
        input_path: 原始 GHS-BUILT-H tile 路徑。
        city: 城市名稱。
        output_path: 輸出 GeoTIFF 路徑。

    Returns:
        處理後的 GeoTIFF 路徑。
    """
    from pyproj import Transformer

    config = get_city_config(city)
    minx, miny, maxx, maxy = config.bounds_4326

    input_path = Path(input_path)

    with rasterio.open(input_path) as src:
        src_crs = src.crs
        src_meta = src.meta.copy()

        # 先裁切再重投影（減少處理量）
        # 將 WGS84 邊界轉到來源 CRS (Mollweide)
        transformer = Transformer.from_crs("EPSG:4326", src_crs, always_xy=True)
        clip_minx, clip_miny = transformer.transform(minx - 0.1, miny - 0.1)
        clip_maxx, clip_maxy = transformer.transform(maxx + 0.1, maxy + 0.1)

        clip_geom = box(clip_minx, clip_miny, clip_maxx, clip_maxy)

        try:
            clipped, clipped_transform = rasterio_mask(src, [clip_geom], crop=True)
        except ValueError:
            logger.warning("City bounds outside GHS tile coverage, skipping")
            raise FileNotFoundError(f"GHS-BUILT-H tile does not cover {city}")

    clipped_meta = src_meta.copy()
    clipped_meta.update({
        "height": clipped.shape[1],
        "width": clipped.shape[2],
        "transform": clipped_transform,
    })

    # 重投影到 EPSG:3826
    transform, width, height = calculate_default_transform(
        src_crs, CRS_INTERNAL,
        clipped_meta["width"], clipped_meta["height"],
        *rasterio.transform.array_bounds(
            clipped_meta["height"], clipped_meta["width"], clipped_transform
        ),
    )

    dst_meta = clipped_meta.copy()
    dst_meta.update({
        "crs": CRS_INTERNAL,
        "transform": transform,
        "width": width,
        "height": height,
        "driver": "GTiff",
    })

    dst_data = np.empty((height, width), dtype=clipped.dtype)
    reproject(
        source=clipped[0],
        destination=dst_data,
        src_transform=clipped_transform,
        src_crs=src_crs,
        dst_transform=transform,
        dst_crs=CRS_INTERNAL,
        resampling=Resampling.bilinear,
    )

    # 清理 nodata
    dst_data[dst_data < 0] = 0

    if output_path is None:
        output_path = PROCESSED_DIR / "buildings" / f"{city}_ghs_built_h.tif"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(output_path, "w", **dst_meta) as dst:
        dst.write(dst_data, 1)

    # 統計
    valid = dst_data[dst_data > 0]
    if len(valid) > 0:
        logger.info(
            "GHS-BUILT-H %s: %d cells with buildings, "
            "height min=%.1fm, max=%.1fm, mean=%.1fm",
            city, len(valid), valid.min(), valid.max(), valid.mean()
        )
    else:
        logger.warning("GHS-BUILT-H %s: no building height data found", city)

    logger.info("Saved processed GHS-BUILT-H to %s", output_path)
    return output_path


def enrich_buildings_with_ghs(
    buildings_path: Path | str,
    ghs_path: Path | str,
    output_path: Path | str | None = None,
) -> Path:
    """用 GHS-BUILT-H 填補 OSM 建築缺失高度。

    Args:
        buildings_path: OSM 建築 GeoPackage 路徑。
        ghs_path: GHS-BUILT-H GeoTIFF 路徑。
        output_path: 輸出路徑。

    Returns:
        增強後的 GeoPackage 路徑。
    """
    import geopandas as gpd

    gdf = gpd.read_file(buildings_path)
    estimated_mask = gdf["height_source"] == "estimated"
    n_estimated = estimated_mask.sum()

    if n_estimated == 0:
        logger.info("All buildings have heights, no enrichment needed")
        return Path(buildings_path)

    logger.info("Enriching %d buildings with GHS-BUILT-H heights", n_estimated)

    with rasterio.open(ghs_path) as src:
        for idx in gdf.loc[estimated_mask].index:
            centroid = gdf.loc[idx, "geometry"].centroid
            try:
                row, col = src.index(centroid.x, centroid.y)
                if 0 <= row < src.height and 0 <= col < src.width:
                    h = float(src.read(1, window=rasterio.windows.Window(col, row, 1, 1))[0, 0])
                    if h > 3.0:
                        gdf.loc[idx, "height"] = round(h, 1)
                        gdf.loc[idx, "height_source"] = "ghs_built_h"
            except (IndexError, ValueError):
                continue

    enriched = (gdf["height_source"] == "ghs_built_h").sum()
    logger.info("Enriched %d / %d estimated buildings with GHS heights", enriched, n_estimated)

    if output_path is None:
        output_path = buildings_path
    output_path = Path(output_path)
    gdf.to_file(output_path, driver="GPKG")
    logger.info("Saved enriched buildings to %s", output_path)
    return output_path


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    city = sys.argv[sys.argv.index("--city") + 1] if "--city" in sys.argv else "taipei"

    # 下載 + 處理
    raw_path = download_ghs_built_h()
    process_ghs_built_h(raw_path, city=city)
