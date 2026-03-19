"""大區域風場 API — 從 Open-Meteo 取得 bbox 範圍的網格化風場資料。"""

from __future__ import annotations

import logging
import math
import random
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Query as QueryParam

router = APIRouter()
logger = logging.getLogger(__name__)

# ── In-memory cache ──
_wind_cache: dict[str, tuple[float, dict]] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour


def _classify_risk(speed: float) -> str:
    if speed <= 5:
        return "green"
    elif speed <= 8:
        return "yellow"
    elif speed <= 12:
        return "red"
    return "black"


def _fetch_regional_wind(
    min_lon: float, min_lat: float, max_lon: float, max_lat: float,
    height: int = 10,
    resolution: float = 0.1,
) -> dict | None:
    """
    Fetch wind data from Open-Meteo for a grid of points within bbox.

    Open-Meteo supports single-point queries, so we create a grid and
    batch-query using the forecast endpoint for each point.
    For efficiency, use coarse resolution (0.1° ≈ 11km) for regional view.
    """
    try:
        import requests

        # Generate grid points
        n_lon = max(2, int((max_lon - min_lon) / resolution) + 1)
        n_lat = max(2, int((max_lat - min_lat) / resolution) + 1)

        # Limit grid size for API rate limit
        if n_lon * n_lat > 100:
            resolution = math.sqrt((max_lon - min_lon) * (max_lat - min_lat) / 100)
            n_lon = max(2, int((max_lon - min_lon) / resolution) + 1)
            n_lat = max(2, int((max_lat - min_lat) / resolution) + 1)

        lons = [min_lon + i * (max_lon - min_lon) / (n_lon - 1) for i in range(n_lon)]
        lats = [min_lat + i * (max_lat - min_lat) / (n_lat - 1) for i in range(n_lat)]

        # Determine wind variable based on height
        if height >= 100:
            speed_var = "wind_speed_120m"
            dir_var = "wind_direction_120m"
        elif height >= 60:
            speed_var = "wind_speed_80m"
            dir_var = "wind_direction_80m"
        else:
            speed_var = "wind_speed_10m"
            dir_var = "wind_direction_10m"

        # Batch query using Open-Meteo multi-point (comma-separated lat/lon)
        lat_str = ",".join(f"{lat:.4f}" for lat in lats for _ in lons)
        lon_str = ",".join(f"{lon:.4f}" for _ in lats for lon in lons)

        params = {
            "latitude": lat_str,
            "longitude": lon_str,
            "current": f"{speed_var},{dir_var},wind_gusts_10m",
            "timezone": "auto",
        }

        url = "https://api.open-meteo.com/v1/forecast"
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Parse response — multi-point returns a list
        points = []
        if isinstance(data, list):
            # Multi-point response
            for i, item in enumerate(data):
                lat_idx = i // n_lon
                lon_idx = i % n_lon
                current = item.get("current", {})
                speed = current.get(speed_var, 0) or 0
                direction = current.get(dir_var, 0) or 0
                gusts = current.get("wind_gusts_10m", 0) or 0

                rad = math.radians(direction)
                u = -speed * math.sin(rad)
                v = -speed * math.cos(rad)

                points.append({
                    "lon": round(lons[lon_idx], 4),
                    "lat": round(lats[lat_idx], 4),
                    "wind_speed": round(speed, 1),
                    "wind_direction": round(direction, 1),
                    "wind_gusts": round(gusts, 1),
                    "u": round(u, 2),
                    "v": round(v, 2),
                    "risk_level": _classify_risk(speed),
                })
        else:
            # Single point response (small bbox)
            current = data.get("current", {})
            speed = current.get(speed_var, 0) or 0
            direction = current.get(dir_var, 0) or 0
            gusts = current.get("wind_gusts_10m", 0) or 0
            rad = math.radians(direction)
            u = -speed * math.sin(rad)
            v = -speed * math.cos(rad)

            # Fill entire grid with this single value
            for lat in lats:
                for lon in lons:
                    points.append({
                        "lon": round(lon, 4),
                        "lat": round(lat, 4),
                        "wind_speed": round(speed, 1),
                        "wind_direction": round(direction, 1),
                        "wind_gusts": round(gusts, 1),
                        "u": round(u, 2),
                        "v": round(v, 2),
                        "risk_level": _classify_risk(speed),
                    })

        return {
            "bbox": [min_lon, min_lat, max_lon, max_lat],
            "grid": {"n_lon": n_lon, "n_lat": n_lat, "resolution": resolution},
            "height_m": height,
            "points": points,
            "point_count": len(points),
            "source": "open-meteo",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.warning("Failed to fetch regional wind from Open-Meteo: %s", e)
        return None


def _generate_mock_regional(
    min_lon: float, min_lat: float, max_lon: float, max_lat: float,
    height: int = 10,
    resolution: float = 0.1,
) -> dict:
    """Generate mock regional wind data when API is unavailable."""
    n_lon = max(2, int((max_lon - min_lon) / resolution) + 1)
    n_lat = max(2, int((max_lat - min_lat) / resolution) + 1)

    if n_lon * n_lat > 100:
        resolution = math.sqrt((max_lon - min_lon) * (max_lat - min_lat) / 100)
        n_lon = max(2, int((max_lon - min_lon) / resolution) + 1)
        n_lat = max(2, int((max_lat - min_lat) / resolution) + 1)

    lons = [min_lon + i * (max_lon - min_lon) / max(1, n_lon - 1) for i in range(n_lon)]
    lats = [min_lat + i * (max_lat - min_lat) / max(1, n_lat - 1) for i in range(n_lat)]

    # Base wind: NE monsoon pattern with spatial variation
    base_speed = 4.5 * (1.0 + 0.3 * (height / 50.0))
    base_dir = 45.0  # NE

    points = []
    for lat in lats:
        for lon in lons:
            # Spatial variation
            speed = base_speed + random.gauss(0, 1.5) + 0.5 * math.sin((lon - 121) * 10)
            speed = max(0.5, round(speed, 1))
            direction = base_dir + random.gauss(0, 15) + 10 * math.sin((lat - 25) * 5)
            direction = round(direction % 360, 1)
            gusts = round(speed * (1.3 + random.random() * 0.4), 1)

            rad = math.radians(direction)
            u = -speed * math.sin(rad)
            v = -speed * math.cos(rad)

            points.append({
                "lon": round(lon, 4),
                "lat": round(lat, 4),
                "wind_speed": speed,
                "wind_direction": direction,
                "wind_gusts": gusts,
                "u": round(u, 2),
                "v": round(v, 2),
                "risk_level": _classify_risk(speed),
            })

    return {
        "bbox": [min_lon, min_lat, max_lon, max_lat],
        "grid": {"n_lon": n_lon, "n_lat": n_lat, "resolution": resolution},
        "height_m": height,
        "points": points,
        "point_count": len(points),
        "source": "mock",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/wind/regional")
async def get_regional_wind(
    min_lon: float = QueryParam(119.5, ge=115, le=125, description="最小經度"),
    min_lat: float = QueryParam(21.5, ge=20, le=27, description="最小緯度"),
    max_lon: float = QueryParam(122.5, ge=115, le=125, description="最大經度"),
    max_lat: float = QueryParam(25.5, ge=20, le=27, description="最大緯度"),
    height: int = QueryParam(10, ge=0, le=500, description="高度層 (m)"),
    resolution: float = QueryParam(0.1, ge=0.02, le=1.0, description="網格解析度 (度)"),
):
    """取得大區域風場網格資料。

    回傳指定 bounding box 內的網格化風場（u/v 向量 + 風速/風向/陣風）。
    資料來自 Open-Meteo，快取 1 小時。可用於大範圍風場粒子動畫和等值線圖。
    """
    # Check cache
    cache_key = f"{min_lon:.2f},{min_lat:.2f},{max_lon:.2f},{max_lat:.2f},{height},{resolution:.3f}"
    now = time.time()
    if cache_key in _wind_cache:
        cached_time, cached_data = _wind_cache[cache_key]
        if now - cached_time < CACHE_TTL_SECONDS:
            logger.info("Regional wind cache hit: %s", cache_key)
            return cached_data

    # Try real data
    result = _fetch_regional_wind(min_lon, min_lat, max_lon, max_lat, height, resolution)

    if result is None:
        result = _generate_mock_regional(min_lon, min_lat, max_lon, max_lat, height, resolution)

    # Cache result
    _wind_cache[cache_key] = (now, result)

    # Cleanup old entries
    for k in list(_wind_cache.keys()):
        if now - _wind_cache[k][0] > CACHE_TTL_SECONDS * 2:
            del _wind_cache[k]

    return result
