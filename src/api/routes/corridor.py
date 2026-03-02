"""風廊查詢 API。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.api.schemas import CorridorResponse

router = APIRouter()


@router.get("/corridors", response_model=list[CorridorResponse])
async def query_corridors(
    city: str = Query("taipei", description="城市名稱"),
):
    """查詢某城市的風廊多邊形。"""
    from src.db.queries import query_corridors_by_city

    try:
        gdf = query_corridors_by_city(city)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    results = []
    for _, row in gdf.iterrows():
        results.append(CorridorResponse(
            corridor_id=row["corridor_id"],
            corridor_class=row.get("corridor_class", "secondary"),
            total_cost=row.get("total_cost", 0),
            estimated_width=row.get("estimated_width"),
            geometry_geojson=row.geometry.__geo_interface__,
        ))

    return results
