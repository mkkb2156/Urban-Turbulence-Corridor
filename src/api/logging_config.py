"""集中式日誌配置 — 統一格式、等級、request middleware。"""

from __future__ import annotations

import logging
import sys
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from config.settings import LOG_LEVEL

logger = logging.getLogger("utc.api")


def setup_logging() -> None:
    """初始化全域日誌配置，使用 LOG_LEVEL 環境變數。"""
    fmt = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format=fmt,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
    # 降低第三方庫噪音
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """記錄每個 HTTP request 的 method、path、status、耗時。"""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        # 跳過健康檢查的頻繁日誌
        path = request.url.path
        if path == "/health":
            return response

        logger.info(
            "%s %s → %d (%.0fms)",
            request.method,
            path,
            response.status_code,
            duration_ms,
        )
        return response
