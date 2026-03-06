"""風廊查詢 API。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query

from src.api.schemas import CorridorResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/corridors", response_model=list[CorridorResponse])
async def query_corridors(
    city: str = Query("taipei", description="城市名稱"),
):
    """查詢某城市的風廊資料，回傳符合前端 Corridor 介面的格式。"""
    from src.db.queries import query_corridors_by_city

    try:
        gdf = query_corridors_by_city(city)
    except Exception as exc:
        logger.warning("Failed to query corridors: %s", exc)
        gdf = None

    if gdf is None or gdf.empty:
        from src.api.fallback import generate_demo_corridors

        return [CorridorResponse(**c) for c in generate_demo_corridors()]

    results = []
    for idx, row in gdf.iterrows():
        corridor_id = str(row.get("corridor_id", f"corridor-{idx}"))
        corridor_class = row.get("corridor_class", "secondary")

        # Map corridor_class to frontend type ('primary' | 'secondary')
        corridor_type = "primary" if corridor_class == "primary" else "secondary"

        # Build a human-readable name
        name = row.get("name", f"Wind Corridor {corridor_id}")

        # Convert geometry to GeoJSON dict
        geom_geojson = row.geometry.__geo_interface__

        # Extract wind direction from DB or default to NE (Taipei dominant)
        dominant_direction = row.get("wind_direction", "NE") or "NE"

        # Estimate mean wind speed from total_cost (lower cost = stronger wind corridor)
        # or use a stored value if available
        mean_wind_speed = row.get("mean_wind_speed", None)
        if mean_wind_speed is None:
            total_cost = row.get("total_cost", 0) or 0
            # Rough heuristic: corridors with lower cost have higher wind speed
            # Scale inversely: cost 0 -> ~8 m/s, cost 100+ -> ~2 m/s
            mean_wind_speed = round(max(2.0, 8.0 - total_cost * 0.05), 2)

        # Determine risk level based on wind speed
        risk_level = row.get("risk_level", None)
        if risk_level is None:
            if mean_wind_speed < 4:
                risk_level = "green"
            elif mean_wind_speed < 8:
                risk_level = "yellow"
            elif mean_wind_speed < 12:
                risk_level = "red"
            else:
                risk_level = "black"

        results.append(CorridorResponse(
            corridor_id=corridor_id,
            name=name,
            type=corridor_type,
            geometry=geom_geojson,
            mean_wind_speed=mean_wind_speed,
            dominant_direction=dominant_direction,
            risk_level=risk_level,
        ))

    return results
