"""風速查詢 API。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.api.schemas import PointQuery, WindResponse

router = APIRouter()


@router.post("/wind", response_model=WindResponse)
async def query_wind(query: PointQuery):
    """查詢指定座標的估算風速。

    透過經緯度定位所在網格，返回該網格的風速與風險資訊。
    """
    from src.db.queries import query_grid_by_point

    try:
        result = query_grid_by_point(query.lon, query.lat)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="No grid data found for this location",
        )

    height_col = f"wind_{int(query.height)}m"
    wind_speed = result.get(height_col, result.get("wind_50m", 0))

    return WindResponse(
        grid_id=result["grid_id"],
        wind_speed=wind_speed or 0,
        risk_level=result.get("risk_level", "unknown"),
        risk_label=result.get("risk_level", "unknown"),
        risk_score=result.get("risk_score", 0),
    )
