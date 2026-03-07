"""FastAPI 應用程式入口。"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.logging_config import RequestLoggingMiddleware, setup_logging
from src.api.routes import area, corridor, dashboard, forecast, monitor, report, risk, route, tests, wind
from src.api.schemas import HealthResponse

# 初始化日誌
setup_logging()

app = FastAPI(
    title="UTC — Urban Turbulence Corridor API",
    description="台灣城市風廊圖層系統 API，供無人機低空作業風險評估使用",
    version="0.1.0",
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(wind.router, prefix="/api/v1", tags=["wind"])
app.include_router(corridor.router, prefix="/api/v1", tags=["corridors"])
app.include_router(risk.router, prefix="/api/v1", tags=["risk"])
app.include_router(tests.router, prefix="/api/v1", tags=["tests"])
app.include_router(dashboard.router, prefix="/api/v1", tags=["dashboard"])
app.include_router(forecast.router, prefix="/api/v1", tags=["forecast"])
app.include_router(area.router, prefix="/api/v1", tags=["area"])
app.include_router(route.router, prefix="/api/v1", tags=["route"])
app.include_router(report.router, prefix="/api/v1", tags=["report"])
app.include_router(monitor.router, prefix="/api/v1", tags=["monitor"])


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康檢查。"""
    return HealthResponse()


# Serve frontend static files (production build)
WEB_DIST = Path(__file__).resolve().parent.parent.parent / "web" / "dist"
if WEB_DIST.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIST), html=True), name="frontend")
