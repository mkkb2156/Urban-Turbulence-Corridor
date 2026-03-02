"""FastAPI 應用程式入口。"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import corridor, risk, wind
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

app.include_router(wind.router, prefix="/api/v1", tags=["wind"])
app.include_router(corridor.router, prefix="/api/v1", tags=["corridors"])
app.include_router(risk.router, prefix="/api/v1", tags=["risk"])


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康檢查。"""
    return HealthResponse()
