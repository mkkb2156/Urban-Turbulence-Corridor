"""風廊查詢與計算 API。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query

from src.api.schemas import CorridorComputeRequest, CorridorResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/corridors", response_model=list[CorridorResponse])
async def query_corridors(
    city: str = Query("taipei", description="城市名稱"),
    wind_direction: float | None = Query(None, description="篩選特定風向的風廊（角度）"),
):
    """查詢某城市的風廊資料，回傳符合前端 Corridor 介面的格式。"""
    from src.db.queries import query_corridors_by_city

    try:
        gdf = query_corridors_by_city(city)
    except Exception as exc:
        logger.warning("Failed to query corridors: %s", exc)
        gdf = None

    if gdf is None or gdf.empty:
        from src.api.fallback import generate_demo_corridors

        return [CorridorResponse(**c) for c in generate_demo_corridors()]

    results = []
    for idx, row in gdf.iterrows():
        corridor_id = str(row.get("corridor_id", f"corridor-{idx}"))
        corridor_class = row.get("corridor_class", "secondary")

        # Map corridor_class to frontend type ('primary' | 'secondary')
        corridor_type = "primary" if corridor_class == "primary" else "secondary"

        # Build a human-readable name
        name = row.get("name", f"Wind Corridor {corridor_id}")

        # Convert geometry to GeoJSON dict
        geom_geojson = row.geometry.__geo_interface__

        # Extract wind direction from DB or default to NE (Taipei dominant)
        dominant_direction = row.get("wind_direction", "NE") or "NE"

        # Wind direction in degrees (if available)
        wind_dir_deg = row.get("wind_direction_deg", None)

        # Filter by direction if requested
        if wind_direction is not None and wind_dir_deg is not None:
            # Allow ±45° tolerance
            diff = abs((wind_dir_deg - wind_direction + 180) % 360 - 180)
            if diff > 45:
                continue

        # Estimate mean wind speed from total_cost (lower cost = stronger wind corridor)
        # or use a stored value if available
        mean_wind_speed = row.get("mean_wind_speed", None)
        if mean_wind_speed is None:
            total_cost = row.get("total_cost", 0) or 0
            # Rough heuristic: corridors with lower cost have higher wind speed
            # Scale inversely: cost 0 -> ~8 m/s, cost 100+ -> ~2 m/s
            mean_wind_speed = round(max(2.0, 8.0 - total_cost * 0.05), 2)

        # Determine risk level based on wind speed
        risk_level = row.get("risk_level", None)
        if risk_level is None:
            if mean_wind_speed < 4:
                risk_level = "green"
            elif mean_wind_speed < 8:
                risk_level = "yellow"
            elif mean_wind_speed < 12:
                risk_level = "red"
            else:
                risk_level = "black"

        results.append(CorridorResponse(
            corridor_id=corridor_id,
            name=name,
            type=corridor_type,
            geometry=geom_geojson,
            mean_wind_speed=mean_wind_speed,
            dominant_direction=dominant_direction,
            risk_level=risk_level,
            wind_direction_deg=wind_dir_deg,
        ))

    return results


@router.post("/corridors/compute", response_model=list[CorridorResponse])
async def compute_corridors(req: CorridorComputeRequest):
    """即時計算指定方向的風廊。

    使用 LCP 演算法從 grid cells FAI 數據計算風廊路徑。
    需要資料庫中有該城市的 grid_cells 資料。
    """
    from config.settings import get_city_config
    from src.db.queries import query_grid_by_bbox

    try:
        city_config = get_city_config(req.city)
    except ValueError:
        from src.api.errors import NotFoundError
        raise NotFoundError(f"Unknown city: {req.city}")

    # 從 DB 讀取 grid cells
    try:
        minx, miny, maxx, maxy = city_config.bounds_4326
        grid = query_grid_by_bbox(minx, miny, maxx, maxy)
    except Exception as exc:
        logger.warning("Failed to query grid for compute: %s", exc)
        from src.api.errors import ServiceUnavailableError
        raise ServiceUnavailableError(f"Database unavailable: {exc}")

    if grid.empty:
        return []

    # 確保有 row/col 欄位（從 grid_id 推斷）
    if "row" not in grid.columns or "col" not in grid.columns:
        grid = _infer_row_col(grid)

    # 轉換到內部 CRS
    from config.settings import CRS_INTERNAL
    if grid.crs and grid.crs.to_epsg() != 3826:
        grid = grid.to_crs(CRS_INTERNAL)

    # 執行 LCP
    from src.wind.lcp import identify_corridors_multi_direction, identify_wind_corridors

    if req.multi_direction:
        # 使用城市設定的主要風向
        directions = [
            (lo + hi) / 2
            for lo, hi in city_config.primary_wind_directions.values()
        ]
        if not directions:
            directions = [req.wind_direction]
        corridors_gdf = identify_corridors_multi_direction(
            grid,
            directions=directions,
            n_corridors_per_direction=req.n_corridors,
            n_corridors_total=req.n_corridors * 2,
        )
    else:
        corridors_gdf = identify_wind_corridors(
            grid,
            fai_col=req.fai_col,
            n_corridors=req.n_corridors,
            wind_direction=req.wind_direction,
        )

    if corridors_gdf.empty:
        return []

    # 轉換到 WGS84 for response
    from config.settings import CRS_OUTPUT
    if corridors_gdf.crs and corridors_gdf.crs.to_epsg() != 4326:
        corridors_gdf = corridors_gdf.to_crs(CRS_OUTPUT)

    # 組裝回應
    from src.wind.lcp import _deg_to_label

    results = []
    for idx, row in corridors_gdf.iterrows():
        corridor_id = row.get("corridor_id", f"computed_{idx:03d}")
        wind_dir_deg = row.get("wind_direction_deg", req.wind_direction)
        dir_label = _deg_to_label(wind_dir_deg)
        total_cost = row.get("total_cost", 0)
        mean_wind_speed = round(max(2.0, 8.0 - total_cost * 0.05), 2)

        if mean_wind_speed < 4:
            risk_level = "green"
        elif mean_wind_speed < 8:
            risk_level = "yellow"
        elif mean_wind_speed < 12:
            risk_level = "red"
        else:
            risk_level = "black"

        results.append(CorridorResponse(
            corridor_id=corridor_id,
            name=f"風廊 {corridor_id} ({dir_label})",
            type="primary" if idx < 3 else "secondary",
            geometry=row.geometry.__geo_interface__,
            mean_wind_speed=mean_wind_speed,
            dominant_direction=dir_label,
            risk_level=risk_level,
            wind_direction_deg=wind_dir_deg,
        ))

    return results


def _infer_row_col(grid):
    """從 grid_id 推斷 row/col（格式：city_ROW_COL）。"""
    import re

    rows = []
    cols = []
    for gid in grid["grid_id"]:
        match = re.search(r"(\d+)_(\d+)$", str(gid))
        if match:
            rows.append(int(match.group(1)))
            cols.append(int(match.group(2)))
        else:
            rows.append(0)
            cols.append(0)
    grid["row"] = rows
    grid["col"] = cols
    return grid
