"""系統監控 API — 檢查所有外部服務連線狀態。"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import requests as http_requests
from fastapi import APIRouter
from sqlalchemy import text

from config.settings import CWA_API_KEY

logger = logging.getLogger(__name__)
router = APIRouter()

_VERSION = "0.1.0"


from schemas import MonitorResponse, ServiceStatus


def _check_database() -> ServiceStatus:
    """檢查 PostGIS 資料庫連線與資料量。"""
    start = time.perf_counter()
    try:
        from db.session import get_engine

        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            grid_count = conn.execute(text("SELECT COUNT(*) FROM grid_cells")).scalar() or 0
            corridor_count = conn.execute(text("SELECT COUNT(*) FROM wind_corridors")).scalar() or 0

        latency = (time.perf_counter() - start) * 1000
        logger.info("Monitor: DB check OK (%.0fms)", latency)
        return ServiceStatus(
            name="PostGIS Database",
            status="up",
            latency_ms=round(latency, 1),
            details={"grid_cells": grid_count, "wind_corridors": corridor_count},
        )
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        logger.warning("Monitor: DB check failed: %s", exc)
        return ServiceStatus(
            name="PostGIS Database",
            status="down",
            latency_ms=round(latency, 1),
            error=str(exc)[:200],
        )


def _check_open_meteo() -> ServiceStatus:
    """檢查 Open-Meteo API 可達性。"""
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=25.03&longitude=121.56"
        "&hourly=wind_speed_10m&forecast_days=1"
    )
    start = time.perf_counter()
    try:
        resp = http_requests.get(url, timeout=5)
        resp.raise_for_status()
        latency = (time.perf_counter() - start) * 1000
        logger.info("Monitor: Open-Meteo check OK (%.0fms)", latency)
        return ServiceStatus(
            name="Open-Meteo API",
            status="up",
            latency_ms=round(latency, 1),
            details={"endpoint": "forecast", "http_status": resp.status_code},
        )
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        logger.warning("Monitor: Open-Meteo check failed: %s", exc)
        return ServiceStatus(
            name="Open-Meteo API",
            status="down",
            latency_ms=round(latency, 1),
            error=str(exc)[:200],
        )


def _check_cwa() -> ServiceStatus:
    """檢查中央氣象署 API 可達性。"""
    if not CWA_API_KEY:
        return ServiceStatus(
            name="CWA Weather API",
            status="down",
            latency_ms=0,
            error="CWA_API_KEY not configured",
        )

    url = (
        "https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0001-001"
        f"?Authorization={CWA_API_KEY}&limit=1"
    )
    start = time.perf_counter()
    try:
        resp = http_requests.get(url, timeout=5)
        resp.raise_for_status()
        latency = (time.perf_counter() - start) * 1000
        logger.info("Monitor: CWA check OK (%.0fms)", latency)
        return ServiceStatus(
            name="CWA Weather API",
            status="up",
            latency_ms=round(latency, 1),
            details={"http_status": resp.status_code},
        )
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        logger.warning("Monitor: CWA check failed: %s", exc)
        return ServiceStatus(
            name="CWA Weather API",
            status="down",
            latency_ms=round(latency, 1),
            error=str(exc)[:200],
        )


@router.get("/monitor", response_model=MonitorResponse)
async def get_monitor_status():
    """檢查所有外部服務狀態並回傳監控報告。"""
    # 使用 ThreadPoolExecutor 並行檢查（同步 requests 在線程中執行）
    checks = [_check_database, _check_open_meteo, _check_cwa]
    service_list: list[ServiceStatus] = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(fn): fn for fn in checks}
        for future in as_completed(futures):
            service_list.append(future.result())

    up_count = sum(1 for s in service_list if s.status == "up")
    total = len(service_list)

    if up_count == total:
        overall = "healthy"
    elif up_count == 0:
        overall = "unhealthy"
    else:
        overall = "degraded"

    return MonitorResponse(
        status=overall,
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=_VERSION,
        services=service_list,
    )
