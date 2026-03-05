"""風場預報 API（mock data for demo）。"""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query as QueryParam

router = APIRouter()


def _generate_mock_forecast(hours: int, base_speed: float = 4.5) -> list[dict]:
    """產生逐時風場預報 mock data。

    模擬台北東北季風模式：
    - 清晨風速較低，午後增強
    - 風向以 NE (45°) 為主，加入隨機擾動
    - 陣風為平均風速的 1.3-1.8 倍
    """
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    forecasts = []

    for h in range(hours):
        t = now + timedelta(hours=h)
        hour_of_day = (t.hour + 8) % 24  # UTC -> Taipei time

        # 日變化：凌晨低、午後高
        diurnal = 1.0 + 0.3 * math.sin((hour_of_day - 6) * math.pi / 12)
        # 多日趨勢：模擬鋒面通過
        trend = 1.0 + 0.4 * math.sin(h * math.pi / 36)
        speed = base_speed * diurnal * trend + random.gauss(0, 0.5)
        speed = max(0.5, round(speed, 1))

        direction = 45 + 20 * math.sin(h * math.pi / 24) + random.gauss(0, 10)
        direction = round(direction % 360, 1)

        gust_factor = 1.3 + random.random() * 0.5
        gusts = round(speed * gust_factor, 1)

        # 風險等級
        if speed <= 5:
            risk = "green"
        elif speed <= 8:
            risk = "yellow"
        elif speed <= 12:
            risk = "red"
        else:
            risk = "black"

        forecasts.append({
            "time": t.isoformat(),
            "wind_speed": speed,
            "wind_direction": direction,
            "wind_gusts": gusts,
            "risk_level": risk,
        })

    return forecasts


@router.get("/forecast")
async def get_forecast(
    city: str = QueryParam("taipei", description="城市"),
    hours: int = QueryParam(72, ge=1, le=168, description="預報時數"),
):
    """取得逐時風場預報（mock）。"""
    return {
        "city": city,
        "hours": hours,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "forecasts": _generate_mock_forecast(hours),
    }


@router.get("/forecast/at")
async def get_forecast_at_point(
    lon: float = QueryParam(..., ge=119, le=123, description="經度"),
    lat: float = QueryParam(..., ge=21, le=26, description="緯度"),
    height: float = QueryParam(50.0, ge=0, le=500, description="飛行高度 (m)"),
    hours: int = QueryParam(72, ge=1, le=168, description="預報時數"),
):
    """取得特定座標的逐時風場預報（含 log profile 降尺度 mock）。

    高度越高風速越大（對數剖面近似）。
    """
    # 高度修正因子（對數剖面近似）
    z0 = 1.0  # 都市粗糙度
    zd = 15.0  # 零平面位移
    ref_height = 10.0
    if height > zd + z0:
        height_factor = math.log((height - zd) / z0) / math.log((ref_height) / z0)
    else:
        height_factor = 1.0

    # 位置修正：信義區風速偏高
    lon_factor = 1.0 + 0.1 * (lon - 121.5)
    lat_factor = 1.0 + 0.05 * (lat - 25.0)
    base_speed = 4.5 * height_factor * lon_factor * lat_factor

    forecasts = _generate_mock_forecast(hours, base_speed=max(1.0, base_speed))

    return {
        "lon": lon,
        "lat": lat,
        "height": height,
        "height_factor": round(height_factor, 2),
        "hours": hours,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "forecasts": forecasts,
    }
