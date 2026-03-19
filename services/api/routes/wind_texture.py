"""v4 新增 — 風場 PNG Texture 端點。

GET /api/v1/wind-texture
回傳 U/V 風場編碼為 PNG，供 WebGL GPU WindLayer 消費。
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Query, Response

from core.wind.texture_encoder import (
    compute_cache_key,
    encode_wind_texture,
    generate_wind_field_from_grids,
)
from fallback import FALLBACK_GRID_CELLS

logger = logging.getLogger(__name__)

router = APIRouter()

# 台北市預設 bbox
TAIPEI_BBOX = (121.45, 24.96, 121.67, 25.21)


@router.get("/wind-texture", tags=["Wind"])
async def get_wind_texture(
    bbox: str = Query(
        default="121.45,24.96,121.67,25.21",
        description="Bounding box: lng_min,lat_min,lng_max,lat_max",
    ),
    datetime_str: str = Query(
        default=None,
        alias="datetime",
        description="ISO 8601 日期時間（預設為當前時間）",
    ),
    altitude: float = Query(default=80.0, ge=10, le=500, description="高度 (m AGL)"),
    resolution: float = Query(default=100.0, ge=10, le=1000, description="解析度 (m/pixel)"),
):
    """回傳風場 PNG Texture。

    - R 通道 = U 風速分量
    - G 通道 = V 風速分量
    - 正規化範圍在 Response Header 中提供

    Headers:
    - X-Wind-Bounds: lng_min,lat_min,lng_max,lat_max
    - X-Wind-Min: -25.0
    - X-Wind-Max: 25.0
    """
    # 解析 bbox
    try:
        parts = [float(x.strip()) for x in bbox.split(",")]
        if len(parts) != 4:
            raise ValueError("bbox must have 4 values")
        bbox_tuple = (parts[0], parts[1], parts[2], parts[3])
    except (ValueError, IndexError):
        bbox_tuple = TAIPEI_BBOX

    # 解析時間
    if datetime_str is None:
        dt = datetime.now()
    else:
        try:
            dt = datetime.fromisoformat(datetime_str)
        except ValueError:
            dt = datetime.now()

    # 嘗試從 DB 取得網格資料，失敗則用 fallback
    grid_data: list[dict] = []
    try:
        from db.session import get_engine, table_exists

        engine = get_engine()
        if engine and table_exists(engine, "grid_cells"):
            from sqlalchemy import text

            with engine.connect() as conn:
                result = conn.execute(
                    text(
                        "SELECT lon, lat, z0, zd, wind_speed_80m "
                        "FROM grid_cells "
                        "WHERE lon BETWEEN :lng_min AND :lng_max "
                        "AND lat BETWEEN :lat_min AND :lat_max"
                    ),
                    {
                        "lng_min": bbox_tuple[0],
                        "lng_max": bbox_tuple[2],
                        "lat_min": bbox_tuple[1],
                        "lat_max": bbox_tuple[3],
                    },
                )
                grid_data = [dict(row._mapping) for row in result]
    except Exception as e:
        logger.warning("DB query failed, using fallback data: %s", e)

    if not grid_data:
        grid_data = [
            {
                "lon": cell.get("lon", 121.55),
                "lat": cell.get("lat", 25.03),
                "z0": 0.5,
                "zd": 5.0,
            }
            for cell in FALLBACK_GRID_CELLS[:50]
        ]

    # 生成風場
    u_field, v_field = generate_wind_field_from_grids(
        grid_data=grid_data,
        bbox=bbox_tuple,
        altitude=altitude,
        resolution=resolution,
    )

    # 編碼為 PNG
    result = encode_wind_texture(u_field, v_field, bounds=bbox_tuple)

    return Response(
        content=result.png_bytes,
        media_type="image/png",
        headers={
            "X-Wind-Bounds": f"{result.bounds[0]},{result.bounds[1]},{result.bounds[2]},{result.bounds[3]}",
            "X-Wind-Min": str(result.wind_min),
            "X-Wind-Max": str(result.wind_max),
            "X-Wind-Width": str(result.width),
            "X-Wind-Height": str(result.height),
            "Cache-Control": "public, max-age=300",
        },
    )
