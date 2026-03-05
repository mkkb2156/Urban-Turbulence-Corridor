"""一鍵下載所有免費數據源。

在本機執行，自動下載並處理所有不需 API key 的數據。
需 API key 的來源（CWA、ERA5）會自動偵測 key 是否存在。

Usage:
    # 下載全部（不含 ERA5）
    python scripts/download_all_data.py --city taipei

    # 包含 ERA5（需要 ~/.cdsapirc）
    python scripts/download_all_data.py --city taipei --include-era5

    # 只下載特定類別
    python scripts/download_all_data.py --city taipei --only terrain,buildings
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

# 加入專案根目錄
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logger = logging.getLogger("download_all_data")


def step(name: str, func, *args, **kwargs) -> bool:
    """執行單一步驟，捕捉錯誤。"""
    logger.info("=" * 60)
    logger.info("📥 %s", name)
    logger.info("=" * 60)
    t0 = time.time()
    try:
        result = func(*args, **kwargs)
        elapsed = time.time() - t0
        logger.info("✅ %s — 完成 (%.1fs)", name, elapsed)
        return True
    except Exception as e:
        elapsed = time.time() - t0
        logger.error("❌ %s — 失敗 (%.1fs): %s", name, elapsed, e)
        return False


def download_terrain(city: str) -> None:
    """下載 Copernicus DEM 地形數據。"""
    from src.ingest.dem_terrain import download_and_process_copernicus
    download_and_process_copernicus(city)


def download_buildings(city: str) -> None:
    """下載 OSM 建築 + GHS-BUILT-H 高度填補。"""
    from src.ingest.osm_buildings import download_osm_buildings
    gdf = download_osm_buildings(city)

    # GHS-BUILT-H 高度填補（非關鍵，失敗不影響 OSM 建築）
    try:
        from src.ingest.ghs_built_h import (
            download_ghs_built_h,
            process_ghs_built_h,
            enrich_buildings_with_ghs,
        )
        from config.settings import PROCESSED_DIR

        raw_path = download_ghs_built_h()
        ghs_path = process_ghs_built_h(raw_path, city=city)

        buildings_path = PROCESSED_DIR / "buildings" / f"{city}_buildings.gpkg"
        if buildings_path.exists():
            enrich_buildings_with_ghs(buildings_path, ghs_path)
    except Exception as e:
        logger.warning("GHS-BUILT-H enrichment failed (non-critical): %s", e)
        logger.info("OSM buildings saved successfully without GHS height enrichment")


def download_landcover(city: str) -> None:
    """下載 ESA WorldCover 土地覆蓋。"""
    from src.ingest.esa_worldcover import (
        download_worldcover,
        process_worldcover,
        worldcover_to_roughness,
    )
    tiles = download_worldcover(city)
    if tiles:
        wc_path = process_worldcover(tiles[0], city=city)
        worldcover_to_roughness(wc_path)


def download_airspace(city: str) -> None:
    """建立無人機空域圖層。"""
    from src.ingest.caa_airspace import create_taipei_airspace_mock, save_airspace
    gdf = create_taipei_airspace_mock()
    save_airspace(gdf, city=city)


def download_era5(city: str, start_year: int, end_year: int | None) -> None:
    """下載 ERA5 再分析數據 + 計算氣候學統計。"""
    from src.ingest.era5 import fetch_era5_wind, compute_era5_climatology
    fetch_era5_wind(city, start_year=start_year, end_year=end_year)
    compute_era5_climatology(city, start_year=start_year, end_year=end_year)


def main():
    parser = argparse.ArgumentParser(description="UTC 一鍵資料下載")
    parser.add_argument("--city", default="taipei", help="城市名稱")
    parser.add_argument("--include-era5", action="store_true", help="包含 ERA5 下載（需 ~/.cdsapirc）")
    parser.add_argument("--era5-start", type=int, default=2020, help="ERA5 起始年份")
    parser.add_argument("--era5-end", type=int, default=None, help="ERA5 結束年份")
    parser.add_argument("--only", type=str, default=None, help="只下載指定類別（逗號分隔）: terrain,buildings,landcover,airspace,era5")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    city = args.city
    only = set(args.only.split(",")) if args.only else None

    logger.info("🌏 UTC 資料下載 — 城市: %s", city)
    logger.info("")

    results = {}
    t_start = time.time()

    # 1. 地形
    if only is None or "terrain" in only:
        results["Copernicus DEM 地形"] = step("Copernicus DEM 地形", download_terrain, city)

    # 2. 建築（OSM + GHS-BUILT-H）
    if only is None or "buildings" in only:
        results["OSM 建築 + GHS 高度"] = step("OSM 建築 + GHS-BUILT-H 高度填補", download_buildings, city)

    # 3. 土地覆蓋
    if only is None or "landcover" in only:
        results["ESA WorldCover"] = step("ESA WorldCover 土地覆蓋", download_landcover, city)

    # 4. 無人機空域
    if only is None or "airspace" in only:
        results["CAA 無人機空域"] = step("CAA 無人機空域圖層", download_airspace, city)

    # 5. ERA5（可選）
    if args.include_era5 or (only and "era5" in only):
        results["ERA5 再分析"] = step(
            "ERA5 再分析數據",
            download_era5, city, args.era5_start, args.era5_end,
        )

    # 摘要
    elapsed = time.time() - t_start
    logger.info("")
    logger.info("=" * 60)
    logger.info("📊 下載摘要 (%.0fs)", elapsed)
    logger.info("=" * 60)
    for name, ok in results.items():
        status = "✅" if ok else "❌"
        logger.info("  %s %s", status, name)

    success = sum(results.values())
    total = len(results)
    logger.info("")
    logger.info("完成 %d/%d 項", success, total)

    if success < total:
        logger.info("💡 失敗的項目可能需要額外安裝依賴: pip install -e '.[pipeline]'")


if __name__ == "__main__":
    main()
