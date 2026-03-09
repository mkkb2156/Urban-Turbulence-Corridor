"""Rate Limiting middleware — 滑動窗口限流。

使用 in-memory 計數器實作，生產環境可切換至 Redis。
每個 API Key 有獨立的限流配額。
"""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimiter:
    """In-memory sliding window rate limiter。"""

    def __init__(self):
        # key → list of request timestamps
        self._requests: dict[str, list[float]] = {}

    def check(self, key: str, limit_per_min: int) -> tuple[bool, int]:
        """檢查是否超過限流。

        Args:
            key: API Key ID
            limit_per_min: 每分鐘最大請求數

        Returns:
            (allowed, remaining): 是否放行 + 剩餘配額
        """
        now = time.time()
        window_start = now - 60.0

        # 清理過期記錄
        timestamps = self._requests.get(key, [])
        timestamps = [t for t in timestamps if t > window_start]

        remaining = max(0, limit_per_min - len(timestamps))

        if len(timestamps) >= limit_per_min:
            self._requests[key] = timestamps
            return False, 0

        timestamps.append(now)
        self._requests[key] = timestamps
        return True, remaining - 1

    def cleanup(self) -> None:
        """清理過期的計數器（可由定期任務呼叫）。"""
        now = time.time()
        window_start = now - 60.0
        expired_keys = []
        for key, timestamps in self._requests.items():
            fresh = [t for t in timestamps if t > window_start]
            if not fresh:
                expired_keys.append(key)
            else:
                self._requests[key] = fresh
        for key in expired_keys:
            del self._requests[key]


# 全域 limiter 實例
_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware — 使用 request.state.api_key_info 的限流配額。

    必須在 APIKeyMiddleware 之後註冊，因為依賴 api_key_info。
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # 只限流 API 路徑
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        # 取得 API Key info（由 APIKeyMiddleware 注入）
        key_info = getattr(request.state, "api_key_info", None)
        if key_info is None:
            return await call_next(request)

        # Admin key 不限流
        if key_info.is_admin:
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(key_info.rate_limit_per_min)
            response.headers["X-RateLimit-Remaining"] = "unlimited"
            return response

        allowed, remaining = _limiter.check(key_info.key_id, key_info.rate_limit_per_min)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit exceeded. Max {key_info.rate_limit_per_min} requests per minute.",
                        "details": {
                            "limit": key_info.rate_limit_per_min,
                            "window": "1 minute",
                            "retry_after": 60,
                        },
                    }
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(key_info.rate_limit_per_min),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(key_info.rate_limit_per_min)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
