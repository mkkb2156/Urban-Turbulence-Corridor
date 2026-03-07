"""區域預測 API。"""

from __future__ import annotations

import logging
import math
import random
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


class AreaPredictRequest(BaseModel):
    """多邊形區域預測請求。"""
    polygon: list[list[float]] = Field(..., description="多邊形頂點 [[lon,lat], ...]")
    height: float = Field(50.0, ge=0, le=500, description="飛行高度 (m)")
    drone_id: str | None = Field(None, description="無人機型號")
    start_time: str | None = Field(None, description="起始時間 (ISO)")
    end_time: str | None = Field(None, description="結束時間 (ISO)")


def _polygon_center(polygon: list[list[float]]) -> tuple[float, float]:
    """計算多邊形中心。"""
    lons = [p[0] for p in polygon]
    lats = [p[1] for p in polygon]
    return sum(lons) / len(lons), sum(lats) / len(lats)


def _polygon_area_approx(polygon: list[list[float]]) -> float:
    """近似多邊形面積 (km²)。"""
    if len(polygon) < 3:
        return 0.0
    # Shoelace formula with degree-to-km conversion
    n = len(polygon)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += polygon[i][0] * polygon[j][1]
        area -= polygon[j][0] * polygon[i][1]
    area = abs(area) / 2.0
    # ~111 km per degree
    return area * 111 * 111


def _point_in_polygon(lon: float, lat: float, polygon: list[list[float]]) -> bool:
    """射線法判斷點是否在多邊形內。"""
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _query_grid_cells(polygon: list[list[float]], height: float) -> list[dict]:
    """查詢多邊形範圍內的網格，優先使用 DB，fallback 使用模擬。"""
    lons = [p[0] for p in polygon]
    lats = [p[1] for p in polygon]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)

    height_col = f"wind_{int(height)}m" if int(height) in (50, 80, 120) else "wind_50m"

    # 嘗試從 DB 查詢
    try:
        from src.db.queries import query_grid_by_bbox
        gdf = query_grid_by_bbox(min_lon, min_lat, max_lon, max_lat)
        if len(gdf) > 0:
            cells = []
            for _, row in gdf.iterrows():
                geom = row.geometry
                clon, clat = geom.centroid.x, geom.centroid.y
                if not _point_in_polygon(clon, clat, polygon):
                    continue
                speed = row.get(height_col, row.get("wind_50m", 4.0)) or 4.0
                cells.append({
                    "lon": round(clon, 6),
                    "lat": round(clat, 6),
                    "wind_speed": round(float(speed), 1),
                    "wind_direction": 45.0,
                    "risk_level": row.get("risk_level", "green"),
                })
            if cells:
                logger.info("Area predict: %d cells from DB", len(cells))
                return cells
    except Exception as e:
        logger.debug("Area predict DB fallback: %s", e)

    # Fallback: 模擬風場
    step = 0.005
    cells = []
    lon = min_lon
    while lon <= max_lon:
        lat = min_lat
        while lat <= max_lat:
            z0, zd = 1.0, 15.0
            h_factor = math.log(max(height - zd, 1) / z0) / math.log(10 / z0) if height > zd + z0 else 1.0
            base = 3.0 + random.gauss(0, 1.5)
            speed = max(0.5, round(base * h_factor, 1))
            direction = round((45 + random.gauss(0, 30)) % 360, 1)

            if speed <= 5:
                risk = "green"
            elif speed <= 8:
                risk = "yellow"
            elif speed <= 12:
                risk = "red"
            else:
                risk = "black"

            cells.append({
                "lon": round(lon, 6),
                "lat": round(lat, 6),
                "wind_speed": speed,
                "wind_direction": direction,
                "risk_level": risk,
            })
            lat += step
        lon += step

    return cells


@router.post("/area/predict")
async def predict_area(req: AreaPredictRequest):
    """多邊形區域環境預測（mock）。"""
    if len(req.polygon) < 3:
        return {"error": "多邊形至少需要 3 個頂點"}

    center_lon, center_lat = _polygon_center(req.polygon)
    area_km2 = _polygon_area_approx(req.polygon)
    cells = _query_grid_cells(req.polygon, req.height)

    if not cells:
        cells = [{"lon": center_lon, "lat": center_lat, "wind_speed": 4.5,
                   "wind_direction": 45, "risk_level": "green"}]

    speeds = [c["wind_speed"] for c in cells]
    risk_counts = {"green": 0, "yellow": 0, "red": 0, "black": 0}
    for c in cells:
        risk_counts[c["risk_level"]] += 1

    total = len(cells)
    risk_distribution = {k: round(v / total * 100, 1) for k, v in risk_counts.items()}

    # Mock wind rose
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                   "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    wind_rose = []
    for i, d in enumerate(directions):
        angle = i * 22.5
        # NE dominant
        freq = 18.0 if d in ("NE", "NNE") else 8.0 if d in ("N", "ENE") else 4.0
        freq += random.gauss(0, 1)
        freq = max(0.5, freq)
        wind_rose.append({
            "direction": d,
            "angle": angle,
            "frequency": round(freq, 1),
            "mean_speed": round(random.uniform(2, 8), 1),
        })
    # Normalize frequencies
    total_freq = sum(w["frequency"] for w in wind_rose)
    for w in wind_rose:
        w["frequency"] = round(w["frequency"] / total_freq * 100, 1)

    # Flyability
    flyability = None
    if req.drone_id:
        drone_tolerances = {
            "dji-mini4-pro": 10.7, "dji-air3": 12.0, "dji-mavic3": 12.0,
            "dji-matrice350": 15.0, "dji-matrice30": 15.0,
        }
        tolerance = drone_tolerances.get(req.drone_id, 10.0)
        max_speed = max(speeds)
        flyability = {
            "drone_id": req.drone_id,
            "max_wind_in_area": round(max_speed, 1),
            "tolerance": tolerance,
            "safe_percentage": round(sum(1 for s in speeds if s <= tolerance * 0.7) / len(speeds) * 100, 1),
            "flyable": max_speed <= tolerance * 0.7,
        }

    return {
        "center": {"lon": round(center_lon, 6), "lat": round(center_lat, 6)},
        "area_km2": round(area_km2, 2),
        "grid_count": len(cells),
        "height": req.height,
        "wind_stats": {
            "mean_speed": round(sum(speeds) / len(speeds), 1),
            "max_speed": round(max(speeds), 1),
            "min_speed": round(min(speeds), 1),
            "std_speed": round((sum((s - sum(speeds)/len(speeds))**2 for s in speeds) / len(speeds))**0.5, 1),
        },
        "risk_distribution": risk_distribution,
        "wind_rose": wind_rose,
        "flyability": flyability,
        "grid_cells": cells,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
