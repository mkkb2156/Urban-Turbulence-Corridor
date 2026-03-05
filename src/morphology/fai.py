"""Frontal Area Index（FAI）計算。

FAI(θ) = Σ(建物垂直於 θ 方向的投影面積) / 網格地面面積

每個網格需計算 16 個方向的 FAI 值。FAI 是方向性指標，
東北季風（θ ≈ 22.5°–45°）與西南季風（θ ≈ 202.5°–225°）是台灣最關鍵的兩個方向。
"""

from __future__ import annotations

import logging

import geopandas as gpd
import numpy as np
from shapely.geometry import LineString

from config.settings import CRS_INTERNAL, WIND_DIRECTIONS_16

logger = logging.getLogger(__name__)


def _projected_width(geom, direction_rad: float) -> float:
    """計算建物輪廓在指定方向的投影寬度。

    將建物頂點投影到垂直於風向的軸上，取最大值與最小值之差。
    支援 Polygon 與 MultiPolygon。

    Args:
        geom: 建物 Shapely Polygon 或 MultiPolygon。
        direction_rad: 風的「來向」角度（弧度），0=N, π/2=E。

    Returns:
        投影寬度（公尺）。
    """
    from shapely.geometry import MultiPolygon

    if isinstance(geom, MultiPolygon):
        return max(_projected_width(p, direction_rad) for p in geom.geoms)

    # 垂直於風向的軸 = 風向 + 90°
    perp_rad = direction_rad + np.pi / 2

    # 投影軸的單位向量
    axis_x = np.sin(perp_rad)
    axis_y = np.cos(perp_rad)

    coords = np.array(geom.exterior.coords)
    projections = coords[:, 0] * axis_x + coords[:, 1] * axis_y

    return float(projections.max() - projections.min())


def compute_fai_single_direction(
    buildings: gpd.GeoDataFrame,
    grid: gpd.GeoDataFrame,
    wind_direction: float,
) -> gpd.GeoDataFrame:
    """計算指定風向的 Frontal Area Index。

    Args:
        buildings: 建物資料，需含 'geometry'（Polygon）與 'height'（float, m）欄位。
                   CRS 必須為 EPSG:3826。
        grid: 100m 網格，需含 'geometry'（Polygon）與 'grid_id'（str）欄位。
              CRS 必須為 EPSG:3826。
        wind_direction: 風向角度（0-360°，0°=N，順時針）。
                        代表「風吹來的方向」（氣象學慣例）。

    Returns:
        grid GeoDataFrame 新增 'fai_{direction}' 欄位（float, 0-1+）。

    Raises:
        ValueError: 若 buildings 缺少 height 欄位或 CRS 不正確。
    """
    if "height" not in buildings.columns:
        raise ValueError("Buildings GeoDataFrame must have a 'height' column")

    # 確認 CRS
    for name, gdf in [("buildings", buildings), ("grid", grid)]:
        if gdf.crs is None or gdf.crs.to_epsg() != 3826:
            raise ValueError(
                f"{name} CRS must be EPSG:3826, got {gdf.crs}. "
                "Use gdf.to_crs(epsg=3826) to convert."
            )

    direction_rad = np.radians(wind_direction)
    col_name = f"fai_{wind_direction:.1f}"

    logger.info("Computing FAI for wind direction %.1f°", wind_direction)

    # 空間交叉：找出每個網格包含哪些建物（處理跨網格建物）
    # 使用 overlay intersection 裁切跨網格建物
    buildings_with_height = buildings[["geometry", "height"]].copy()
    intersected = gpd.overlay(
        grid[["grid_id", "geometry"]],
        buildings_with_height,
        how="intersection",
    )

    if intersected.empty:
        grid[col_name] = 0.0
        return grid

    # 計算每個裁切後建物片段的投影面積
    frontal_areas = []
    for _, row in intersected.iterrows():
        geom = row.geometry
        if geom.is_empty or not geom.is_valid:
            frontal_areas.append(0.0)
            continue
        # overlay intersection 可能產生 GeometryCollection，提取面幾何
        if geom.geom_type == "GeometryCollection":
            from shapely.ops import unary_union
            polys = [g for g in geom.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
            if not polys:
                frontal_areas.append(0.0)
                continue
            geom = unary_union(polys)
        # 投影寬度 × 建物高度 = 正面面積
        width = _projected_width(geom, direction_rad)
        frontal_areas.append(width * row["height"])

    intersected["frontal_area"] = frontal_areas

    # 按網格聚合
    fai_by_grid = intersected.groupby("grid_id")["frontal_area"].sum().reset_index()
    fai_by_grid.columns = ["grid_id", "total_frontal_area"]

    # 合併回網格
    grid = grid.copy()
    grid = grid.merge(fai_by_grid, on="grid_id", how="left")
    grid["total_frontal_area"] = grid["total_frontal_area"].fillna(0.0)

    # FAI = 正面面積 / 網格地面面積
    grid[col_name] = grid["total_frontal_area"] / grid.geometry.area
    grid = grid.drop(columns=["total_frontal_area"])

    logger.info(
        "FAI(%.1f°) stats: min=%.4f, max=%.4f, mean=%.4f",
        wind_direction,
        grid[col_name].min(),
        grid[col_name].max(),
        grid[col_name].mean(),
    )

    return grid


def compute_fai_all_directions(
    buildings: gpd.GeoDataFrame,
    grid: gpd.GeoDataFrame,
    directions: list[float] | None = None,
) -> gpd.GeoDataFrame:
    """計算所有方向的 FAI。

    Args:
        buildings: 建物資料。
        grid: 分析網格。
        directions: 風向列表（度），None 時使用 16 方向。

    Returns:
        grid GeoDataFrame 新增 16 個 'fai_{direction}' 欄位。
    """
    if directions is None:
        directions = WIND_DIRECTIONS_16

    result = grid.copy()
    for direction in directions:
        result = compute_fai_single_direction(buildings, result, direction)

    # 計算最大 FAI 與對應方向
    fai_cols = [f"fai_{d:.1f}" for d in directions]
    fai_values = result[fai_cols].values
    result["fai_max"] = fai_values.max(axis=1)
    max_indices = fai_values.argmax(axis=1)
    result["fai_max_direction"] = [directions[i] for i in max_indices]

    # 東北季風 FAI（主要用 22.5° 與 45.0° 的平均）
    ne_cols = [c for c in fai_cols if any(
        abs(float(c.split("_")[1]) - d) < 1 for d in [22.5, 45.0]
    )]
    if ne_cols:
        result["fai_ne"] = result[ne_cols].mean(axis=1)

    # 西南季風 FAI
    sw_cols = [c for c in fai_cols if any(
        abs(float(c.split("_")[1]) - d) < 1 for d in [202.5, 225.0]
    )]
    if sw_cols:
        result["fai_sw"] = result[sw_cols].mean(axis=1)

    logger.info("Computed FAI for %d directions across %d grid cells", len(directions), len(result))
    return result


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    city = sys.argv[sys.argv.index("--city") + 1] if "--city" in sys.argv else "taipei"
    n_dirs = int(sys.argv[sys.argv.index("--directions") + 1]) if "--directions" in sys.argv else 16
    directions = [i * (360 / n_dirs) for i in range(n_dirs)]
    logger.info("FAI calculation for %s with %d directions", city, n_dirs)
