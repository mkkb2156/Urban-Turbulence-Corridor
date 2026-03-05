"""區域預測 API（mock data for demo）。"""

from __future__ import annotations

import math
import random
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel, Field

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


def _generate_mock_grid_cells(polygon: list[list[float]], height: float) -> list[dict]:
    """在多邊形範圍內生成 mock grid cells。"""
    lons = [p[0] for p in polygon]
    lats = [p[1] for p in polygon]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)

    step = 0.005  # ~500m grid
    cells = []
    lon = min_lon
    while lon <= max_lon:
        lat = min_lat
        while lat <= max_lat:
            # 高度修正
            z0 = 1.0
            zd = 15.0
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
    cells = _generate_mock_grid_cells(req.polygon, req.height)

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
