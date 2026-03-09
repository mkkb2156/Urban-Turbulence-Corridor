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
import pandas as pd
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


def _direction_to_boundaries(
    wind_direction_deg: float,
    rows_max: int,
    cols_max: int,
    index_map: dict,
) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """根據風向角度自動決定 source（上風側）與 target（下風側）邊界。

    風從 source 吹向 target。例如 NE 風（45°）從北/東邊進入，往南/西邊吹。

    Args:
        wind_direction_deg: 風向角度（氣象慣例，0=N, 90=E, 180=S, 270=W）。
        rows_max: 網格最大行號。
        cols_max: 網格最大列號。
        index_map: (row, col) → grid_id 對照。

    Returns:
        (source_cells, target_cells) — 各為 (row, col) 列表。
    """
    # 正規化到 0-360
    d = wind_direction_deg % 360

    # 根據風向決定邊界：風從 source 側進入
    # 行號：0=北，rows_max=南
    # 列號：0=西，cols_max=東
    north = [(0, c) for c in range(cols_max + 1)]
    south = [(rows_max, c) for c in range(cols_max + 1)]
    east = [(r, cols_max) for r in range(rows_max + 1)]
    west = [(r, 0) for r in range(rows_max + 1)]

    if 337.5 <= d or d < 22.5:       # N
        source, target = north, south
    elif 22.5 <= d < 67.5:            # NE
        source, target = north + east, south + west
    elif 67.5 <= d < 112.5:           # E
        source, target = east, west
    elif 112.5 <= d < 157.5:          # SE
        source, target = south + east, north + west
    elif 157.5 <= d < 202.5:          # S
        source, target = south, north
    elif 202.5 <= d < 247.5:          # SW
        source, target = south + west, north + east
    elif 247.5 <= d < 292.5:          # W
        source, target = west, east
    else:                              # NW (292.5-337.5)
        source, target = north + west, south + east

    # 過濾只保留有效的網格座標
    source = [(r, c) for r, c in source if (r, c) in index_map]
    target = [(r, c) for r, c in target if (r, c) in index_map]

    return source, target


def _direction_to_fai_col(wind_direction_deg: float, grid: gpd.GeoDataFrame) -> str:
    """根據風向選擇最適合的 FAI 欄位。

    Args:
        wind_direction_deg: 風向角度。
        grid: 網格 GeoDataFrame。

    Returns:
        FAI 欄位名稱。
    """
    d = wind_direction_deg % 360
    # NE 季風 (0-90°) 用 fai_ne；SW 季風 (180-270°) 用 fai_sw
    if 135 <= d < 315 and "fai_sw" in grid.columns:
        return "fai_sw"
    if "fai_ne" in grid.columns:
        return "fai_ne"
    # 其他 FAI 方向欄位名稱 fallback
    fai_cols = [c for c in grid.columns if c.startswith("fai_")]
    return fai_cols[0] if fai_cols else "fai_ne"


def identify_wind_corridors(
    grid: gpd.GeoDataFrame,
    fai_col: str | None = None,
    source_cells: list[tuple[int, int]] | None = None,
    target_cells: list[tuple[int, int]] | None = None,
    n_corridors: int = 10,
    wind_direction: float | None = None,
) -> gpd.GeoDataFrame:
    """辨識風廊路徑。

    Args:
        grid: 含 FAI 欄位的分析網格。
        fai_col: FAI 欄位名稱，None 時根據 wind_direction 自動選擇。
        source_cells: 風源點 (row, col)，None 時根據 wind_direction 自動決定。
        target_cells: 目標點 (row, col)，None 時根據 wind_direction 自動決定。
        n_corridors: 最大風廊數量。
        wind_direction: 風向角度（氣象慣例 0=N），None 時預設 NE (45°)。

    Returns:
        風廊 GeoDataFrame，含路徑幾何與成本資訊。
    """
    if wind_direction is None:
        wind_direction = 45.0  # 預設東北季風

    if fai_col is None:
        fai_col = _direction_to_fai_col(wind_direction, grid)

    cost_surface, index_map = fai_to_cost_surface(grid, fai_col)
    rows_max = grid["row"].max()
    cols_max = grid["col"].max()

    # 根據風向自動決定 source/target 邊界
    if source_cells is None or target_cells is None:
        auto_source, auto_target = _direction_to_boundaries(
            wind_direction, rows_max, cols_max, index_map,
        )
        if source_cells is None:
            source_cells = auto_source
        if target_cells is None:
            target_cells = auto_target

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
                "wind_direction_deg": wind_direction,
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


def identify_corridors_multi_direction(
    grid: gpd.GeoDataFrame,
    directions: list[float] | None = None,
    n_corridors_per_direction: int = 5,
    n_corridors_total: int = 10,
) -> gpd.GeoDataFrame:
    """辨識多風向風廊並合併去重。

    Args:
        grid: 含 FAI 欄位的分析網格。
        directions: 風向角度列表，None 時使用 NE + SW 兩季風方向。
        n_corridors_per_direction: 每個方向最大風廊數。
        n_corridors_total: 合併後最大風廊數。

    Returns:
        合併去重後的風廊 GeoDataFrame。
    """
    if directions is None:
        directions = [45.0, 225.0]  # NE + SW 台灣兩大季風

    all_corridors = []
    for direction in directions:
        gdf = identify_wind_corridors(
            grid,
            n_corridors=n_corridors_per_direction,
            wind_direction=direction,
        )
        if not gdf.empty:
            # 加上方向前綴避免 ID 衝突
            dir_label = _deg_to_label(direction)
            gdf["corridor_id"] = gdf["corridor_id"].apply(
                lambda cid: f"{dir_label}_{cid}",
            )
            all_corridors.append(gdf)

    if not all_corridors:
        return gpd.GeoDataFrame(
            columns=["corridor_id", "geometry", "total_cost", "wind_direction_deg"],
        )

    merged = gpd.GeoDataFrame(
        pd.concat(all_corridors, ignore_index=True),
        crs=CRS_INTERNAL,
    )

    # 去重：移除空間上高度重疊的風廊（>70% 重疊）
    merged = _deduplicate_corridors(merged, overlap_threshold=0.7)

    # 按成本排序取 top N
    merged = merged.sort_values("total_cost").head(n_corridors_total).reset_index(drop=True)

    logger.info(
        "Multi-direction corridors: %d directions → %d corridors",
        len(directions), len(merged),
    )
    return merged


def _deg_to_label(deg: float) -> str:
    """將角度轉換為風向標籤。"""
    labels = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = round(deg / 45) % 8
    return labels[idx]


def _deduplicate_corridors(
    corridors: gpd.GeoDataFrame,
    overlap_threshold: float = 0.7,
) -> gpd.GeoDataFrame:
    """移除空間上高度重疊的風廊。"""
    if len(corridors) <= 1:
        return corridors

    keep = [True] * len(corridors)
    buffer_dist = 100.0  # 100m buffer for overlap check

    for i in range(len(corridors)):
        if not keep[i]:
            continue
        geom_i = corridors.iloc[i].geometry.buffer(buffer_dist)
        for j in range(i + 1, len(corridors)):
            if not keep[j]:
                continue
            geom_j = corridors.iloc[j].geometry.buffer(buffer_dist)
            intersection = geom_i.intersection(geom_j).area
            smaller_area = min(geom_i.area, geom_j.area)
            if smaller_area > 0 and intersection / smaller_area > overlap_threshold:
                # 保留成本較低的那條
                if corridors.iloc[j]["total_cost"] < corridors.iloc[i]["total_cost"]:
                    keep[i] = False
                    break
                else:
                    keep[j] = False

    return corridors[keep].reset_index(drop=True)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    city = sys.argv[sys.argv.index("--city") + 1] if "--city" in sys.argv else "taipei"
    season = sys.argv[sys.argv.index("--season") + 1] if "--season" in sys.argv else "northeast"
    logger.info("LCP analysis for %s, season=%s", city, season)
