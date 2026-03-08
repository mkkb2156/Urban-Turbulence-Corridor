"""無人機功率與續航 API。"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter

from src.api.schemas import (
    DronePowerRequest,
    DronePowerResponse,
    MissionFeasibilityRequest,
    MissionFeasibilityResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/drone/power", response_model=DronePowerResponse)
async def compute_drone_power(req: DronePowerRequest):
    """計算指定風況下的無人機功率、續航與航程。"""
    from src.risk.power_model import get_power_spec, hover_power, power_with_wind

    try:
        spec = get_power_spec(req.drone_id)
    except ValueError as exc:
        from src.api.errors import NotFoundError
        raise NotFoundError(str(exc))

    result = power_with_wind(
        spec,
        cruise_speed_ms=req.cruise_speed,
        wind_speed_ms=req.wind_speed,
        wind_angle_deg=req.wind_angle,
        altitude_m=req.altitude,
    )

    return DronePowerResponse(
        drone_id=req.drone_id,
        drone_name=spec.name,
        hover_power_w=result["hover_power_w"],
        forward_power_w=result["power_w"],
        groundspeed_ms=result["groundspeed_ms"],
        endurance_min=result["endurance_min"],
        range_km=result["range_km"],
        battery_impact_pct=result["battery_impact_pct"],
        headwind_ms=result["headwind_ms"],
        crosswind_ms=result["crosswind_ms"],
        battery_capacity_wh=spec.battery_wh,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/drone/mission", response_model=MissionFeasibilityResponse)
async def compute_mission_feasibility(req: MissionFeasibilityRequest):
    """評估路線任務可行性 — 結合風場的電池續航分析。"""
    from src.risk.power_model import get_power_spec, mission_feasibility

    try:
        spec = get_power_spec(req.drone_id)
    except ValueError as exc:
        from src.api.errors import NotFoundError
        raise NotFoundError(str(exc))

    # 構建分段列表
    segments = []
    waypoints = req.waypoints
    for i in range(len(waypoints) - 1):
        lon1, lat1 = waypoints[i]
        lon2, lat2 = waypoints[i + 1]

        # 計算距離與航向
        distance_m, bearing = _haversine_bearing(lat1, lon1, lat2, lon2)

        # 查詢中點風場
        mid_lon = (lon1 + lon2) / 2
        mid_lat = (lat1 + lat2) / 2
        wind = _get_wind_at_point(mid_lon, mid_lat, req.height)

        segments.append({
            "distance_m": distance_m,
            "bearing": bearing,
            "wind_speed": wind["speed"],
            "wind_direction": wind["direction"],
        })

    result = mission_feasibility(
        spec,
        segments,
        reserve_pct=req.reserve_pct,
        altitude_m=req.height,
    )

    return MissionFeasibilityResponse(
        drone_id=req.drone_id,
        drone_name=spec.name,
        feasible=result["feasible"],
        total_energy_wh=result["total_energy_wh"],
        battery_capacity_wh=result["battery_capacity_wh"],
        battery_remaining_pct=result["battery_remaining_pct"],
        total_time_min=result["total_time_min"],
        critical_segments=result["critical_segments"],
        recommended_speed_ms=result["recommended_speed_ms"],
        segments_detail=result["segments_detail"],
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def _haversine_bearing(
    lat1: float, lon1: float, lat2: float, lon2: float,
) -> tuple[float, float]:
    """計算兩點距離 (m) 與航向 (deg)。"""
    import math

    R = 6371000  # Earth radius in meters
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c

    y = math.sin(dlon) * math.cos(lat2_r)
    x = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(dlon)
    bearing = (math.degrees(math.atan2(y, x)) + 360) % 360

    return distance, bearing


def _get_wind_at_point(lon: float, lat: float, height: float) -> dict:
    """查詢指定點的風場資料。如果 DB 不可用則使用 fallback。"""
    try:
        from src.db.queries import query_grid_by_point
        result = query_grid_by_point(lon, lat)
        if result:
            height_key = f"wind_{int(height)}m"
            speed = result.get(height_key, result.get("wind_50m", 5.0)) or 5.0
            return {"speed": speed, "direction": 45.0}
    except Exception:
        pass

    # Fallback: 預設值
    return {"speed": 5.0, "direction": 45.0}
