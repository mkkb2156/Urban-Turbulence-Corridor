"""風速查詢 API。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.api.schemas import PointQuery, WindResponse

router = APIRouter()


def _do_wind_query(lon: float, lat: float, height: float) -> WindResponse:
    """Shared logic for POST and GET wind endpoints."""
    result = None
    try:
        from src.db.queries import query_grid_by_point

        result = query_grid_by_point(lon, lat)
    except Exception:
        pass  # DB unavailable, will use fallback

    if result is None:
        from src.api.fallback import generate_wind_at_point

        result = generate_wind_at_point(lon, lat, height)

    height_col = f"wind_{int(height)}m"
    wind_speed = result.get(height_col, result.get("wind_50m", 0))

    return WindResponse(
        grid_id=result["grid_id"],
        wind_speed=wind_speed or 0,
        risk_level=result.get("risk_level", "unknown"),
        risk_label=result.get("risk_level", "unknown"),
        risk_score=result.get("risk_score", 0),
    )


@router.get("/wind", response_model=WindResponse)
async def query_wind_get(
    lon: float = Query(..., ge=119, le=123, description="經度 (WGS84)"),
    lat: float = Query(..., ge=21, le=26, description="緯度 (WGS84)"),
    height: float = Query(50.0, ge=0, le=500, description="飛行高度 (m)"),
):
    """查詢指定座標的估算風速 (GET)。"""
    return _do_wind_query(lon, lat, height)


@router.post("/wind", response_model=WindResponse)
async def query_wind(query: PointQuery):
    """查詢指定座標的估算風速。

    透過經緯度定位所在網格，返回該網格的風速與風險資訊。
    """
    return _do_wind_query(query.lon, query.lat, query.height)
