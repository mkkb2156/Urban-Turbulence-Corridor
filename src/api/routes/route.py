"""路線分析與最優路線規劃 API。"""

from __future__ import annotations

import logging
import math
import random
from datetime import datetime, timezone

from fastapi import APIRouter

from src.api.schemas import RouteAnalyzeRequest, RoutePlanRequest

logger = logging.getLogger(__name__)
router = APIRouter()


def _haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """計算兩點距離 (m)。"""
    R = 6371000
    rad = math.pi / 180
    dlat = (lat2 - lat1) * rad
    dlon = (lon2 - lon1) * rad
    a = math.sin(dlat/2)**2 + math.cos(lat1*rad) * math.cos(lat2*rad) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _bearing(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """計算方位角 (degrees)。"""
    rad = math.pi / 180
    dlon = (lon2 - lon1) * rad
    y = math.sin(dlon) * math.cos(lat2 * rad)
    x = math.cos(lat1*rad) * math.sin(lat2*rad) - math.sin(lat1*rad) * math.cos(lat2*rad) * math.cos(dlon)
    return (math.atan2(y, x) * 180 / math.pi + 360) % 360


def _interpolate_points(p1: list[float], p2: list[float], interval: float = 100) -> list[list[float]]:
    """在兩點間等距插值。"""
    dist = _haversine(p1[0], p1[1], p2[0], p2[1])
    n = max(2, int(dist / interval))
    points = []
    for i in range(n + 1):
        t = i / n
        lon = p1[0] + t * (p2[0] - p1[0])
        lat = p1[1] + t * (p2[1] - p1[1])
        points.append([round(lon, 6), round(lat, 6)])
    return points


def _wind_at_point(lon: float, lat: float, height: float) -> dict:
    """查詢單點風場，優先使用 DB，fallback 使用模擬。"""
    height_col = f"wind_{int(height)}m" if int(height) in (50, 80, 120) else "wind_50m"
    try:
        from src.db.queries import query_grid_by_point
        row = query_grid_by_point(lon, lat)
        if row is not None:
            speed = row.get(height_col, row.get("wind_50m", 4.0)) or 4.0
            risk = row.get("risk_level", "green")
            # 用 NE 季風 45 度作為預設方向
            direction = 45.0
            return {"wind_speed": round(speed, 1), "wind_direction": direction, "risk_level": risk}
    except Exception as e:
        logger.debug("Route wind query DB fallback: %s", e)

    # Fallback: 模擬風場
    z0, zd = 1.0, 15.0
    h_factor = math.log(max(height - zd, 1) / z0) / math.log(10 / z0) if height > zd + z0 else 1.0
    base = 3.5 + 1.5 * math.sin((lon - 121.5) * 50) + random.gauss(0, 0.8)
    speed = max(0.5, round(base * h_factor, 1))
    direction = round((45 + 15 * math.sin((lat - 25.0) * 100) + random.gauss(0, 8)) % 360, 1)

    if speed <= 5:
        risk = "green"
    elif speed <= 8:
        risk = "yellow"
    elif speed <= 12:
        risk = "red"
    else:
        risk = "black"

    return {"wind_speed": speed, "wind_direction": direction, "risk_level": risk}


def _analyze_segments(waypoints: list[list[float]], height: float) -> list[dict]:
    """分析路線各段風況。"""
    segments = []
    for i in range(len(waypoints) - 1):
        p1, p2 = waypoints[i], waypoints[i + 1]
        sample_pts = _interpolate_points(p1, p2, interval=100)

        winds = [_wind_at_point(p[0], p[1], height) for p in sample_pts]
        avg_speed = sum(w["wind_speed"] for w in winds) / len(winds)
        avg_dir = sum(w["wind_direction"] for w in winds) / len(winds)

        # 計算逆風/側風分量
        from src.risk.derived import headwind_crosswind as _hcw
        seg_bearing = _bearing(p1[0], p1[1], p2[0], p2[1])
        wind_components = _hcw(avg_speed, avg_dir, seg_bearing)
        headwind = wind_components["headwind"]
        crosswind = wind_components["crosswind"]

        dist = _haversine(p1[0], p1[1], p2[0], p2[1])
        effective_speed = wind_components["effective_groundspeed"]
        travel_time = dist / effective_speed

        # 最高風險
        risk_order = {"green": 0, "yellow": 1, "red": 2, "black": 3}
        max_risk = max(winds, key=lambda w: risk_order[w["risk_level"]])["risk_level"]

        segments.append({
            "from": p1,
            "to": p2,
            "distance_m": round(dist, 0),
            "bearing": round(seg_bearing, 1),
            "avg_wind_speed": round(avg_speed, 1),
            "avg_wind_direction": round(avg_dir, 1),
            "headwind": headwind,
            "crosswind": crosswind,
            "wind_effect_pct": wind_components["wind_effect_pct"],
            "risk_level": max_risk,
            "travel_time_s": round(travel_time, 1),
            "sample_points": [
                {"lon": p[0], "lat": p[1], **w}
                for p, w in zip(sample_pts, winds)
            ],
        })

    return segments


@router.post("/route/analyze")
async def analyze_route(req: RouteAnalyzeRequest):
    """路線風況分析（mock）。"""
    if len(req.waypoints) < 2:
        return {"error": "至少需要 2 個路徑點"}

    segments = _analyze_segments(req.waypoints, req.height)

    total_distance = sum(s["distance_m"] for s in segments)
    total_time = sum(s["travel_time_s"] for s in segments)
    risk_order = {"green": 0, "yellow": 1, "red": 2, "black": 3}
    max_risk = max(segments, key=lambda s: risk_order[s["risk_level"]])["risk_level"]
    avg_speed = sum(s["avg_wind_speed"] for s in segments) / len(segments)

    # Flyability
    flyability = None
    if req.drone_id:
        tolerances = {
            "dji-mini4-pro": 10.7, "dji-air3": 12.0, "dji-mavic3": 12.0,
            "dji-matrice350": 15.0, "dji-matrice30": 15.0,
        }
        tol = tolerances.get(req.drone_id, 10.0)
        all_speeds = [p["wind_speed"] for s in segments for p in s["sample_points"]]
        max_wind = max(all_speeds)
        flyability = {
            "drone_id": req.drone_id,
            "max_wind_on_route": round(max_wind, 1),
            "tolerance": tol,
            "flyable": max_wind <= tol * 0.7,
            "danger_segments": sum(1 for s in segments if risk_order[s["risk_level"]] >= 2),
        }

    return {
        "waypoints": req.waypoints,
        "height": req.height,
        "total_distance_m": round(total_distance, 0),
        "total_time_s": round(total_time, 0),
        "max_risk": max_risk,
        "avg_wind_speed": round(avg_speed, 1),
        "segments": segments,
        "flyability": flyability,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _generate_route_variant(
    start: list[float],
    end: list[float],
    mode: str,
    height: float,
) -> dict:
    """產生一條路線變體。"""
    # 根據模式產生不同的偏移路線
    mid_lon = (start[0] + end[0]) / 2
    mid_lat = (start[1] + end[1]) / 2

    if mode == "safest":
        # 偏移更多避開風廊
        offset_lon = random.uniform(-0.01, 0.01)
        offset_lat = random.uniform(-0.005, 0.005)
        waypoints = [
            start,
            [round(mid_lon + offset_lon, 6), round(mid_lat + offset_lat, 6)],
            end,
        ]
    elif mode == "shortest":
        # 直線
        waypoints = [start, end]
    else:  # balanced
        offset_lon = random.uniform(-0.005, 0.005)
        offset_lat = random.uniform(-0.003, 0.003)
        waypoints = [
            start,
            [round(mid_lon + offset_lon, 6), round(mid_lat + offset_lat, 6)],
            end,
        ]

    segments = _analyze_segments(waypoints, height)
    total_distance = sum(s["distance_m"] for s in segments)
    total_time = sum(s["travel_time_s"] for s in segments)
    risk_order = {"green": 0, "yellow": 1, "red": 2, "black": 3}
    max_risk = max(segments, key=lambda s: risk_order[s["risk_level"]])["risk_level"]
    avg_risk_score = sum(risk_order[s["risk_level"]] for s in segments) / len(segments)

    # GeoJSON LineString
    all_points = []
    for seg in segments:
        for pt in seg["sample_points"]:
            all_points.append([pt["lon"], pt["lat"]])

    return {
        "mode": mode,
        "waypoints": waypoints,
        "geometry": {
            "type": "LineString",
            "coordinates": all_points,
        },
        "total_distance_m": round(total_distance, 0),
        "total_time_s": round(total_time, 0),
        "max_risk": max_risk,
        "avg_risk_score": round(avg_risk_score, 2),
        "segments": segments,
    }


@router.post("/route/plan")
async def plan_route(req: RoutePlanRequest):
    """最優路線規劃（mock）。返回三條備選路線。"""
    routes = []
    for mode in ["safest", "shortest", "balanced"]:
        route = _generate_route_variant(req.start, req.end, mode, req.height)
        routes.append(route)

    # Flyability
    flyability = None
    if req.drone_id:
        tolerances = {
            "dji-mini4-pro": 10.7, "dji-air3": 12.0, "dji-mavic3": 12.0,
            "dji-matrice350": 15.0, "dji-matrice30": 15.0,
        }
        tol = tolerances.get(req.drone_id, 10.0)
        for r in routes:
            all_speeds = [p["wind_speed"] for s in r["segments"] for p in s["sample_points"]]
            r["flyable"] = max(all_speeds) <= tol * 0.7

    return {
        "start": req.start,
        "end": req.end,
        "height": req.height,
        "routes": routes,
        "recommended": "balanced",
        "flyability": flyability,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
