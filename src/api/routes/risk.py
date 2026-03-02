"""風險等級查詢 API。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.api.schemas import PointQuery, RiskResponse

router = APIRouter()


@router.post("/risk", response_model=RiskResponse)
async def query_risk(query: PointQuery):
    """查詢指定座標的風險等級。

    返回風速、風險等級、各高度風速、FAI 等綜合資訊。
    若提供無人機型號，額外返回可飛性評估。
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

    # 可飛性檢查
    flyability = None
    if query.drone_id:
        from src.risk.drone_specs import check_flyability

        height_col = f"wind_{int(query.height)}m"
        wind_speed = result.get(height_col, result.get("wind_50m", 0)) or 0
        try:
            flyability = check_flyability(wind_speed, query.drone_id)
        except ValueError:
            pass

    return RiskResponse(
        grid_id=result["grid_id"],
        risk_level=result.get("risk_level", "unknown"),
        risk_label=result.get("risk_level", "unknown"),
        risk_score=result.get("risk_score", 0),
        wind_speed_50m=result.get("wind_50m"),
        wind_speed_80m=result.get("wind_80m"),
        wind_speed_120m=result.get("wind_120m"),
        fai_ne=result.get("fai_ne"),
        is_corridor=result.get("is_corridor", False),
        flyability=flyability,
    )
