"""風場預報 API — 真實 Open-Meteo 數據 + mock fallback。"""

from __future__ import annotations

import logging
import math
import random
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query as QueryParam

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Risk classification ──

def _classify_risk(speed: float) -> str:
    if speed <= 5:
        return "green"
    elif speed <= 8:
        return "yellow"
    elif speed <= 12:
        return "red"
    return "black"


# ── Real data fetch ──

def _fetch_real_forecast(
    city: str,
    hours: int,
    lat: float | None = None,
    lon: float | None = None,
) -> list[dict] | None:
    """嘗試從 Open-Meteo 取得真實預報，失敗回傳 None。"""
    try:
        from src.ingest.open_meteo import fetch_forecast_wind

        df = fetch_forecast_wind(city=city, hours=hours, lat=lat, lon=lon)
        if df.empty:
            return None

        forecasts = []
        for _, row in df.iterrows():
            speed = float(row["wind_speed"])
            direction = float(row["wind_direction"])
            gusts = float(row["wind_gusts"]) if row.get("wind_gusts") is not None and not math.isnan(row["wind_gusts"]) else None

            forecasts.append({
                "time": row["time"].isoformat(),
                "wind_speed": round(speed, 1),
                "wind_direction": round(direction, 1),
                "wind_gusts": round(gusts, 1) if gusts is not None else None,
                "risk_level": _classify_risk(speed),
                "wind_speed_80m": round(float(row["wind_speed_80m"]), 1) if row.get("wind_speed_80m") is not None and not math.isnan(row["wind_speed_80m"]) else None,
                "wind_direction_80m": round(float(row["wind_direction_80m"]), 1) if row.get("wind_direction_80m") is not None and not math.isnan(row["wind_direction_80m"]) else None,
                "wind_speed_120m": round(float(row["wind_speed_120m"]), 1) if row.get("wind_speed_120m") is not None and not math.isnan(row["wind_speed_120m"]) else None,
                "wind_direction_120m": round(float(row["wind_direction_120m"]), 1) if row.get("wind_direction_120m") is not None and not math.isnan(row["wind_direction_120m"]) else None,
            })

        logger.info("Real forecast: %d records from Open-Meteo", len(forecasts))
        return forecasts

    except Exception as e:
        logger.warning("Failed to fetch real forecast, falling back to mock: %s", e)
        return None


def _interpolate_height(forecast: dict, height: float) -> dict:
    """根據飛行高度從多高度層數據選取最佳風速。

    Open-Meteo 提供 10m / 80m / 120m 三層。
    若有對應高度層實測值則直接使用，否則用 log profile 插值。
    """
    result = dict(forecast)

    if height >= 100 and forecast.get("wind_speed_120m") is not None:
        result["wind_speed"] = forecast["wind_speed_120m"]
        result["wind_direction"] = forecast["wind_direction_120m"]
    elif height >= 60 and forecast.get("wind_speed_80m") is not None:
        result["wind_speed"] = forecast["wind_speed_80m"]
        result["wind_direction"] = forecast["wind_direction_80m"]
    elif height > 16:
        # log profile 從 10m 外推
        z0, zd = 1.0, 15.0
        factor = math.log((height - zd) / z0) / math.log((10.0 - zd) / z0) if 10.0 > zd + z0 else 1.0
        result["wind_speed"] = round(forecast["wind_speed"] * max(factor, 1.0), 1)

    result["risk_level"] = _classify_risk(result["wind_speed"])
    return result


# ── Mock fallback ──

def _generate_mock_forecast(hours: int, base_speed: float = 4.5) -> list[dict]:
    """產生逐時風場預報 mock data（當真實 API 不可用時）。"""
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    forecasts = []

    for h in range(hours):
        t = now + timedelta(hours=h)
        hour_of_day = (t.hour + 8) % 24

        diurnal = 1.0 + 0.3 * math.sin((hour_of_day - 6) * math.pi / 12)
        trend = 1.0 + 0.4 * math.sin(h * math.pi / 36)
        speed = base_speed * diurnal * trend + random.gauss(0, 0.5)
        speed = max(0.5, round(speed, 1))

        direction = 45 + 20 * math.sin(h * math.pi / 24) + random.gauss(0, 10)
        direction = round(direction % 360, 1)

        gust_factor = 1.3 + random.random() * 0.5
        gusts = round(speed * gust_factor, 1)

        forecasts.append({
            "time": t.isoformat(),
            "wind_speed": speed,
            "wind_direction": direction,
            "wind_gusts": gusts,
            "risk_level": _classify_risk(speed),
            "wind_speed_80m": None,
            "wind_direction_80m": None,
            "wind_speed_120m": None,
            "wind_direction_120m": None,
        })

    return forecasts


# ── API endpoints ──

@router.get("/forecast")
async def get_forecast(
    city: str = QueryParam("taipei", description="城市"),
    hours: int = QueryParam(72, ge=1, le=168, description="預報時數"),
):
    """取得逐時風場預報。優先使用 Open-Meteo 真實數據，失敗時回退 mock。"""
    forecasts = _fetch_real_forecast(city, hours)
    source = "open-meteo"

    if forecasts is None:
        forecasts = _generate_mock_forecast(hours)
        source = "mock"

    return {
        "city": city,
        "hours": hours,
        "source": source,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "forecasts": forecasts,
    }


@router.get("/forecast/at")
async def get_forecast_at_point(
    lon: float = QueryParam(..., ge=119, le=123, description="經度"),
    lat: float = QueryParam(..., ge=21, le=26, description="緯度"),
    height: float = QueryParam(50.0, ge=0, le=500, description="飛行高度 (m)"),
    hours: int = QueryParam(72, ge=1, le=168, description="預報時數"),
):
    """取得特定座標的逐時風場預報（含高度插值）。"""
    forecasts = _fetch_real_forecast("taipei", hours, lat=lat, lon=lon)
    source = "open-meteo"

    if forecasts is None:
        z0, zd, ref_height = 1.0, 15.0, 10.0
        height_factor = math.log((height - zd) / z0) / math.log(ref_height / z0) if height > zd + z0 else 1.0
        lon_factor = 1.0 + 0.1 * (lon - 121.5)
        lat_factor = 1.0 + 0.05 * (lat - 25.0)
        base_speed = 4.5 * height_factor * lon_factor * lat_factor
        forecasts = _generate_mock_forecast(hours, base_speed=max(1.0, base_speed))
        source = "mock"
    else:
        forecasts = [_interpolate_height(f, height) for f in forecasts]

    return {
        "lon": lon,
        "lat": lat,
        "height": height,
        "hours": hours,
        "source": source,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "forecasts": forecasts,
    }


# ── CWA 即時測站 ──

@router.get("/forecast/stations")
async def get_cwa_stations(
    region: str = QueryParam("taipei", description="區域"),
):
    """取得 CWA 即時測站風場觀測。"""
    try:
        from src.ingest.cwa_weather import fetch_current_observations, filter_taipei_stations

        df = fetch_current_observations()
        if region == "taipei":
            df = filter_taipei_stations(df)

        stations = []
        for _, row in df.iterrows():
            speed = row.get("wind_speed")
            if speed is None or (isinstance(speed, float) and math.isnan(speed)):
                continue
            stations.append({
                "station_id": row["station_id"],
                "station_name": row["station_name"],
                "lat": round(float(row["latitude"]), 6),
                "lon": round(float(row["longitude"]), 6),
                "wind_speed": round(float(speed), 1),
                "wind_direction": round(float(row["wind_direction"]), 1) if row.get("wind_direction") is not None and not (isinstance(row["wind_direction"], float) and math.isnan(row["wind_direction"])) else None,
                "gust_speed": round(float(row["gust_speed"]), 1) if row.get("gust_speed") is not None and not (isinstance(row["gust_speed"], float) and math.isnan(row["gust_speed"])) else None,
                "observation_time": row.get("observation_time"),
                "risk_level": _classify_risk(float(speed)),
            })

        logger.info("CWA stations: %d records for %s", len(stations), region)
        return {
            "region": region,
            "source": "cwa",
            "station_count": len(stations),
            "stations": stations,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.warning("Failed to fetch CWA stations: %s", e)
        return {
            "region": region,
            "source": "error",
            "station_count": 0,
            "stations": [],
            "error": str(e),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
