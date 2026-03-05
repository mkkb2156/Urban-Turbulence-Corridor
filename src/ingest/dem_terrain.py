"""DSM/DTM 下載與處理。

處理 20m DTM/DSM 地形資料，裁切至目標城市範圍。
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import rasterio
from rasterio.mask import mask as rasterio_mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
from shapely.geometry import box

from config.settings import CRS_INTERNAL, PROCESSED_DIR, RAW_DIR, get_city_config

logger = logging.getLogger(__name__)


def load_dem(path: Path | str) -> tuple[np.ndarray, dict]:
    """讀取 DEM/DSM 光柵資料。

    Args:
        path: GeoTIFF 檔案路徑。

    Returns:
        (data_array, metadata) 元組。
    """
    path = Path(path)
    with rasterio.open(path) as src:
        data = src.read(1)
        meta = src.meta.copy()
        meta["transform"] = src.transform
        meta["crs"] = src.crs
    logger.info("Loaded DEM from %s: shape=%s, crs=%s", path, data.shape, meta["crs"])
    return data, meta


def reproject_dem(
    data: np.ndarray,
    src_meta: dict,
    dst_crs: str = CRS_INTERNAL,
) -> tuple[np.ndarray, dict]:
    """將 DEM 投影轉換至目標座標系。

    Args:
        data: 光柵資料陣列。
        src_meta: 來源中繼資料。
        dst_crs: 目標座標系（預設 EPSG:3826）。

    Returns:
        (reprojected_data, new_metadata) 元組。
    """
    src_crs = src_meta["crs"]
    if str(src_crs) == dst_crs:
        logger.info("DEM already in %s, skipping reprojection", dst_crs)
        return data, src_meta

    transform, width, height = calculate_default_transform(
        src_crs, dst_crs, src_meta["width"], src_meta["height"],
        *rasterio.transform.array_bounds(
            src_meta["height"], src_meta["width"], src_meta["transform"]
        ),
    )

    dst_meta = src_meta.copy()
    dst_meta.update({
        "crs": dst_crs,
        "transform": transform,
        "width": width,
        "height": height,
    })

    dst_data = np.empty((height, width), dtype=data.dtype)
    reproject(
        source=data,
        destination=dst_data,
        src_transform=src_meta["transform"],
        src_crs=src_crs,
        dst_transform=transform,
        dst_crs=dst_crs,
        resampling=Resampling.bilinear,
    )

    logger.info("Reprojected DEM from %s to %s", src_crs, dst_crs)
    return dst_data, dst_meta


def clip_dem_to_city(
    data: np.ndarray,
    meta: dict,
    city: str,
) -> tuple[np.ndarray, dict]:
    """裁切 DEM 至城市邊界。

    Args:
        data: 光柵資料（需已在 EPSG:3826）。
        meta: 光柵中繼資料。
        city: 城市名稱。

    Returns:
        (clipped_data, clipped_metadata) 元組。
    """
    from pyproj import Transformer

    config = get_city_config(city)
    minx, miny, maxx, maxy = config.bounds_4326

    # 轉換邊界至 EPSG:3826
    transformer = Transformer.from_crs("EPSG:4326", CRS_INTERNAL, always_xy=True)
    minx_m, miny_m = transformer.transform(minx, miny)
    maxx_m, maxy_m = transformer.transform(maxx, maxy)

    clip_geom = box(minx_m, miny_m, maxx_m, maxy_m)

    with rasterio.MemoryFile() as memfile:
        with memfile.open(**meta) as dataset:
            dataset.write(data, 1)

        with memfile.open() as dataset:
            clipped, clipped_transform = rasterio_mask(
                dataset, [clip_geom], crop=True
            )

    clipped_meta = meta.copy()
    clipped_meta.update({
        "height": clipped.shape[1],
        "width": clipped.shape[2],
        "transform": clipped_transform,
    })

    logger.info("Clipped DEM to %s bounds: shape=%s", city, clipped.shape)
    return clipped[0], clipped_meta


def preprocess_terrain(
    input_path: Path | str,
    output_path: Path | str | None = None,
    city: str = "taipei",
    terrain_type: str = "dtm",
) -> Path:
    """完整地形預處理 pipeline。

    Args:
        input_path: 原始 DEM/DSM 路徑。
        output_path: 輸出路徑。
        city: 城市名稱。
        terrain_type: "dtm" 或 "dsm"。

    Returns:
        輸出檔案路徑。
    """
    data, meta = load_dem(input_path)
    data, meta = reproject_dem(data, meta)
    data, meta = clip_dem_to_city(data, meta, city)

    if output_path is None:
        output_path = PROCESSED_DIR / "terrain" / f"{city}_{terrain_type}.tif"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    meta["driver"] = "GTiff"
    with rasterio.open(output_path, "w", **meta) as dst:
        dst.write(data, 1)

    logger.info("Saved processed %s to %s", terrain_type, output_path)
    return output_path


def download_copernicus_dem(
    city: str = "taipei",
    output_dir: Path | str | None = None,
) -> Path:
    """從 AWS S3 下載 Copernicus GLO-30 DEM 對應的 tile。

    Copernicus DEM 30m 以 1°×1° tile 儲存於 S3 公開桶。
    檔名格式: Copernicus_DSM_COG_10_N{lat}_00_E{lon}_00_DEM.tif

    Args:
        city: 城市名稱（決定下載範圍）。
        output_dir: 下載目標目錄。

    Returns:
        合併後的 GeoTIFF 路徑。
    """
    import math

    config = get_city_config(city)
    minx, miny, maxx, maxy = config.bounds_4326

    if output_dir is None:
        output_dir = RAW_DIR / "terrain" / "copernicus"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 計算需要哪些 1°×1° tiles
    lat_start = math.floor(miny)
    lat_end = math.floor(maxy)
    lon_start = math.floor(minx)
    lon_end = math.floor(maxx)

    tile_paths: list[Path] = []

    for lat in range(lat_start, lat_end + 1):
        for lon in range(lon_start, lon_end + 1):
            ns = "N" if lat >= 0 else "S"
            ew = "E" if lon >= 0 else "W"
            lat_str = f"{abs(lat):02d}"
            lon_str = f"{abs(lon):03d}"

            tile_name = f"Copernicus_DSM_COG_10_{ns}{lat_str}_00_{ew}{lon_str}_00_DEM.tif"
            s3_url = f"https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com/{tile_name}"

            local_path = output_dir / tile_name

            if local_path.exists():
                logger.info("Tile already downloaded: %s", local_path.name)
                tile_paths.append(local_path)
                continue

            logger.info("Downloading Copernicus DEM tile: %s", tile_name)
            try:
                import requests
                response = requests.get(s3_url, timeout=120, stream=True)
                response.raise_for_status()

                with open(local_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                logger.info("Downloaded: %s (%.1f MB)", tile_name, local_path.stat().st_size / 1e6)
                tile_paths.append(local_path)
            except Exception as e:
                logger.warning("Failed to download %s: %s", tile_name, e)

    if not tile_paths:
        raise FileNotFoundError(f"No Copernicus DEM tiles downloaded for {city}")

    # 若只有一個 tile 直接返回
    if len(tile_paths) == 1:
        logger.info("Single tile covers the area: %s", tile_paths[0].name)
        return tile_paths[0]

    # 合併多個 tiles
    from rasterio.merge import merge

    merged_path = output_dir / f"{city}_copernicus_merged.tif"
    datasets = [rasterio.open(p) for p in tile_paths]

    try:
        merged_data, merged_transform = merge(datasets)
        merged_meta = datasets[0].meta.copy()
        merged_meta.update({
            "driver": "GTiff",
            "height": merged_data.shape[1],
            "width": merged_data.shape[2],
            "transform": merged_transform,
        })

        with rasterio.open(merged_path, "w", **merged_meta) as dst:
            dst.write(merged_data)

        logger.info("Merged %d tiles to %s", len(tile_paths), merged_path)
    finally:
        for ds in datasets:
            ds.close()

    return merged_path


def download_and_process_copernicus(
    city: str = "taipei",
) -> Path:
    """完整 Copernicus DEM 工作流：下載 → 重投影 → 裁切。

    Returns:
        處理後的 GeoTIFF 路徑。
    """
    raw_path = download_copernicus_dem(city)
    output_path = preprocess_terrain(raw_path, city=city, terrain_type="dsm_copernicus")
    return output_path


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    city = sys.argv[sys.argv.index("--city") + 1] if "--city" in sys.argv else "taipei"
    input_dir = RAW_DIR / "terrain"
    preprocess_terrain(input_dir, city=city)
