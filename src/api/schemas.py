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
    """風廊查詢回應 (matches frontend Corridor interface)。"""

    corridor_id: str
    name: str
    type: str  # 'primary' | 'secondary'
    geometry: dict  # GeoJSON LineString
    mean_wind_speed: float
    dominant_direction: str
    risk_level: str


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


class BatchPointQuery(BaseModel):
    """批次風險查詢請求。"""

    points: list[PointQuery] = Field(..., min_length=1, max_length=100, description="批次查詢點位（最多 100 個）")


class BatchRiskResponse(BaseModel):
    """批次風險查詢回應。"""

    results: list[RiskResponse]
    total: int
    flyable_count: int = 0
    not_flyable_count: int = 0


class HealthResponse(BaseModel):
    """健康檢查回應。"""

    status: str = "ok"
    version: str = "0.1.0"
    city: str = "taipei"


# ─── Dashboard models ─────────────────────────────────────────


class DashboardStats(BaseModel):
    """Dashboard 統計摘要。"""

    total_grids: int = 0
    risk_distribution: dict = Field(
        default_factory=lambda: {"green": 0, "yellow": 0, "red": 0, "black": 0},
    )
    corridor_count: int = 0
    mean_wind_speed: float = 0.0
    monitoring_area_km2: float = 0.0
    last_updated: str = ""


class GridCellResponse(BaseModel):
    """地圖用網格資料。"""

    grid_id: str
    lon: float
    lat: float
    risk_level: str
    risk_score: float
    wind_speed: float
    wind_direction: str = "NE"
    is_corridor: bool = False
    turbulence: float | None = None
    gust_factor: float | None = None
    shelter_index: float | None = None


class WindRoseSectorResponse(BaseModel):
    """風花圖扇區資料。"""

    direction: str
    angle: float
    frequency: float
    mean_speed: float


class FAIDataResponse(BaseModel):
    """FAI 指標資料。"""

    grid_id: str
    fai_value: float
    lon: float
    lat: float
    terrain_roughness: float
    building_density: float
