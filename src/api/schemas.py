"""Pydantic request/response models — 所有 API 端點的型別定義。"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ─── Shared / Common ───────────────────────────────────────────


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


# ─── Health ────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    """健康檢查回應。"""

    status: str = "ok"
    version: str = "0.1.0"
    city: str = "taipei"


# ─── Wind ──────────────────────────────────────────────────────


class WindResponse(BaseModel):
    """風速查詢回應。"""

    grid_id: str
    wind_speed: float = Field(..., description="估算風速 (m/s)")
    wind_direction: str = Field("NE", description="主要風向")
    risk_level: str
    risk_label: str
    risk_score: float


# ─── Corridor ──────────────────────────────────────────────────


class CorridorResponse(BaseModel):
    """風廊查詢回應。"""

    corridor_id: str
    name: str
    type: str  # 'primary' | 'secondary'
    geometry: dict  # GeoJSON LineString
    mean_wind_speed: float
    dominant_direction: str
    risk_level: str


# ─── Risk ──────────────────────────────────────────────────────


class DroneFlyability(BaseModel):
    """無人機可飛性評估。"""

    drone_id: str
    drone_name: str
    max_wind_speed: float
    flyable: bool
    margin: float
    recommendation: str


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

    points: list[PointQuery] = Field(
        ..., min_length=1, max_length=100,
        description="批次查詢點位（最多 100 個）",
    )


class BatchRiskResponse(BaseModel):
    """批次風險查詢回應。"""

    results: list[RiskResponse]
    total: int
    flyable_count: int = 0
    not_flyable_count: int = 0


# ─── Dashboard ─────────────────────────────────────────────────


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


# ─── Forecast ──────────────────────────────────────────────────


class ForecastPoint(BaseModel):
    """逐時預報資料點。"""

    time: str
    wind_speed: float
    wind_direction: float
    wind_gusts: float | None = None
    risk_level: str
    wind_speed_80m: float | None = None
    wind_direction_80m: float | None = None
    wind_speed_120m: float | None = None
    wind_direction_120m: float | None = None


class ForecastResponse(BaseModel):
    """風場預報回應。"""

    city: str = ""
    lon: float | None = None
    lat: float | None = None
    height: float | None = None
    hours: int
    source: str  # 'open-meteo' | 'mock'
    generated_at: str
    forecasts: list[ForecastPoint]


class CWAStation(BaseModel):
    """CWA 測站觀測。"""

    station_id: str
    station_name: str
    lat: float
    lon: float
    wind_speed: float
    wind_direction: float | None = None
    gust_speed: float | None = None
    observation_time: str | None = None
    risk_level: str


class CWAStationsResponse(BaseModel):
    """CWA 測站列表回應。"""

    region: str
    source: str
    station_count: int
    stations: list[CWAStation]
    error: str | None = None
    fetched_at: str


# ─── Area Analysis ─────────────────────────────────────────────


class AreaPredictRequest(BaseModel):
    """多邊形區域預測請求。"""

    polygon: list[list[float]] = Field(..., description="多邊形頂點 [[lon,lat], ...]")
    height: float = Field(50.0, ge=0, le=500, description="飛行高度 (m)")
    drone_id: str | None = Field(None, description="無人機型號")
    start_time: str | None = Field(None, description="起始時間 (ISO)")
    end_time: str | None = Field(None, description="結束時間 (ISO)")


class AreaWindStats(BaseModel):
    """區域風速統計。"""

    mean_speed: float
    max_speed: float
    min_speed: float
    std_speed: float


class AreaFlyability(BaseModel):
    """區域可飛性評估。"""

    drone_id: str
    max_wind_in_area: float
    tolerance: float
    safe_percentage: float
    flyable: bool


class AreaGridCell(BaseModel):
    """區域分析中的網格資料。"""

    lon: float
    lat: float
    wind_speed: float
    wind_direction: float
    risk_level: str


class AreaPredictResponse(BaseModel):
    """區域預測回應。"""

    center: dict  # {"lon": float, "lat": float}
    area_km2: float
    grid_count: int
    height: float
    wind_stats: AreaWindStats
    risk_distribution: dict
    wind_rose: list[WindRoseSectorResponse]
    flyability: AreaFlyability | None = None
    grid_cells: list[AreaGridCell]
    generated_at: str


# ─── Route Analysis ────────────────────────────────────────────


class RouteAnalyzeRequest(BaseModel):
    """路線風況分析請求。"""

    waypoints: list[list[float]] = Field(..., description="路徑點 [[lon,lat], ...]")
    height: float = Field(50.0, ge=0, le=500)
    drone_id: str | None = None
    time: str | None = None


class RouteSamplePoint(BaseModel):
    """路線取樣點。"""

    lon: float
    lat: float
    wind_speed: float
    wind_direction: float
    risk_level: str


class RouteSegment(BaseModel):
    """路線分析段落。"""

    from_point: list[float] = Field(alias="from")
    to_point: list[float] = Field(alias="to")
    distance_m: float
    bearing: float
    avg_wind_speed: float
    avg_wind_direction: float
    headwind: float
    crosswind: float
    wind_effect_pct: float
    risk_level: str
    travel_time_s: float
    sample_points: list[RouteSamplePoint]

    model_config = {"populate_by_name": True}


class RouteFlyability(BaseModel):
    """路線可飛性評估。"""

    drone_id: str
    max_wind_on_route: float
    tolerance: float
    flyable: bool
    danger_segments: int


class RouteAnalyzeResponse(BaseModel):
    """路線分析回應。"""

    waypoints: list[list[float]]
    height: float
    total_distance_m: float
    total_time_s: float
    max_risk: str
    avg_wind_speed: float
    segments: list[dict]  # Keep as dict for backward compatibility
    flyability: dict | None = None
    generated_at: str


# ─── Route Planning ────────────────────────────────────────────


class RoutePlanRequest(BaseModel):
    """最優路線規劃請求。"""

    start: list[float] = Field(..., description="起點 [lon, lat]")
    end: list[float] = Field(..., description="終點 [lon, lat]")
    height: float = Field(50.0, ge=0, le=500)
    drone_id: str | None = None
    mode: str = Field("balanced", description="safest|shortest|balanced")


class PlannedRoute(BaseModel):
    """規劃路線。"""

    mode: str
    waypoints: list[list[float]]
    geometry: dict  # GeoJSON LineString
    total_distance_m: float
    total_time_s: float
    max_risk: str
    avg_risk_score: float
    segments: list[dict]
    flyable: bool | None = None


class RoutePlanResponse(BaseModel):
    """路線規劃回應。"""

    start: list[float]
    end: list[float]
    height: float
    routes: list[PlannedRoute]
    recommended: str
    flyability: dict | None = None
    generated_at: str


# ─── Monitor ───────────────────────────────────────────────────


class ServiceStatus(BaseModel):
    """服務狀態。"""

    name: str
    status: str  # "up" | "down"
    latency_ms: float
    details: dict = {}
    error: str | None = None


class MonitorResponse(BaseModel):
    """系統監控回應。"""

    status: str  # "healthy" | "degraded" | "unhealthy"
    timestamp: str
    version: str
    services: list[ServiceStatus]


# ─── Report ────────────────────────────────────────────────────


class ReportRequest(BaseModel):
    """報告生成請求。"""

    report_type: str = Field(..., description="area|route|plan")
    title: str = Field("飛行任務報告", description="報告標題")
    drone_id: str | None = None
    height: float = Field(50.0)
    data: dict = Field(default_factory=dict, description="分析結果數據")
    format: str = Field("json", description="json|pdf")


# ─── Derived Data ──────────────────────────────────────────────


class DerivedTurbulence(BaseModel):
    """湍流指標。"""

    ti_50m: float | None = None
    ti_80m: float | None = None
    ti_120m: float | None = None
    assessment: str = ""


class DerivedWindShear(BaseModel):
    """風切變指標。"""

    shear_50_80: float | None = None
    shear_80_120: float | None = None
    assessment: str = ""


class DerivedGust(BaseModel):
    """陣風指標。"""

    gust_factor: float | None = None
    gust_speed_50m: float | None = None
    gust_speed_80m: float | None = None
    gust_speed_120m: float | None = None


class DerivedShelter(BaseModel):
    """遮蔽指標。"""

    shelter_index: float | None = None
    assessment: str = ""


class DerivedAltitude(BaseModel):
    """高度限制。"""

    min_safe_alt: float | None = None
    max_legal_alt: float | None = None
    flyable_range_m: float | None = None


class DerivedDataResponse(BaseModel):
    """衍生數據回應。"""

    grid_id: str
    lon: float
    lat: float
    morphology: dict
    wind: dict
    derived: dict
    risk: dict
    generated_at: str


# ─── Flight Windows ────────────────────────────────────────────


class FlightWindow(BaseModel):
    """適飛時段。"""

    start: str
    end: str
    hours: float
    avg_wind: float
    max_wind: float
    min_wind: float


class FlightWindowsResponse(BaseModel):
    """適飛時段回應。"""

    lon: float
    lat: float
    drone_id: str
    max_wind_tolerance: float
    safe_wind_threshold: float
    source: str
    total_hours: int
    flyable_hours: int
    flyable_pct: float
    windows: list[FlightWindow]
    generated_at: str
