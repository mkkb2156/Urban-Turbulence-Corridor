"""網格化系統。

建立分析用的正方形網格，支援不同城市與網格大小。
預設 100m × 100m，以城市 bounding box 左下角對齊。
網格 ID 格式: {city}_{row:03d}_{col:03d}
"""

from __future__ import annotations

import logging
from pathlib import Path

import geopandas as gpd
import numpy as np
from pyproj import Transformer
from shapely.geometry import box

from config.settings import CRS_INTERNAL, DEFAULT_GRID_SIZE, OUTPUT_DIR, get_city_config

logger = logging.getLogger(__name__)


def create_grid(
    bounds: tuple[float, float, float, float] | None = None,
    cell_size: int = DEFAULT_GRID_SIZE,
    crs: str = CRS_INTERNAL,
    city: str = "taipei",
) -> gpd.GeoDataFrame:
    """建立正方形分析網格。

    Args:
        bounds: (minx, miny, maxx, maxy) 邊界，需為 EPSG:3826 座標。
                None 時使用城市設定的邊界。
        cell_size: 網格邊長（公尺）。
        crs: 座標參考系統。
        city: 城市名稱（用於自動取得邊界與 ID 前綴）。

    Returns:
        網格 GeoDataFrame，含 'grid_id'、'geometry'、'row'、'col' 欄位。
    """
    if bounds is None:
        config = get_city_config(city)
        minx_4326, miny_4326, maxx_4326, maxy_4326 = config.bounds_4326
        transformer = Transformer.from_crs("EPSG:4326", CRS_INTERNAL, always_xy=True)
        minx, miny = transformer.transform(minx_4326, miny_4326)
        maxx, maxy = transformer.transform(maxx_4326, maxy_4326)
    else:
        minx, miny, maxx, maxy = bounds

    # 對齊至 cell_size 倍數
    minx = np.floor(minx / cell_size) * cell_size
    miny = np.floor(miny / cell_size) * cell_size
    maxx = np.ceil(maxx / cell_size) * cell_size
    maxy = np.ceil(maxy / cell_size) * cell_size

    cols = int((maxx - minx) / cell_size)
    rows = int((maxy - miny) / cell_size)

    logger.info(
        "Creating %d×%d grid (%d cells) with cell_size=%dm for %s",
        rows, cols, rows * cols, cell_size, city,
    )

    grid_cells = []
    grid_ids = []
    row_indices = []
    col_indices = []

    for r in range(rows):
        for c in range(cols):
            x0 = minx + c * cell_size
            y0 = miny + r * cell_size
            x1 = x0 + cell_size
            y1 = y0 + cell_size
            grid_cells.append(box(x0, y0, x1, y1))
            grid_ids.append(f"{city}_{r:03d}_{c:03d}")
            row_indices.append(r)
            col_indices.append(c)

    gdf = gpd.GeoDataFrame(
        {
            "grid_id": grid_ids,
            "row": row_indices,
            "col": col_indices,
        },
        geometry=grid_cells,
        crs=crs,
    )

    logger.info("Created grid with %d cells", len(gdf))
    return gdf


def clip_grid_to_boundary(
    grid: gpd.GeoDataFrame,
    boundary: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """裁切網格至城市行政邊界。

    Args:
        grid: 完整矩形網格。
        boundary: 城市行政邊界 GeoDataFrame。

    Returns:
        只保留與邊界相交的網格。
    """
    boundary = boundary.to_crs(grid.crs)
    boundary_union = boundary.union_all()
    mask = grid.intersects(boundary_union)
    result = grid[mask].copy()
    logger.info("Clipped grid from %d to %d cells", len(grid), len(result))
    return result


def save_grid(
    grid: gpd.GeoDataFrame,
    output_path: Path | str | None = None,
    city: str = "taipei",
) -> Path:
    """儲存網格至 GeoPackage。

    Args:
        grid: 網格 GeoDataFrame。
        output_path: 輸出路徑。
        city: 城市名稱。

    Returns:
        輸出檔案路徑。
    """
    if output_path is None:
        output_path = OUTPUT_DIR / f"{city}_grid.gpkg"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    grid.to_file(output_path, driver="GPKG")
    logger.info("Saved grid (%d cells) to %s", len(grid), output_path)
    return output_path


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    city = sys.argv[sys.argv.index("--city") + 1] if "--city" in sys.argv else "taipei"
    size = int(sys.argv[sys.argv.index("--size") + 1]) if "--size" in sys.argv else DEFAULT_GRID_SIZE
    grid = create_grid(cell_size=size, city=city)
    save_grid(grid, city=city)
