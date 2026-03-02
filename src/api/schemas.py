"""Pydantic request/response models。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PointQuery(BaseModel):
    """單點查詢請求。"""

    lon: float = Field(..., ge=119, le=123, description="經度 (WGS84)")
    lat: float = Field(..., ge=21, le=26, description="緯度 (WGS84)")
    height: float = Field(50.0, ge=0, le=500, description="飛行高度 (m)")
    drone_id: str | None = Field(None, description="無人機型號 ID")


class BboxQuery(BaseModel):
    """範圍查詢請求。"""

    minx: float = Field(..., description="最小經度")
    miny: float = Field(..., description="最小緯度")
    maxx: float = Field(..., description="最大經度")
    maxy: float = Field(..., description="最大緯度")


class WindResponse(BaseModel):
    """風速查詢回應。"""

    grid_id: str
    wind_speed: float = Field(..., description="估算風速 (m/s)")
    wind_direction: str = Field("NE", description="主要風向")
    risk_level: str
    risk_label: str
    risk_score: float


class CorridorResponse(BaseModel):
    """風廊查詢回應。"""

    corridor_id: str
    corridor_class: str
    total_cost: float
    estimated_width: float | None = None
    geometry_geojson: dict


class RiskResponse(BaseModel):
    """風險查詢回應。"""

    grid_id: str
    risk_level: str
    risk_label: str
    risk_score: float
    wind_speed_50m: float | None = None
    wind_speed_80m: float | None = None
    wind_speed_120m: float | None = None
    fai_ne: float | None = None
    is_corridor: bool = False
    flyability: dict | None = None


class HealthResponse(BaseModel):
    """健康檢查回應。"""

    status: str = "ok"
    version: str = "0.1.0"
    city: str = "taipei"
