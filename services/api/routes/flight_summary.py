"""v4 新增 — 飛行摘要聚合端點。

GET /api/v1/flight-summary
一次查詢回傳 Wizard Step3 所需全部資料：
- 風險等級 + 分數
- 風速 / 陣風 / 風向
- 機型安全檢查
- 電池消耗影響
- 風廊警告
- 最佳飛行時段

目標回應 < 300ms。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Query

from core.risk.derived import (
    find_best_flight_windows,
    gust_factor,
    turbulence_intensity,
)
from core.risk.drone_specs import check_flyability, get_drone_spec
from fallback import FALLBACK_GRID_CELLS

logger = logging.getLogger(__name__)

router = APIRouter()

# 機型 ID 對應表
DRONE_ID_MAP = {
    "M30T": "dji-matrice30",
    "M350": "dji-matrice350",
    "Mini4": "dji-mini4-pro",
    "Air3": "dji-air3",
    "Mavic3E": "dji-mavic3",
}


@router.get("/flight-summary", tags=["Flight"])
async def get_flight_summary(
    lat: float = Query(..., ge=21.0, le=26.0, description="緯度"),
    lng: float = Query(..., ge=119.0, le=123.0, description="經度"),
    drone: str = Query(default="M30T", description="機型代碼 (M30T, M350, Mini4, Air3, Mavic3E)"),
    datetime_str: str = Query(
        default=None,
        alias="datetime",
        description="ISO 8601 日期時間（預設為當前時間）",
    ),
    altitude: float = Query(default=80.0, ge=10, le=500, description="飛行高度 (m AGL)"),
):
    """回傳飛行風險摘要 — Wizard Step3 結論面板所需全部資料。"""
    # 解析時間
    if datetime_str:
        try:
            dt = datetime.fromisoformat(datetime_str)
        except ValueError:
            dt = datetime.now(timezone.utc)
    else:
        dt = datetime.now(timezone.utc)

    # 解析機型
    drone_id = DRONE_ID_MAP.get(drone, drone)

    # 取得風場資料
    wind_speed = 6.8
    wind_gust = 10.2
    wind_direction = 45.0
    wind_direction_label = "NE"
    risk_level = "yellow"
    risk_score = 38
    in_corridor = False
    corridor_warning = None
    z0 = 0.5
    zd = 5.0
    fai_max = 0.3

    try:
        from db.session import get_engine, table_exists

        engine = get_engine()
        if engine and table_exists(engine, "grid_cells"):
            from sqlalchemy import text

            with engine.connect() as conn:
                result = conn.execute(
                    text(
                        "SELECT *, "
                        "ST_Distance(geom::geography, ST_SetSRID(ST_Point(:lng, :lat), 4326)::geography) as dist "
                        "FROM grid_cells "
                        "ORDER BY geom <-> ST_SetSRID(ST_Point(:lng, :lat), 4326) "
                        "LIMIT 1"
                    ),
                    {"lng": lng, "lat": lat},
                )
                row = result.fetchone()
                if row:
                    mapping = row._mapping
                    wind_speed = float(mapping.get("wind_speed_80m", 6.8) or 6.8)
                    risk_level = str(mapping.get("risk_level", "yellow") or "yellow")
                    risk_score = int(mapping.get("risk_score", 38) or 38)
                    z0 = float(mapping.get("z0", 0.5) or 0.5)
                    zd = float(mapping.get("zd", 5.0) or 5.0)
                    fai_max_val = mapping.get("fai_max")
                    if fai_max_val is not None:
                        fai_max = float(fai_max_val)
                    in_corridor = bool(mapping.get("is_corridor", False))
    except Exception as e:
        logger.warning("DB query failed, using fallback data: %s", e)

    # 計算衍生指標
    ti = turbulence_intensity(altitude, z0, zd)
    gf = gust_factor(ti, fai_max)
    wind_gust = wind_speed * gf

    # 機型安全檢查
    flyability = check_flyability(wind_speed, drone_id)
    drone_ok = flyability["flyable"]
    drone_safe_limit = flyability.get("tolerance", 10.5)

    # 電池影響估算（簡化）
    battery_extra_pct = round(wind_speed * 4.1, 1)  # 約每 m/s 增加 4% 消耗

    # 風廊警告
    if in_corridor:
        corridor_warning = "位於主風廊中，側風加速效應，建議降低飛行速度"

    # 最佳飛行時段
    best_windows = []
    worst_period = None
    try:
        from core.ingest.open_meteo import fetch_forecast

        forecasts = fetch_forecast(lat, lng, hours=24)
        if forecasts:
            max_wind = drone_safe_limit * 0.7
            windows = find_best_flight_windows(forecasts, max_wind)
            best_windows = [
                {
                    "start": w["start"].strftime("%H:%M") if hasattr(w["start"], "strftime") else str(w["start"]),
                    "end": w["end"].strftime("%H:%M") if hasattr(w["end"], "strftime") else str(w["end"]),
                    "risk": "green",
                }
                for w in windows[:3]
            ]
            # 找最差時段
            if forecasts:
                max_wind_fc = max(forecasts, key=lambda f: f.get("wind_speed", 0))
                if max_wind_fc.get("wind_speed", 0) > max_wind:
                    worst_period = {
                        "start": "13:00",
                        "end": "17:00",
                        "risk": "red",
                    }
    except Exception as e:
        logger.warning("Forecast fetch failed: %s", e)

    # 如果沒有真實時段資料，提供預設
    if not best_windows:
        best_windows = [
            {"start": "06:00", "end": "09:00", "risk": "green"},
            {"start": "20:00", "end": "23:00", "risk": "green"},
        ]
    if worst_period is None:
        worst_period = {"start": "13:00", "end": "17:00", "risk": "red"}

    # 風向標籤
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                   "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = int((wind_direction + 11.25) / 22.5) % 16
    wind_direction_label = directions[idx]

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "wind_speed": round(wind_speed, 1),
        "wind_gust": round(wind_gust, 1),
        "wind_direction_label": wind_direction_label,
        "drone_ok": drone_ok,
        "drone_safe_limit": drone_safe_limit,
        "battery_extra_pct": battery_extra_pct,
        "in_corridor": in_corridor,
        "corridor_warning": corridor_warning,
        "best_windows": best_windows,
        "worst_period": worst_period,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
