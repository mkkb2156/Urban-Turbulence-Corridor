"""Fallback 資料產生模組 — DB 不可用時提供即時 / demo 數據。

當 Supabase 資料庫尚未初始化或連線失敗時，
使用 Open-Meteo 即時風速 + 演算法產生的台北都市網格資料，
確保前端所有功能可正常運作。
"""

from __future__ import annotations

import logging
import math
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── 快取 ──────────────────────────────────────────────────────

_wind_cache: dict = {"data": None, "time": 0}
_grids_cache: dict = {"data": None, "time": 0, "height": None}

CACHE_TTL = 600  # 10 minutes


# ── 台北試驗區設定 ────────────────────────────────────────────

# 涵蓋信義區 + 大安區 + 中山區 + 松山區核心區域
PILOT_LON_MIN, PILOT_LON_MAX = 121.50, 121.58
PILOT_LAT_MIN, PILOT_LAT_MAX = 25.01, 25.06
GRID_STEP = 0.002  # ~200m spacing


# ── Risk classification (same thresholds used project-wide) ──

def _classify_risk(speed: float) -> str:
    if speed <= 5:
        return "green"
    elif speed <= 8:
        return "yellow"
    elif speed <= 12:
        return "red"
    return "black"


def _risk_score(speed: float) -> float:
    """0-1 normalized risk score."""
    return round(min(speed / 15.0, 1.0), 4)


# ── Open-Meteo 即時風速 ──────────────────────────────────────

def get_current_wind(
    lon: float = 121.55,
    lat: float = 25.03,
) -> tuple[float, float]:
    """取得即時 10m 風速與風向，快取 10 分鐘。

    Returns:
        (wind_speed_10m, wind_direction) in (m/s, degrees).
    """
    now = time.time()
    if _wind_cache["data"] and now - _wind_cache["time"] < CACHE_TTL:
        return _wind_cache["data"]

    try:
        from src.ingest.open_meteo import fetch_forecast_wind

        df = fetch_forecast_wind(city="taipei", hours=1, lat=lat, lon=lon)
        if not df.empty:
            row = df.iloc[0]
            result = (float(row["wind_speed"]), float(row["wind_direction"]))
            _wind_cache["data"] = result
            _wind_cache["time"] = now
            logger.info("Fallback: fetched live wind from Open-Meteo: %.1f m/s @ %.0f°", *result)
            return result
    except Exception as e:
        logger.warning("Fallback: Open-Meteo fetch failed, using Taipei average: %s", e)

    # 台北年均風速 fallback
    return (3.5, 45.0)


# ── Log profile 高度修正 ──────────────────────────────────────

def _height_correction(speed_10m: float, height: float, z0: float = 1.0, zd: float = 15.0) -> float:
    """Wind profile extrapolation from 10m reference.

    Uses power-law profile (alpha depends on roughness) which is more robust
    than log-law when reference height is near or below displacement height.
    """
    ref_height = 10.0
    if height <= ref_height:
        return speed_10m
    # Power-law exponent: higher roughness → steeper profile
    # Typical urban alpha: 0.25-0.40
    alpha = 0.10 + 0.15 * min(z0, 2.0)
    factor = (height / ref_height) ** alpha
    return round(speed_10m * factor, 2)


# ── 位置相關粗糙度參數 ────────────────────────────────────────

def _roughness_params(lon: float, lat: float) -> tuple[float, float, float, float]:
    """根據台北區域回傳 (z0, zd, bcr, fai)。

    信義/大安核心區 → 高密度；河川沿線 → 低密度。
    """
    # 基隆河沿線（北側低地）
    if lat > 25.055:
        return (0.5, 8.0, 0.25, 0.15)
    # 信義區核心（101 附近）
    if 121.555 < lon < 121.575 and 25.030 < lat < 25.045:
        return (2.0, 25.0, 0.55, 0.45)
    # 大安區（住宅密集）
    if 121.52 < lon < 121.55 and 25.015 < lat < 25.035:
        return (1.5, 18.0, 0.45, 0.35)
    # 中山區（商業混合）
    if lon < 121.53 and lat > 25.04:
        return (1.2, 15.0, 0.40, 0.30)
    # 預設（一般都市）
    return (1.0, 15.0, 0.35, 0.25)


# ── 單點風速查詢 fallback ─────────────────────────────────────

def generate_wind_at_point(lon: float, lat: float, height: float) -> dict:
    """產生指定座標的風速數據，格式與 query_grid_by_point 相同。"""
    speed_10m, direction = get_current_wind(lon, lat)
    z0, zd, bcr, fai = _roughness_params(lon, lat)

    wind_50 = _height_correction(speed_10m, 50.0, z0, zd)
    wind_80 = _height_correction(speed_10m, 80.0, z0, zd)
    wind_120 = _height_correction(speed_10m, 120.0, z0, zd)

    height_col = f"wind_{int(height)}m"
    speeds = {"wind_50m": wind_50, "wind_80m": wind_80, "wind_120m": wind_120}
    wind_at_height = speeds.get(height_col, wind_50)

    risk = _classify_risk(wind_at_height)

    return {
        "grid_id": f"fallback-{int(lon * 1000)}-{int(lat * 1000)}",
        "bcr": bcr,
        "svf": round(1.0 - bcr * 0.6, 4),
        "fai_ne": fai,
        "fai_sw": round(fai * 0.7, 4),
        "wind_50m": wind_50,
        "wind_80m": wind_80,
        "wind_120m": wind_120,
        "wind_direction": direction,
        "risk_level": risk,
        "risk_score": _risk_score(wind_at_height),
        "is_corridor": False,
    }


# ── Demo 網格 ────────────────────────────────────────────────

def generate_demo_grids(height: int = 50) -> list[dict]:
    """產生台北試驗區的網格資料，用於地圖渲染。"""
    now = time.time()
    if (
        _grids_cache["data"]
        and _grids_cache["height"] == height
        and now - _grids_cache["time"] < CACHE_TTL
    ):
        return _grids_cache["data"]

    speed_10m, direction = get_current_wind()
    wind_col = f"wind_{height}m"

    # Direction string from degrees
    dir_labels = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    dir_str = dir_labels[int((direction + 11.25) % 360 / 22.5)]

    grids = []
    lon = PILOT_LON_MIN
    while lon <= PILOT_LON_MAX:
        lat = PILOT_LAT_MIN
        while lat <= PILOT_LAT_MAX:
            z0, zd, bcr, fai = _roughness_params(lon, lat)
            wind_speed = _height_correction(speed_10m, float(height), z0, zd)

            # 小幅空間擾動，讓地圖看起來更真實
            spatial_var = 1.0 + 0.1 * math.sin(lon * 500) * math.cos(lat * 500)
            wind_speed = round(wind_speed * spatial_var, 2)

            risk = _classify_risk(wind_speed)

            # 河川沿線標記為風廊
            is_corridor = (
                lat > 25.052  # 基隆河沿線
                or (121.505 < lon < 121.525 and lat < 25.025)  # 新店溪沿線
            )

            grids.append({
                "grid_id": f"demo-{int(lon * 1000)}-{int(lat * 1000)}",
                "lon": round(lon, 6),
                "lat": round(lat, 6),
                "risk_level": risk,
                "risk_score": _risk_score(wind_speed),
                "wind_speed": wind_speed,
                "wind_direction": dir_str,
                "is_corridor": is_corridor,
            })
            lat += GRID_STEP
        lon += GRID_STEP

    _grids_cache["data"] = grids
    _grids_cache["height"] = height
    _grids_cache["time"] = now
    logger.info("Fallback: generated %d demo grid cells for height=%dm", len(grids), height)
    return grids


# ── Demo 風廊 ────────────────────────────────────────────────

def generate_demo_corridors() -> list[dict]:
    """回傳 5 條基於台北真實地理的風廊。"""
    corridors = [
        {
            "corridor_id": "corridor-keelung-river",
            "name": "基隆河谷風廊",
            "type": "primary",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [121.505, 25.058], [121.520, 25.060], [121.540, 25.058],
                    [121.555, 25.055], [121.570, 25.052], [121.580, 25.055],
                ],
            },
            "mean_wind_speed": 5.8,
            "dominant_direction": "NE",
            "risk_level": "yellow",
        },
        {
            "corridor_id": "corridor-tamsui-river",
            "name": "淡水河風廊",
            "type": "primary",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [121.500, 25.020], [121.505, 25.030], [121.508, 25.040],
                    [121.505, 25.050], [121.502, 25.058],
                ],
            },
            "mean_wind_speed": 5.2,
            "dominant_direction": "NW",
            "risk_level": "yellow",
        },
        {
            "corridor_id": "corridor-xinyi-road",
            "name": "信義路都市風廊",
            "type": "secondary",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [121.510, 25.033], [121.525, 25.033], [121.540, 25.034],
                    [121.555, 25.033], [121.570, 25.033],
                ],
            },
            "mean_wind_speed": 4.1,
            "dominant_direction": "E",
            "risk_level": "green",
        },
        {
            "corridor_id": "corridor-renai-road",
            "name": "仁愛路林蔭風廊",
            "type": "secondary",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [121.515, 25.037], [121.530, 25.037], [121.545, 25.038],
                    [121.560, 25.037], [121.575, 25.036],
                ],
            },
            "mean_wind_speed": 3.8,
            "dominant_direction": "E",
            "risk_level": "green",
        },
        {
            "corridor_id": "corridor-xinsheng-south",
            "name": "新生南路綠帶風廊",
            "type": "secondary",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [121.534, 25.015], [121.534, 25.025], [121.533, 25.035],
                    [121.533, 25.045], [121.534, 25.055],
                ],
            },
            "mean_wind_speed": 3.5,
            "dominant_direction": "S",
            "risk_level": "green",
        },
    ]
    return corridors


# ── Demo FAI ──────────────────────────────────────────────────

def generate_demo_fai(height: int = 50) -> list[dict]:
    """產生台北試驗區的 FAI 數據。"""
    grids = generate_demo_grids(height)
    fai_data = []
    for g in grids:
        lon, lat = g["lon"], g["lat"]
        _, _, bcr, fai = _roughness_params(lon, lat)
        # 空間擾動
        fai_var = fai * (1.0 + 0.15 * math.sin(lon * 800) * math.cos(lat * 800))
        z0, _, _, _ = _roughness_params(lon, lat)
        fai_data.append({
            "grid_id": g["grid_id"],
            "fai_value": round(fai_var, 4),
            "lon": lon,
            "lat": lat,
            "terrain_roughness": round(z0, 4),
            "building_density": round(bcr, 4),
        })
    return fai_data


# ── Demo 統計 ─────────────────────────────────────────────────

def generate_demo_stats() -> dict:
    """從 demo grid 彙總統計數據。"""
    grids = generate_demo_grids(50)
    total = len(grids)
    if total == 0:
        return {}

    risk_dist = {"green": 0, "yellow": 0, "red": 0, "black": 0}
    corridor_count = 0
    total_wind = 0.0

    for g in grids:
        risk_dist[g["risk_level"]] = risk_dist.get(g["risk_level"], 0) + 1
        if g["is_corridor"]:
            corridor_count += 1
        total_wind += g["wind_speed"]

    return {
        "total_grids": total,
        "risk_distribution": risk_dist,
        "corridor_count": corridor_count,
        "mean_wind_speed": round(total_wind / total, 2),
        "monitoring_area_km2": round(total * 0.04, 2),  # ~200m x 200m = 0.04 km²
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
