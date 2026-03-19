"""風速查詢 API。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from schemas import PointQuery, WindResponse

router = APIRouter()


def _do_wind_query(lon: float, lat: float, height: float, model: str = "log_profile") -> WindResponse:
    """Shared logic for POST and GET wind endpoints."""
    result = None
    try:
        from db.queries import query_grid_by_point

        result = query_grid_by_point(lon, lat)
    except Exception:
        pass  # DB unavailable, will use fallback

    if result is None:
        from fallback import generate_wind_at_point

        result = generate_wind_at_point(lon, lat, height)

    height_col = f"wind_{int(height)}m"
    wind_speed = result.get(height_col, result.get("wind_50m", 0))

    # Röckle 模型：考慮建築繞流效應
    if model == "rockle" and wind_speed:
        try:
            wind_speed = _rockle_adjusted_speed(lon, lat, height, wind_speed, result)
        except Exception:
            pass  # fallback to log profile result

    return WindResponse(
        grid_id=result["grid_id"],
        wind_speed=wind_speed or 0,
        risk_level=result.get("risk_level", "unknown"),
        risk_label=result.get("risk_level", "unknown"),
        risk_score=result.get("risk_score", 0),
    )


def _rockle_adjusted_speed(
    lon: float, lat: float, height: float,
    base_speed: float, grid_result: dict,
) -> float:
    """使用 Röckle 模型調整風速。"""
    from pyproj import Transformer

    from core.wind.rockle import buildings_from_grid, rockle_wind_at_point

    # WGS84 → TWD97
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3826", always_xy=True)
    x, y = transformer.transform(lon, lat)

    # 從 grid 資料推算附近建築
    mean_h = grid_result.get("mean_height") or grid_result.get("max_height")
    bcr = grid_result.get("bcr", 0)
    if not mean_h or mean_h < 3 or bcr < 0.05:
        return base_speed

    # 建立簡化建築
    buildings = [{
        "cx": x, "cy": y,
        "width": 30, "depth": 30,
        "height": mean_h,
    }]

    result = rockle_wind_at_point(
        x, y, buildings,
        reference_wind_speed=base_speed,
        reference_wind_direction=45.0,
        target_height=height,
    )

    return result["speed"]


@router.get("/wind", response_model=WindResponse)
async def query_wind_get(
    lon: float = Query(..., ge=119, le=123, description="經度 (WGS84)"),
    lat: float = Query(..., ge=21, le=26, description="緯度 (WGS84)"),
    height: float = Query(50.0, ge=0, le=500, description="飛行高度 (m)"),
    model: str = Query("log_profile", description="風場模型: log_profile | rockle"),
):
    """查詢指定座標的估算風速 (GET)。"""
    return _do_wind_query(lon, lat, height, model)


@router.post("/wind", response_model=WindResponse)
async def query_wind(query: PointQuery):
    """查詢指定座標的估算風速。

    透過經緯度定位所在網格，返回該網格的風速與風險資訊。
    """
    return _do_wind_query(query.lon, query.lat, query.height)
