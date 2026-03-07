"""風險等級查詢 API。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query as QueryParam

from src.api.schemas import BatchPointQuery, BatchRiskResponse, PointQuery, RiskResponse

router = APIRouter()


def _do_risk_query(
    lon: float,
    lat: float,
    height: float,
    drone_id: str | None,
) -> RiskResponse:
    """Shared logic for POST and GET risk endpoints."""
    result = None
    try:
        from src.db.queries import query_grid_by_point

        result = query_grid_by_point(lon, lat)
    except Exception:
        pass  # DB unavailable, will use fallback

    if result is None:
        from src.api.fallback import generate_wind_at_point

        result = generate_wind_at_point(lon, lat, height)

    # 可飛性檢查
    flyability = None
    if drone_id:
        from src.risk.drone_specs import check_flyability

        height_col = f"wind_{int(height)}m"
        wind_speed = result.get(height_col, result.get("wind_50m", 0)) or 0
        try:
            flyability = check_flyability(wind_speed, drone_id)
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


@router.get("/risk", response_model=RiskResponse)
async def query_risk_get(
    lon: float = QueryParam(..., ge=119, le=123, description="經度 (WGS84)"),
    lat: float = QueryParam(..., ge=21, le=26, description="緯度 (WGS84)"),
    height: float = QueryParam(50.0, ge=0, le=500, description="飛行高度 (m)"),
    drone_id: str | None = QueryParam(None, description="無人機型號 ID"),
):
    """查詢指定座標的風險等級 (GET)。"""
    return _do_risk_query(lon, lat, height, drone_id)


@router.post("/risk", response_model=RiskResponse)
async def query_risk(query: PointQuery):
    """查詢指定座標的風險等級。

    返回風速、風險等級、各高度風速、FAI 等綜合資訊。
    若提供無人機型號，額外返回可飛性評估。
    """
    return _do_risk_query(query.lon, query.lat, query.height, query.drone_id)


@router.post("/risk/batch", response_model=BatchRiskResponse)
async def query_risk_batch(query: BatchPointQuery):
    """批次查詢多個座標的風險等級。

    接受最多 100 個點位，回傳所有結果及統計摘要。
    """
    results = []
    flyable = 0
    not_flyable = 0

    for pt in query.points:
        r = _do_risk_query(pt.lon, pt.lat, pt.height, pt.drone_id)
        results.append(r)
        if r.flyability:
            if r.flyability.get("flyable"):
                flyable += 1
            else:
                not_flyable += 1

    return BatchRiskResponse(
        results=results,
        total=len(results),
        flyable_count=flyable,
        not_flyable_count=not_flyable,
    )
