"""ESA WorldCover 2021 土地覆蓋資料下載與處理。

10m 解析度全球土地覆蓋分類，用於判定地表粗糙度 z₀。

來源: https://worldcover2021.esa.int
格式: GeoTIFF (Cloud Optimized)
座標系: EPSG:4326

Classification:
    10 = Tree cover           → z₀ = 1.0
    20 = Shrubland             → z₀ = 0.3
    30 = Grassland             → z₀ = 0.03
    40 = Cropland              → z₀ = 0.05
    50 = Built-up              → z₀ = 1.0
    60 = Bare / sparse veg     → z₀ = 0.005
    70 = Snow and ice          → z₀ = 0.001
    80 = Permanent water       → z₀ = 0.0002
    90 = Herbaceous wetland    → z₀ = 0.05
    95 = Mangroves             → z₀ = 0.5
   100 = Moss and lichen       → z₀ = 0.01

Usage:
    python -m src.ingest.esa_worldcover --city taipei
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

# ESA WorldCover class → roughness length z₀ (m)
WORLDCOVER_ROUGHNESS: dict[int, float] = {
    10: 1.0,      # Tree cover
    20: 0.3,      # Shrubland
    30: 0.03,     # Grassland
    40: 0.05,     # Cropland
    50: 1.0,      # Built-up
    60: 0.005,    # Bare / sparse vegetation
    70: 0.001,    # Snow and ice
    80: 0.0002,   # Permanent water bodies
    90: 0.05,     # Herbaceous wetland
    95: 0.5,      # Mangroves
    100: 0.01,    # Moss and lichen
}

# ESA WorldCover class → 零平面位移 zd (m)
WORLDCOVER_DISPLACEMENT: dict[int, float] = {
    10: 8.0,      # Tree cover — assume 12m avg height → zd ≈ 0.67*H
    20: 1.0,
    30: 0.0,
    40: 0.0,
    50: 15.0,     # Built-up — assume urban avg ≈ 22m → zd ≈ 0.67*H
    60: 0.0,
    70: 0.0,
    80: 0.0,
    90: 0.0,
    95: 4.0,
    100: 0.0,
}

# S3 tile naming pattern
# ESA_WorldCover_10m_2021_v200_{ew}{lon}{ns}{lat}_Map.tif
WORLDCOVER_S3_BASE = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/"


def _tile_name(lon: int, lat: int) -> str:
    """Generate ESA WorldCover tile filename for given 3°×3° block."""
    ns = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    return f"ESA_WorldCover_10m_2021_v200_{ns}{abs(lat):02d}{ew}{abs(lon):03d}_Map.tif"


def download_worldcover(
    city: str = "taipei",
    output_dir: Path | str | None = None,
) -> list[Path]:
    """下載涵蓋城市範圍的 ESA WorldCover tiles。

    WorldCover tiles 以 3°×3° 為單位（左下角座標對齊到 3 的倍數）。
    """
    import math
    import requests

    config = get_city_config(city)
    minx, miny, maxx, maxy = config.bounds_4326

    if output_dir is None:
        output_dir = RAW_DIR / "landcover" / "worldcover"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 計算所需 3°×3° tiles（左下角對齊到 3 的倍數）
    lon_start = int(math.floor(minx / 3) * 3)
    lon_end = int(math.floor(maxx / 3) * 3)
    lat_start = int(math.floor(miny / 3) * 3)
    lat_end = int(math.floor(maxy / 3) * 3)

    tile_paths: list[Path] = []
    for lat in range(lat_start, lat_end + 1, 3):
        for lon in range(lon_start, lon_end + 1, 3):
            name = _tile_name(lon, lat)
            url = f"{WORLDCOVER_S3_BASE}{name}"
            local = output_dir / name

            if local.exists():
                logger.info("WorldCover tile exists: %s", name)
                tile_paths.append(local)
                continue

            logger.info("Downloading WorldCover tile: %s", name)
            try:
                resp = requests.get(url, timeout=300, stream=True)
                resp.raise_for_status()
                with open(local, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=16384):
                        f.write(chunk)
                logger.info("Downloaded: %s (%.1f MB)", name, local.stat().st_size / 1e6)
                tile_paths.append(local)
            except Exception as e:
                logger.warning("Failed to download %s: %s", name, e)

    return tile_paths


def process_worldcover(
    input_path: Path | str,
    city: str = "taipei",
    output_path: Path | str | None = None,
) -> Path:
    """裁切 + 重投影 WorldCover tile 至城市範圍。

    Args:
        input_path: WorldCover GeoTIFF 路徑。
        city: 城市名稱。
        output_path: 輸出路徑。

    Returns:
        處理後的 GeoTIFF 路徑（EPSG:3826）。
    """
    config = get_city_config(city)
    minx, miny, maxx, maxy = config.bounds_4326

    with rasterio.open(input_path) as src:
        # 裁切到城市邊界（加一點 buffer）
        clip_geom = box(minx - 0.01, miny - 0.01, maxx + 0.01, maxy + 0.01)
        clipped, clipped_transform = rasterio_mask(src, [clip_geom], crop=True)
        clipped_meta = src.meta.copy()
        clipped_meta.update({
            "height": clipped.shape[1],
            "width": clipped.shape[2],
            "transform": clipped_transform,
        })

    # 重投影到 EPSG:3826
    transform, width, height = calculate_default_transform(
        clipped_meta["crs"], CRS_INTERNAL,
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
        src_crs=clipped_meta["crs"],
        dst_transform=transform,
        dst_crs=CRS_INTERNAL,
        resampling=Resampling.nearest,  # 分類資料用最近鄰
    )

    if output_path is None:
        output_path = PROCESSED_DIR / "landcover" / f"{city}_worldcover.tif"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(output_path, "w", **dst_meta) as dst:
        dst.write(dst_data, 1)

    # 統計
    unique, counts = np.unique(dst_data[dst_data > 0], return_counts=True)
    class_names = {
        10: "Tree", 20: "Shrub", 30: "Grass", 40: "Crop",
        50: "Built-up", 60: "Bare", 80: "Water", 90: "Wetland",
    }
    for cls, cnt in zip(unique, counts):
        name = class_names.get(int(cls), f"Class_{int(cls)}")
        logger.info("  %s: %d pixels (%.1f%%)", name, cnt, cnt / counts.sum() * 100)

    logger.info("Saved WorldCover to %s", output_path)
    return output_path


def worldcover_to_roughness(
    worldcover_path: Path | str,
    output_path: Path | str | None = None,
) -> Path:
    """將 WorldCover 分類轉換為粗糙度 z₀ 光柵。

    Returns:
        z₀ GeoTIFF 路徑。
    """
    with rasterio.open(worldcover_path) as src:
        data = src.read(1)
        meta = src.meta.copy()

    z0 = np.full_like(data, 0.3, dtype=np.float32)
    for cls, roughness in WORLDCOVER_ROUGHNESS.items():
        z0[data == cls] = roughness

    meta["dtype"] = "float32"

    if output_path is None:
        output_path = Path(worldcover_path).parent / (Path(worldcover_path).stem.replace("worldcover", "roughness_z0") + ".tif")
    output_path = Path(output_path)

    with rasterio.open(output_path, "w", **meta) as dst:
        dst.write(z0, 1)

    logger.info("Saved roughness z₀ raster to %s", output_path)
    return output_path


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    city = sys.argv[sys.argv.index("--city") + 1] if "--city" in sys.argv else "taipei"

    tiles = download_worldcover(city)
    if tiles:
        wc_path = process_worldcover(tiles[0], city=city)
        worldcover_to_roughness(wc_path)
