#!/usr/bin/env python3
"""Phase 1 完整 pipeline 執行。

Usage:
    python scripts/run_pipeline.py --city taipei --grid-size 100
    python scripts/run_pipeline.py --city taipei_pilot --grid-size 100
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# 加入專案根目錄至 path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from config.settings import (
    DEFAULT_GRID_SIZE,
    DRONE_HEIGHTS,
    OUTPUT_DIR,
    PROCESSED_DIR,
    get_city_config,
)

logger = logging.getLogger("utc.pipeline")


def run_phase1_pipeline(
    city: str = "taipei",
    grid_size: int = DEFAULT_GRID_SIZE,
    reference_wind_speed: float = 6.0,
    skip_ingest: bool = False,
) -> Path:
    """執行 Phase 1 完整 pipeline。

    Steps:
    1. 建立分析網格
    2. 載入建物資料
    3. 計算 BCR
    4. 計算 FAI（16 方向）
    5. 計算 SVF
    6. 計算粗糙度參數
    7. 風速降尺度
    8. LCP 風廊辨識
    9. 風險分類
    10. 輸出結果

    Args:
        city: 城市名稱。
        grid_size: 網格大小（公尺）。
        reference_wind_speed: 參考風速（m/s）。
        skip_ingest: 跳過資料下載步驟。

    Returns:
        輸出檔案路徑。
    """
    config = get_city_config(city)
    logger.info("=" * 60)
    logger.info("UTC Phase 1 Pipeline — %s", config.name)
    logger.info("Grid size: %dm, Reference wind: %.1f m/s", grid_size, reference_wind_speed)
    logger.info("=" * 60)

    # Step 1: 建立分析網格
    logger.info("[1/9] Creating analysis grid...")
    from src.morphology.grid import create_grid

    grid = create_grid(cell_size=grid_size, city=city)
    logger.info("Grid: %d cells", len(grid))

    # Step 2: 載入建物資料
    logger.info("[2/9] Loading building data...")
    buildings_path = PROCESSED_DIR / "buildings" / f"{city}_buildings.gpkg"
    if not buildings_path.exists():
        logger.warning(
            "Processed buildings not found at %s. "
            "Run data ingestion first: python -m src.ingest.nlsc_buildings --city %s",
            buildings_path,
            city,
        )
        logger.info("Continuing with empty buildings for demonstration...")
        import geopandas as gpd

        buildings = gpd.GeoDataFrame(
            columns=["geometry", "height", "height_source"],
            geometry="geometry",
            crs="EPSG:3826",
        )
    else:
        import geopandas as gpd

        buildings = gpd.read_file(buildings_path)
        logger.info("Loaded %d buildings", len(buildings))

    # Step 3: 計算 BCR
    logger.info("[3/9] Computing BCR...")
    from src.morphology.bcr import compute_bcr

    grid = compute_bcr(buildings, grid)

    # Step 4: 計算 FAI（16 方向）
    logger.info("[4/9] Computing FAI (16 directions)...")
    from src.morphology.fai import compute_fai_all_directions

    grid = compute_fai_all_directions(buildings, grid)

    # Step 5: 計算 SVF
    logger.info("[5/9] Computing SVF...")
    from src.morphology.svf import estimate_svf_from_morphology

    grid = estimate_svf_from_morphology(grid, buildings)

    # Step 6: 計算粗糙度參數
    logger.info("[6/9] Computing roughness parameters...")
    from src.morphology.roughness import compute_roughness_params

    if "fai_ne" in grid.columns:
        grid = compute_roughness_params(grid, buildings, fai_col="fai_ne")
    else:
        logger.warning("FAI_NE not available, skipping roughness calculation")
        grid["z0"] = 0.03
        grid["zd"] = 0.0

    # Step 7: 風速降尺度
    logger.info("[7/9] Downscaling wind speed...")
    from src.wind.log_profile import downscale_wind_to_grid

    grid = downscale_wind_to_grid(
        grid,
        reference_speed=reference_wind_speed,
        target_heights=DRONE_HEIGHTS,
    )

    # Step 8: LCP 風廊辨識
    logger.info("[8/9] Identifying wind corridors (LCP)...")
    from src.wind.corridor import classify_corridors
    from src.wind.lcp import corridors_to_grid_mask, identify_wind_corridors

    fai_col = "fai_ne" if "fai_ne" in grid.columns else "fai_22.5"
    if fai_col in grid.columns:
        corridors = identify_wind_corridors(grid, fai_col=fai_col)
        corridors = classify_corridors(corridors)
        grid = corridors_to_grid_mask(grid, corridors)
    else:
        logger.warning("No FAI column for LCP, skipping corridor analysis")
        import geopandas as gpd

        corridors = gpd.GeoDataFrame(columns=["corridor_id", "geometry", "total_cost"])
        grid["is_corridor"] = False
        grid["corridor_rank"] = -1

    # Step 9: 風險分類
    logger.info("[9/9] Classifying wind risk...")
    from src.risk.classifier import classify_wind_risk
    from src.risk.score import compute_risk_score

    wind_col = "wind_50m" if "wind_50m" in grid.columns else None
    if wind_col:
        grid = classify_wind_risk(grid, wind_col=wind_col)
        grid = compute_risk_score(grid, wind_col=wind_col, fai_col=fai_col)
    else:
        grid["risk_level"] = "unknown"
        grid["risk_score"] = 0

    # Output
    output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    grid_output = output_dir / f"{city}_grid.gpkg"
    # 移除 list 類型欄位（GPKG 不支援）
    save_cols = [c for c in grid.columns if not isinstance(grid[c].iloc[0] if len(grid) > 0 else None, list)]
    grid[save_cols].to_file(grid_output, driver="GPKG")
    logger.info("Saved grid to %s", grid_output)

    if not corridors.empty:
        corridor_output = output_dir / f"{city}_corridors.gpkg"
        save_cols_c = [c for c in corridors.columns if not isinstance(corridors[c].iloc[0] if len(corridors) > 0 else None, list)]
        corridors[save_cols_c].to_file(corridor_output, driver="GPKG")
        logger.info("Saved corridors to %s", corridor_output)

    logger.info("=" * 60)
    logger.info("Pipeline complete! Output: %s", output_dir)
    logger.info("=" * 60)

    return grid_output


def main():
    parser = argparse.ArgumentParser(description="UTC Phase 1 Pipeline")
    parser.add_argument("--city", default="taipei", help="City name")
    parser.add_argument("--grid-size", type=int, default=DEFAULT_GRID_SIZE, help="Grid cell size (m)")
    parser.add_argument("--wind-speed", type=float, default=6.0, help="Reference wind speed (m/s)")
    parser.add_argument("--skip-ingest", action="store_true", help="Skip data ingestion")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    run_phase1_pipeline(
        city=args.city,
        grid_size=args.grid_size,
        reference_wind_speed=args.wind_speed,
        skip_ingest=args.skip_ingest,
    )


if __name__ == "__main__":
    main()
