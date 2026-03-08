"""集中式日誌配置 — 統一格式、等級、request middleware + 使用量追蹤。"""

from __future__ import annotations

import logging
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

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


# ── 使用量追蹤 (in-memory, 生產環境可切 DB/Redis) ────────────────


class UsageTracker:
    """API 使用量追蹤器 — 記錄每個 API Key 的請求次數與延遲。"""

    def __init__(self):
        # key_id → { endpoint → { count, total_ms, last_used } }
        self._usage: dict[str, dict[str, dict]] = defaultdict(
            lambda: defaultdict(lambda: {"count": 0, "total_ms": 0.0, "last_used": ""})
        )

    def record(self, key_id: str, endpoint: str, method: str, status: int, duration_ms: float):
        """記錄一次 API 呼叫。"""
        path_key = f"{method} {endpoint}"
        entry = self._usage[key_id][path_key]
        entry["count"] += 1
        entry["total_ms"] += duration_ms
        entry["last_used"] = datetime.now(timezone.utc).isoformat()
        entry["last_status"] = status

    def get_stats(self, key_id: str | None = None) -> dict:
        """取得使用量統計。"""
        if key_id:
            return dict(self._usage.get(key_id, {}))
        # 全域統計
        result = {}
        for kid, endpoints in self._usage.items():
            total_requests = sum(e["count"] for e in endpoints.values())
            result[kid] = {
                "total_requests": total_requests,
                "endpoints": len(endpoints),
                "last_used": max(
                    (e["last_used"] for e in endpoints.values()),
                    default="",
                ),
            }
        return result


# 全域 tracker 實例
usage_tracker = UsageTracker()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """記錄每個 HTTP request 的 method、path、status、耗時 + 使用量追蹤。"""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        path = request.url.path

        # 跳過健康檢查的頻繁日誌
        if path == "/health":
            return response

        logger.info(
            "%s %s → %d (%.0fms)",
            request.method,
            path,
            response.status_code,
            duration_ms,
        )

        # 使用量追蹤（只追蹤 API 路徑）
        if path.startswith("/api/"):
            key_info = getattr(request.state, "api_key_info", None)
            key_id = key_info.key_id if key_info else "anonymous"
            usage_tracker.record(
                key_id=key_id,
                endpoint=path,
                method=request.method,
                status=response.status_code,
                duration_ms=duration_ms,
            )

        return response
