"""UTC v4 — FastAPI 應用程式入口。"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from auth import APIKeyMiddleware
from errors import UTCError, utc_error_handler
from logging_config import RequestLoggingMiddleware, setup_logging
from rate_limit import RateLimitMiddleware
from routes import (
    area,
    corridor,
    dashboard,
    derived,
    drone_power,
    flight_summary,
    forecast,
    monitor,
    report,
    risk,
    route,
    tests,
    wind,
    wind_regional,
    wind_texture,
)
from schemas import HealthResponse

# 初始化日誌
setup_logging()

app = FastAPI(
    title="UTC v4 — Urban Turbulence Corridor API",
    description=(
        "台灣城市風廊圖層系統 API v4，供無人機低空作業風險評估使用。\n\n"
        "## 認證\n"
        "使用 `X-API-Key` header 或 `?api_key=` query parameter 認證。\n"
        "當 `API_KEY_REQUIRED=false` 時不需認證（開發模式）。\n\n"
        "## 限流\n"
        "每個 API Key 有獨立限流配額（預設 60 次/分鐘）。\n"
        "超過限流會收到 429 Too Many Requests。"
    ),
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── 統一錯誤處理 ─────────────────────────────────────────────────
app.add_exception_handler(UTCError, utc_error_handler)

# ── Middleware（註冊順序：外 → 內，執行順序：內 → 外）──────────────
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(APIKeyMiddleware)

# ── 繼承 v3 API Routes ──────────────────────────────────────────
app.include_router(dashboard.router, prefix="/api/v1", tags=["Dashboard"])
app.include_router(wind.router, prefix="/api/v1", tags=["Wind"])
app.include_router(wind_regional.router, prefix="/api/v1", tags=["Wind"])
app.include_router(risk.router, prefix="/api/v1", tags=["Risk"])
app.include_router(corridor.router, prefix="/api/v1", tags=["Corridors"])
app.include_router(forecast.router, prefix="/api/v1", tags=["Forecast"])
app.include_router(derived.router, prefix="/api/v1", tags=["Derived Data"])
app.include_router(area.router, prefix="/api/v1", tags=["Analysis"])
app.include_router(route.router, prefix="/api/v1", tags=["Route"])
app.include_router(report.router, prefix="/api/v1", tags=["Report"])
app.include_router(drone_power.router, prefix="/api/v1", tags=["Drone Power"])
app.include_router(monitor.router, prefix="/api/v1", tags=["System"])
app.include_router(tests.router, prefix="/api/v1", tags=["System"])

# ── v4 新增 Routes ──────────────────────────────────────────────
app.include_router(wind_texture.router, prefix="/api/v1", tags=["Wind"])
app.include_router(flight_summary.router, prefix="/api/v1", tags=["Flight"])


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """健康檢查 — 不需要 API Key。"""
    return HealthResponse()


# Serve frontend static files (production build)
WEB_DIST = Path(__file__).resolve().parent.parent.parent / "apps" / "web" / "dist"
if WEB_DIST.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIST), html=True), name="frontend")
