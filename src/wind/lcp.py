"""Least Cost Path（LCP）風廊辨識。

流程：
1. 將 FAI(θ) 光柵化為阻力面（cost surface）
2. 定義風源點（source points）：城市上風側邊界、河川、大型空地
3. 執行 cost-distance 分析
4. 從下風側回溯最低成本路徑
5. 路徑經過的網格 = 風廊候選區

使用 scipy 的 shortest_path / minimum_cost_path 實作，
不依賴 GRASS GIS。
"""

from __future__ import annotations

import logging
from typing import Sequence

import geopandas as gpd
import numpy as np
from scipy.ndimage import label as ndimage_label
from scipy.sparse.csgraph import shortest_path
from shapely.geometry import LineString, Point

from config.settings import CRS_INTERNAL

logger = logging.getLogger(__name__)


def fai_to_cost_surface(
    grid: gpd.GeoDataFrame,
    fai_col: str = "fai_ne",
    min_cost: float = 1.0,
    fai_weight: float = 10.0,
) -> tuple[np.ndarray, dict]:
    """將 FAI 網格轉換為阻力面。

    低 FAI = 低阻力（風容易通過）。
    高 FAI = 高阻力（建物密集阻擋風流）。

    Args:
        grid: 含 FAI 欄位的分析網格。
        fai_col: FAI 欄位名稱。
        min_cost: 最小阻力值。
        fai_weight: FAI 對阻力的權重。

    Returns:
        (cost_array, index_map) — 2D 阻力陣列與 grid_id 對照。
    """
    if fai_col not in grid.columns:
        raise ValueError(f"Grid must have '{fai_col}' column")

    rows = grid["row"].max() + 1
    cols = grid["col"].max() + 1

    cost = np.full((rows, cols), np.inf)
    index_map = {}

    for _, cell in grid.iterrows():
        r, c = int(cell["row"]), int(cell["col"])
        fai = cell[fai_col]
        cost[r, c] = min_cost + fai * fai_weight
        index_map[(r, c)] = cell["grid_id"]

    # 用中位數填補 inf（有效網格外的區域）
    valid = cost[cost < np.inf]
    if len(valid) > 0:
        fill_val = np.median(valid) * 2
        cost[cost == np.inf] = fill_val

    logger.info(
        "Cost surface: shape=%s, min=%.2f, max=%.2f, mean=%.2f",
        cost.shape, cost.min(), cost.max(), cost.mean(),
    )

    return cost, index_map


def compute_cost_distance(
    cost_surface: np.ndarray,
    source_cells: list[tuple[int, int]],
) -> np.ndarray:
    """計算從風源點到所有網格的累積最低成本距離。

    使用 8 連通鄰域（含對角線），對角線距離為 √2 倍。

    Args:
        cost_surface: 2D 阻力面陣列。
        source_cells: 風源點的 (row, col) 列表。

    Returns:
        2D 累積成本距離陣列。
    """
    rows, cols = cost_surface.shape
    n = rows * cols

    # 建立鄰接矩陣（稀疏）
    from scipy.sparse import lil_matrix

    graph = lil_matrix((n, n), dtype=np.float64)

    # 8 連通方向：(dr, dc, distance_factor)
    neighbors = [
        (-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),  # 4-連通
        (-1, -1, 1.414), (-1, 1, 1.414), (1, -1, 1.414), (1, 1, 1.414),  # 對角線
    ]

    for r in range(rows):
        for c in range(cols):
            idx = r * cols + c
            for dr, dc, dist_factor in neighbors:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    nidx = nr * cols + nc
                    # 成本 = 兩點成本平均 × 距離
                    avg_cost = (cost_surface[r, c] + cost_surface[nr, nc]) / 2
                    graph[idx, nidx] = avg_cost * dist_factor

    graph = graph.tocsr()

    # 從所有源點計算最短路徑
    source_indices = [r * cols + c for r, c in source_cells]

    cost_distance = np.full((rows, cols), np.inf)

    for src_idx in source_indices:
        distances = shortest_path(graph, directed=False, indices=src_idx)
        cost_2d = distances.reshape(rows, cols)
        cost_distance = np.minimum(cost_distance, cost_2d)

    logger.info(
        "Cost distance: min=%.2f, max=%.2f (excl inf)",
        cost_distance[cost_distance < np.inf].min() if np.any(cost_distance < np.inf) else 0,
        cost_distance[cost_distance < np.inf].max() if np.any(cost_distance < np.inf) else 0,
    )

    return cost_distance


def trace_least_cost_path(
    cost_distance: np.ndarray,
    cost_surface: np.ndarray,
    target_cell: tuple[int, int],
) -> list[tuple[int, int]]:
    """從目標點回溯最低成本路徑。

    Args:
        cost_distance: 累積成本距離陣列。
        cost_surface: 原始阻力面。
        target_cell: 目標點 (row, col)。

    Returns:
        路徑上的 (row, col) 列表（從目標到源點）。
    """
    rows, cols = cost_distance.shape
    path = [target_cell]
    current = target_cell

    neighbors = [
        (-1, 0), (1, 0), (0, -1), (0, 1),
        (-1, -1), (-1, 1), (1, -1), (1, 1),
    ]

    max_steps = rows * cols  # 防止無窮迴圈
    for _ in range(max_steps):
        r, c = current
        best_neighbor = None
        best_cost = cost_distance[r, c]

        for dr, dc in neighbors:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                if cost_distance[nr, nc] < best_cost:
                    best_cost = cost_distance[nr, nc]
                    best_neighbor = (nr, nc)

        if best_neighbor is None:
            break  # 到達源點或無法前進
        path.append(best_neighbor)
        current = best_neighbor

    return path


def identify_wind_corridors(
    grid: gpd.GeoDataFrame,
    fai_col: str = "fai_ne",
    source_cells: list[tuple[int, int]] | None = None,
    target_cells: list[tuple[int, int]] | None = None,
    n_corridors: int = 10,
) -> gpd.GeoDataFrame:
    """辨識風廊路徑。

    Args:
        grid: 含 FAI 欄位的分析網格。
        fai_col: FAI 欄位名稱。
        source_cells: 風源點 (row, col)，None 時使用上邊界。
        target_cells: 目標點 (row, col)，None 時使用下邊界。
        n_corridors: 最大風廊數量。

    Returns:
        風廊 GeoDataFrame，含路徑幾何與成本資訊。
    """
    cost_surface, index_map = fai_to_cost_surface(grid, fai_col)
    rows_max = grid["row"].max()
    cols_max = grid["col"].max()

    # 預設源點：上邊界（假設東北季風從北方進入）
    if source_cells is None:
        source_cells = [(0, c) for c in range(cols_max + 1)]
        source_cells = [(r, c) for r, c in source_cells if (r, c) in index_map]

    # 預設目標點：下邊界
    if target_cells is None:
        target_cells = [(rows_max, c) for c in range(cols_max + 1)]
        target_cells = [(r, c) for r, c in target_cells if (r, c) in index_map]

    if not source_cells or not target_cells:
        logger.warning("No valid source or target cells, returning empty corridors")
        return gpd.GeoDataFrame(columns=["corridor_id", "geometry", "total_cost"])

    logger.info(
        "Computing cost distance from %d source cells to %d targets",
        len(source_cells), len(target_cells),
    )

    cost_distance = compute_cost_distance(cost_surface, source_cells)

    # 從每個目標點回溯路徑
    corridors = []
    for i, target in enumerate(target_cells[:n_corridors]):
        path = trace_least_cost_path(cost_distance, cost_surface, target)
        if len(path) < 2:
            continue

        # 轉換路徑座標回地理座標
        grid_centroids = grid.set_index(["row", "col"]).geometry.centroid
        path_coords = []
        for r, c in path:
            if (r, c) in grid_centroids.index:
                pt = grid_centroids.loc[(r, c)]
                path_coords.append((pt.x, pt.y))

        if len(path_coords) >= 2:
            total_cost = sum(cost_surface[r, c] for r, c in path)
            corridors.append({
                "corridor_id": f"corridor_{i:03d}",
                "geometry": LineString(path_coords),
                "total_cost": total_cost,
                "length_cells": len(path),
                "path_cells": [index_map.get((r, c), "") for r, c in path],
            })

    # 排序：低成本 = 更好的風廊
    corridors.sort(key=lambda x: x["total_cost"])

    gdf = gpd.GeoDataFrame(corridors, crs=CRS_INTERNAL)
    logger.info("Identified %d wind corridors", len(gdf))

    return gdf


def corridors_to_grid_mask(
    grid: gpd.GeoDataFrame,
    corridors: gpd.GeoDataFrame,
    buffer_distance: float = 50.0,
) -> gpd.GeoDataFrame:
    """標記網格是否位於風廊上。

    Args:
        grid: 分析網格。
        corridors: 風廊 GeoDataFrame。
        buffer_distance: 風廊緩衝區距離（公尺）。

    Returns:
        grid 新增 'is_corridor' 與 'corridor_rank' 欄位。
    """
    grid = grid.copy()
    grid["is_corridor"] = False
    grid["corridor_rank"] = -1

    if corridors.empty:
        return grid

    for rank, (_, corridor) in enumerate(corridors.iterrows()):
        buffer = corridor.geometry.buffer(buffer_distance)
        mask = grid.intersects(buffer)
        grid.loc[mask & ~grid["is_corridor"], "corridor_rank"] = rank
        grid.loc[mask, "is_corridor"] = True

    logger.info(
        "Corridor cells: %d / %d (%.1f%%)",
        grid["is_corridor"].sum(),
        len(grid),
        grid["is_corridor"].sum() / len(grid) * 100,
    )

    return grid


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    city = sys.argv[sys.argv.index("--city") + 1] if "--city" in sys.argv else "taipei"
    season = sys.argv[sys.argv.index("--season") + 1] if "--season" in sys.argv else "northeast"
    logger.info("LCP analysis for %s, season=%s", city, season)
