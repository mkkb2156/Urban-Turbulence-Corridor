"""FastAPI 應用程式入口。"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routes import corridor, dashboard, risk, tests, wind
from src.api.schemas import HealthResponse

app = FastAPI(
    title="UTC — Urban Turbulence Corridor API",
    description="台灣城市風廊圖層系統 API，供無人機低空作業風險評估使用",
    version="0.1.0",
)

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


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康檢查。"""
    return HealthResponse()


# Serve frontend static files (production build)
WEB_DIST = Path(__file__).resolve().parent.parent.parent / "web" / "dist"
if WEB_DIST.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIST), html=True), name="frontend")
