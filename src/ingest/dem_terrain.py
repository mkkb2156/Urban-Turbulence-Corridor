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


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    city = sys.argv[sys.argv.index("--city") + 1] if "--city" in sys.argv else "taipei"
    input_dir = RAW_DIR / "terrain"
    preprocess_terrain(input_dir, city=city)
