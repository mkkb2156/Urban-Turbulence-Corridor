"""衍生數據 API — 湍流、風切變、陣風、遮蔽、高度限制、飛行窗口。"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Query as QueryParam

from src.risk.derived import (
    compute_all_derived,
    find_best_flight_windows,
    headwind_crosswind,
    weibull_exceedance,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_engine():
    from src.db.queries import get_engine
    return get_engine()


def _table_exists(conn, table_name: str) -> bool:
    from sqlalchemy import text
    result = conn.execute(
        text(
            "SELECT EXISTS ("
            "  SELECT FROM information_schema.tables "
            "  WHERE table_name = :tbl"
            ")"
        ),
        {"tbl": table_name},
    ).scalar()
    return bool(result)


@router.get("/derived/{grid_id}")
async def get_derived_data(grid_id: str):
    """取得指定網格的所有衍生數據。"""
    from sqlalchemy import text

    try:
        engine = _get_engine()
        with engine.connect() as conn:
            if not _table_exists(conn, "grid_cells"):
                raise RuntimeError("grid_cells table not found")

            row = conn.execute(text("""
                SELECT
                    grid_id,
                    ST_X(ST_Centroid(ST_Transform(geometry, 4326))) AS lon,
                    ST_Y(ST_Centroid(ST_Transform(geometry, 4326))) AS lat,
                    z0, zd, svf, bcr,
                    fai_ne, fai_sw, fai_max, fai_max_direction,
                    mean_height, max_height, n_buildings,
                    wind_50m, wind_80m, wind_120m,
                    risk_level, risk_score, is_corridor,
                    turbulence_50m, turbulence_80m, turbulence_120m,
                    shear_50_80, shear_80_120,
                    gust_factor, shelter_index,
                    min_safe_alt, max_legal_alt,
                    wind_direction_deg
                FROM grid_cells
                WHERE grid_id = :gid
            """), {"gid": grid_id}).fetchone()

            if not row:
                return {"error": f"Grid cell '{grid_id}' not found"}

            m = row._mapping
            data = dict(m)

            # 如果衍生欄位尚未回填，即時計算
            derived = compute_all_derived(data)

            # 合併：DB 有值用 DB，沒值用即時計算
            for key, val in derived.items():
                if key not in data or data.get(key) is None:
                    data[key] = val

            # 格式化回應
            return {
                "grid_id": data["grid_id"],
                "lon": round(float(data.get("lon") or 0), 6),
                "lat": round(float(data.get("lat") or 0), 6),

                # 原始形態學
                "morphology": {
                    "z0": data.get("z0"),
                    "zd": data.get("zd"),
                    "svf": data.get("svf"),
                    "bcr": data.get("bcr"),
                    "mean_height": data.get("mean_height"),
                    "max_height": data.get("max_height"),
                    "n_buildings": data.get("n_buildings"),
                    "fai_ne": data.get("fai_ne"),
                    "fai_sw": data.get("fai_sw"),
                    "fai_max": data.get("fai_max"),
                },

                # 風速
                "wind": {
                    "speed_50m": data.get("wind_50m"),
                    "speed_80m": data.get("wind_80m"),
                    "speed_120m": data.get("wind_120m"),
                    "direction_deg": data.get("wind_direction_deg"),
                },

                # 衍生指標
                "derived": {
                    "turbulence": {
                        "ti_50m": data.get("turbulence_50m") or derived.get("turbulence_50m"),
                        "ti_80m": data.get("turbulence_80m") or derived.get("turbulence_80m"),
                        "ti_120m": data.get("turbulence_120m") or derived.get("turbulence_120m"),
                        "assessment": _ti_assessment(data.get("turbulence_50m") or derived.get("turbulence_50m")),
                    },
                    "wind_shear": {
                        "shear_50_80": data.get("shear_50_80") or derived.get("shear_50_80"),
                        "shear_80_120": data.get("shear_80_120") or derived.get("shear_80_120"),
                        "assessment": _shear_assessment(data.get("shear_50_80") or derived.get("shear_50_80")),
                    },
                    "gust": {
                        "gust_factor": data.get("gust_factor") or derived.get("gust_factor"),
                        "gust_speed_50m": derived.get("gust_speed_50m"),
                        "gust_speed_80m": derived.get("gust_speed_80m"),
                        "gust_speed_120m": derived.get("gust_speed_120m"),
                    },
                    "shelter": {
                        "shelter_index": data.get("shelter_index") or derived.get("shelter_index"),
                        "assessment": _shelter_assessment(data.get("shelter_index") or derived.get("shelter_index")),
                    },
                    "altitude": {
                        "min_safe_alt": data.get("min_safe_alt") or derived.get("min_safe_alt"),
                        "max_legal_alt": data.get("max_legal_alt") or derived.get("max_legal_alt"),
                        "flyable_range_m": derived.get("flyable_range_m"),
                    },
                },

                # 風險
                "risk": {
                    "level": data.get("risk_level"),
                    "score": data.get("risk_score"),
                    "is_corridor": bool(data.get("is_corridor")),
                },

                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

    except Exception as exc:
        logger.warning("Derived data query failed: %s", exc)
        return {"error": str(exc)}


@router.get("/derived/{grid_id}/flyability")
async def check_flyability_derived(
    grid_id: str,
    drone_id: str = QueryParam("dji-mini4-pro", description="無人機型號"),
    height: int = QueryParam(50, description="飛行高度: 50, 80, 120"),
):
    """結合衍生數據的無人機適飛性詳細檢查。"""
    from sqlalchemy import text

    drone_specs = {
        "dji-mini4-pro": {"name": "DJI Mini 4 Pro", "max_wind": 10.7, "weight": 0.249},
        "dji-air3": {"name": "DJI Air 3", "max_wind": 12.0, "weight": 0.720},
        "dji-mavic3": {"name": "DJI Mavic 3", "max_wind": 12.0, "weight": 0.895},
        "dji-matrice350": {"name": "DJI Matrice 350 RTK", "max_wind": 15.0, "weight": 6.470},
        "dji-matrice30": {"name": "DJI Matrice 30", "max_wind": 15.0, "weight": 3.770},
    }
    spec = drone_specs.get(drone_id, {"name": drone_id, "max_wind": 10.0, "weight": 1.0})

    if height not in (50, 80, 120):
        height = 50
    wind_col = f"wind_{height}m"

    try:
        engine = _get_engine()
        with engine.connect() as conn:
            row = conn.execute(text(f"""
                SELECT
                    grid_id, z0, zd, svf, bcr,
                    fai_ne, fai_sw, fai_max,
                    mean_height, max_height,
                    wind_50m, wind_80m, wind_120m,
                    risk_level, risk_score, is_corridor
                FROM grid_cells
                WHERE grid_id = :gid
            """), {"gid": grid_id}).fetchone()

            if not row:
                return {"error": f"Grid cell '{grid_id}' not found"}

            data = dict(row._mapping)
            derived = compute_all_derived(data)

            wind_speed = data.get(wind_col) or 0
            gf = derived.get("gust_factor") or 1.5
            gust_speed = wind_speed * gf
            ti = derived.get(f"turbulence_{height}m") or 0.3

            flyable = wind_speed <= spec["max_wind"] * 0.7
            gust_safe = gust_speed <= spec["max_wind"]

            # 綜合建議
            issues = []
            if not flyable:
                issues.append(f"平均風速 {wind_speed:.1f} m/s 超過安全閾值 {spec['max_wind'] * 0.7:.1f} m/s")
            if not gust_safe:
                issues.append(f"預估陣風 {gust_speed:.1f} m/s 超過最大抗風能力 {spec['max_wind']:.1f} m/s")
            if ti and ti > 0.35:
                issues.append(f"湍流強度 {ti:.2f} 偏高，消費級無人機可能不穩定")
            shear = derived.get("shear_50_80")
            if shear and shear > 0.3:
                issues.append(f"風切變指數 {shear:.2f} 偏高，起降階段需注意")

            return {
                "grid_id": grid_id,
                "drone": spec,
                "height": height,
                "wind_speed": round(wind_speed, 1),
                "gust_speed": round(gust_speed, 1),
                "turbulence_intensity": round(ti, 3) if ti else None,
                "flyable": flyable and gust_safe,
                "flyable_mean_wind": flyable,
                "flyable_gust": gust_safe,
                "issues": issues,
                "recommendation": "適合飛行" if (flyable and gust_safe and not issues) else "建議謹慎" if flyable else "不建議飛行",
                "derived": derived,
            }

    except Exception as exc:
        logger.warning("Flyability check failed: %s", exc)
        return {"error": str(exc)}


@router.get("/forecast/flight-windows")
async def get_flight_windows(
    lon: float = QueryParam(121.55, ge=119, le=123),
    lat: float = QueryParam(25.03, ge=21, le=26),
    drone_id: str = QueryParam("dji-mini4-pro"),
    hours: int = QueryParam(72, ge=1, le=168),
    min_hours: int = QueryParam(2, ge=1, le=8),
):
    """找出指定地點未來最佳飛行時段。"""
    from src.api.routes.forecast import _fetch_real_forecast, _generate_mock_forecast

    drone_tolerances = {
        "dji-mini4-pro": 10.7, "dji-air3": 12.0, "dji-mavic3": 12.0,
        "dji-matrice350": 15.0, "dji-matrice30": 15.0,
    }
    max_wind = drone_tolerances.get(drone_id, 10.0)

    forecasts = _fetch_real_forecast("taipei", hours, lat=lat, lon=lon)
    source = "open-meteo"
    if forecasts is None:
        forecasts = _generate_mock_forecast(hours)
        source = "mock"

    windows = find_best_flight_windows(forecasts, max_wind, min_hours)

    return {
        "lon": lon,
        "lat": lat,
        "drone_id": drone_id,
        "max_wind_tolerance": max_wind,
        "safe_wind_threshold": round(max_wind * 0.7, 1),
        "source": source,
        "total_hours": hours,
        "flyable_hours": sum(w["hours"] for w in windows),
        "flyable_pct": round(sum(w["hours"] for w in windows) / hours * 100, 1),
        "windows": windows,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ── 評估文字 ─────────────────────────────────────────────────────

def _ti_assessment(ti: float | None) -> str:
    if ti is None:
        return "資料不足"
    if ti < 0.15:
        return "極低湍流，非常適合飛行"
    if ti < 0.25:
        return "低湍流，適合飛行"
    if ti < 0.35:
        return "中等湍流，消費級無人機需注意"
    if ti < 0.50:
        return "高湍流，僅建議專業級無人機"
    return "極高湍流，不建議飛行"


def _shear_assessment(shear: float | None) -> str:
    if shear is None:
        return "資料不足"
    if shear < 0.15:
        return "低風切變，起降安全"
    if shear < 0.25:
        return "中等風切變，起降時稍注意"
    if shear < 0.35:
        return "高風切變，起降時需特別注意"
    return "極高風切變，起降風險高"


def _shelter_assessment(si: float | None) -> str:
    if si is None:
        return "資料不足"
    if si < 0.1:
        return "低遮蔽，風速接近自由大氣"
    if si < 0.3:
        return "中等遮蔽，有一定建築擋風效果"
    if si < 0.6:
        return "高遮蔽，風速較低但可能有渦流"
    return "極高遮蔽，建築密集區域，注意亂流"
