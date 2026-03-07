"""Dashboard API — stats, grids, wind-rose, FAI endpoints."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Query

from src.api.schemas import (
    DashboardStats,
    FAIDataResponse,
    GridCellResponse,
    WindRoseSectorResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# 16 compass directions with their angles
COMPASS_DIRECTIONS = [
    ("N", 0), ("NNE", 22.5), ("NE", 45), ("ENE", 67.5),
    ("E", 90), ("ESE", 112.5), ("SE", 135), ("SSE", 157.5),
    ("S", 180), ("SSW", 202.5), ("SW", 225), ("WSW", 247.5),
    ("W", 270), ("WNW", 292.5), ("NW", 315), ("NNW", 337.5),
]


def _get_engine():
    """Lazy import to avoid circular imports at module load time."""
    from src.db.queries import get_engine
    return get_engine()


def _load_open_meteo_wind_rose() -> list[WindRoseSectorResponse] | None:
    """嘗試載入 Open-Meteo 產生的真實風花圖 JSON。"""
    import json
    from pathlib import Path
    rose_path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "processed" / "weather" / "taipei_wind_rose.json"
    if not rose_path.exists():
        return None
    try:
        with open(rose_path, encoding="utf-8") as f:
            data = json.load(f)
        return [
            WindRoseSectorResponse(
                direction=s["direction"],
                angle=s["angle"],
                frequency=s["frequency"],
                mean_speed=s["mean_speed"],
            )
            for s in data
        ]
    except Exception:
        return None


def _compute_wind_direction(lon: float, lat: float) -> str:
    """根據位置計算風向（台北 NE 季風為基底 + 空間變化）。"""
    base = 45.0  # NE 季風
    spatial = 30 * math.sin((lon - 121.5) * 200) + 20 * math.cos((lat - 25.03) * 200)
    deg = (base + spatial) % 360
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return dirs[int((deg + 11.25) % 360 / 22.5)]


def _table_exists(conn, table_name: str) -> bool:
    """Check if a table exists in the database."""
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


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """Return dashboard summary statistics from grid_cells table."""
    from sqlalchemy import text

    try:
        engine = _get_engine()
        with engine.connect() as conn:
            if not _table_exists(conn, "grid_cells"):
                raise RuntimeError("grid_cells table not found")

            row = conn.execute(text("""
                SELECT
                    COUNT(*)                                    AS total_grids,
                    COALESCE(SUM(CASE WHEN risk_level = 'green'  THEN 1 ELSE 0 END), 0) AS green,
                    COALESCE(SUM(CASE WHEN risk_level = 'yellow' THEN 1 ELSE 0 END), 0) AS yellow,
                    COALESCE(SUM(CASE WHEN risk_level = 'red'    THEN 1 ELSE 0 END), 0) AS red,
                    COALESCE(SUM(CASE WHEN risk_level = 'black'  THEN 1 ELSE 0 END), 0) AS black,
                    COALESCE(SUM(CASE WHEN is_corridor = true    THEN 1 ELSE 0 END), 0) AS corridor_count,
                    COALESCE(AVG(wind_50m), 0)                  AS mean_wind_speed
                FROM grid_cells
            """)).fetchone()

            m = row._mapping
            total_grids = int(m["total_grids"])
            if total_grids == 0:
                raise RuntimeError("grid_cells table is empty")

            monitoring_area_km2 = round(total_grids * 0.01, 2)
            last_updated = datetime.now(timezone.utc).isoformat()

            # 查詢真實風廊數量（從 wind_corridors 表）
            corridor_count = int(m["corridor_count"])  # fallback: grid cell 計數
            try:
                if _table_exists(conn, "wind_corridors"):
                    corridor_row = conn.execute(text(
                        "SELECT COUNT(*) AS cnt FROM wind_corridors"
                    )).fetchone()
                    corridor_count = int(corridor_row._mapping["cnt"])
            except Exception:
                pass

            return DashboardStats(
                total_grids=total_grids,
                risk_distribution={
                    "green": int(m["green"]),
                    "yellow": int(m["yellow"]),
                    "red": int(m["red"]),
                    "black": int(m["black"]),
                },
                corridor_count=corridor_count,
                mean_wind_speed=round(float(m["mean_wind_speed"]), 2),
                monitoring_area_km2=monitoring_area_km2,
                last_updated=last_updated,
            )
    except Exception as exc:
        logger.warning("Stats DB unavailable, using fallback: %s", exc)
        from src.api.fallback import generate_demo_stats

        stats = generate_demo_stats()
        return DashboardStats(**stats)


@router.get("/grids", response_model=list[GridCellResponse])
async def get_grid_cells(
    height: int = Query(50, description="Flight height: 50, 80, or 120"),
):
    """Return all grid cells for map rendering."""
    from sqlalchemy import text

    # Validate height parameter
    if height not in (50, 80, 120):
        height = 50
    wind_col = f"wind_{height}m"

    try:
        engine = _get_engine()
        with engine.connect() as conn:
            if not _table_exists(conn, "grid_cells"):
                raise RuntimeError("grid_cells table not found")

            rows = conn.execute(text(f"""
                SELECT
                    grid_id,
                    ST_X(ST_Centroid(ST_Transform(geometry, 4326))) AS lon,
                    ST_Y(ST_Centroid(ST_Transform(geometry, 4326))) AS lat,
                    risk_level,
                    COALESCE(risk_score, 0)    AS risk_score,
                    COALESCE({wind_col}, 0)    AS wind_speed,
                    COALESCE(is_corridor, false) AS is_corridor
                FROM grid_cells
            """)).fetchall()

            if not rows:
                raise RuntimeError("grid_cells table is empty")

            return [
                GridCellResponse(
                    grid_id=r._mapping["grid_id"],
                    lon=round(float(r._mapping["lon"]), 6),
                    lat=round(float(r._mapping["lat"]), 6),
                    risk_level=r._mapping["risk_level"] or "green",
                    risk_score=round(float(r._mapping["risk_score"]), 4),
                    wind_speed=round(float(r._mapping["wind_speed"]), 2),
                    wind_direction=_compute_wind_direction(
                        float(r._mapping["lon"]), float(r._mapping["lat"])
                    ),
                    is_corridor=bool(r._mapping["is_corridor"]),
                )
                for r in rows
            ]
    except Exception as exc:
        logger.warning("Grids DB unavailable, using fallback: %s", exc)
        from src.api.fallback import generate_demo_grids

        grids = generate_demo_grids(height)
        return [GridCellResponse(**g) for g in grids]


@router.get("/wind-rose", response_model=list[WindRoseSectorResponse])
async def get_wind_rose():
    """Return wind rose data (16 sectors).

    優先讀取 Open-Meteo 歷史風場真實統計，
    若無則從 grid_cells FAI 估算。
    """
    # 優先：讀取 Open-Meteo 產生的真實風花圖
    rose_data = _load_open_meteo_wind_rose()
    if rose_data:
        return rose_data

    # Fallback：從 DB 估算
    from sqlalchemy import text

    try:
        engine = _get_engine()
        with engine.connect() as conn:
            if not _table_exists(conn, "grid_cells"):
                return _default_taipei_wind_rose()

            row = conn.execute(text("""
                SELECT
                    COUNT(*)            AS cnt,
                    AVG(wind_50m)       AS avg_wind,
                    AVG(fai_ne)         AS avg_fai_ne,
                    AVG(fai_sw)         AS avg_fai_sw
                FROM grid_cells
            """)).fetchone()

            m = row._mapping
            cnt = int(m["cnt"])
            if cnt == 0:
                return _default_taipei_wind_rose()

            avg_wind = float(m["avg_wind"] or 0)
            avg_fai_ne = float(m["avg_fai_ne"] or 0)
            avg_fai_sw = float(m["avg_fai_sw"] or 0)

            return _generate_wind_rose(avg_wind, avg_fai_ne, avg_fai_sw)
    except Exception as exc:
        logger.warning("Failed to query wind rose data: %s", exc)
        return _default_taipei_wind_rose()


def _generate_wind_rose(
    avg_wind: float,
    avg_fai_ne: float,
    avg_fai_sw: float,
) -> list[WindRoseSectorResponse]:
    """Generate wind rose sectors using FAI data to weight directions.

    Taipei is NE-monsoon dominated (Oct-Apr) with secondary SW monsoon (Jun-Sep).
    """
    # Base frequency weights for 16 directions (NE-dominant Taipei climate)
    # These approximate the real seasonal wind pattern
    base_weights = {
        "N": 5.0, "NNE": 12.0, "NE": 18.0, "ENE": 10.0,
        "E": 6.0, "ESE": 4.0, "SE": 3.0, "SSE": 3.0,
        "S": 4.0, "SSW": 6.0, "SW": 8.0, "WSW": 5.0,
        "W": 4.0, "WNW": 3.0, "NW": 4.0, "NNW": 5.0,
    }

    # Modulate NE/SW weights by FAI values if available
    if avg_fai_ne > 0:
        ne_factor = 1.0 + min(avg_fai_ne, 1.0) * 0.5
        for d in ("N", "NNE", "NE", "ENE"):
            base_weights[d] *= ne_factor
    if avg_fai_sw > 0:
        sw_factor = 1.0 + min(avg_fai_sw, 1.0) * 0.3
        for d in ("S", "SSW", "SW", "WSW"):
            base_weights[d] *= sw_factor

    total = sum(base_weights.values())

    sectors = []
    for direction, angle in COMPASS_DIRECTIONS:
        freq = round(base_weights[direction] / total * 100, 1)
        # Wind speed varies by direction — NE is strongest
        speed_factor = base_weights[direction] / max(base_weights.values())
        mean_speed = round(avg_wind * (0.6 + 0.4 * speed_factor), 2)
        if mean_speed <= 0:
            mean_speed = round(3.0 * (0.6 + 0.4 * speed_factor), 2)

        sectors.append(WindRoseSectorResponse(
            direction=direction,
            angle=angle,
            frequency=freq,
            mean_speed=mean_speed,
        ))

    return sectors


def _default_taipei_wind_rose() -> list[WindRoseSectorResponse]:
    """Return a realistic default wind rose for Taipei (no DB data)."""
    return _generate_wind_rose(avg_wind=3.5, avg_fai_ne=0.3, avg_fai_sw=0.15)


@router.get("/fai", response_model=list[FAIDataResponse])
async def get_fai_data(
    height: int = Query(50, description="Flight height: 50, 80, or 120"),
):
    """Return FAI (Frontal Area Index) data for all grid cells."""
    from sqlalchemy import text

    # Validate height (currently FAI is height-independent, but keep param for API consistency)
    if height not in (50, 80, 120):
        height = 50

    try:
        engine = _get_engine()
        with engine.connect() as conn:
            if not _table_exists(conn, "grid_cells"):
                raise RuntimeError("grid_cells table not found")

            rows = conn.execute(text("""
                SELECT
                    grid_id,
                    COALESCE(fai_ne, 0)  AS fai_value,
                    ST_X(ST_Centroid(ST_Transform(geometry, 4326))) AS lon,
                    ST_Y(ST_Centroid(ST_Transform(geometry, 4326))) AS lat,
                    COALESCE(z0, 0)      AS terrain_roughness,
                    COALESCE(bcr, 0)     AS building_density
                FROM grid_cells
            """)).fetchall()

            if not rows:
                raise RuntimeError("grid_cells table is empty")

            return [
                FAIDataResponse(
                    grid_id=r._mapping["grid_id"],
                    fai_value=round(float(r._mapping["fai_value"]), 4),
                    lon=round(float(r._mapping["lon"]), 6),
                    lat=round(float(r._mapping["lat"]), 6),
                    terrain_roughness=round(float(r._mapping["terrain_roughness"]), 4),
                    building_density=round(float(r._mapping["building_density"]), 4),
                )
                for r in rows
            ]
    except Exception as exc:
        logger.warning("FAI DB unavailable, using fallback: %s", exc)
        from src.api.fallback import generate_demo_fai

        fai_data = generate_demo_fai(height)
        return [FAIDataResponse(**f) for f in fai_data]
