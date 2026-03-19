"""統一錯誤處理 — 標準 error response 格式。

所有 API 錯誤繼承 UTCError，由全域 exception handler 統一處理。
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class UTCError(Exception):
    """UTC API 基礎錯誤。"""

    def __init__(
        self,
        code: str,
        message: str,
        status: int = 400,
        details: dict | list | None = None,
    ):
        self.code = code
        self.message = message
        self.status = status
        self.details = details
        super().__init__(message)


class NotFoundError(UTCError):
    """資源不存在 (404)。"""

    def __init__(self, message: str = "Resource not found", details=None):
        super().__init__("NOT_FOUND", message, 404, details)


class ValidationError(UTCError):
    """請求參數驗證失敗 (422)。"""

    def __init__(self, message: str = "Validation failed", details=None):
        super().__init__("VALIDATION_ERROR", message, 422, details)


class DatabaseError(UTCError):
    """資料庫不可用 (503)。"""

    def __init__(self, message: str = "Database unavailable", details=None):
        super().__init__("DATABASE_ERROR", message, 503, details)


class ExternalAPIError(UTCError):
    """外部 API 呼叫失敗 (502)。"""

    def __init__(self, message: str = "External API error", details=None):
        super().__init__("EXTERNAL_API_ERROR", message, 502, details)


class AuthenticationError(UTCError):
    """認證失敗 (401)。"""

    def __init__(self, message: str = "Authentication required", details=None):
        super().__init__("UNAUTHORIZED", message, 401, details)


class RateLimitError(UTCError):
    """超過限流 (429)。"""

    def __init__(self, message: str = "Rate limit exceeded", details=None):
        super().__init__("RATE_LIMIT_EXCEEDED", message, 429, details)


# ── Exception handlers (註冊到 FastAPI app) ──────────────────────


async def utc_error_handler(_request: Request, exc: UTCError) -> JSONResponse:
    """統一處理 UTCError，回傳標準 error response。"""
    return JSONResponse(
        status_code=exc.status,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def generic_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """處理未預期的例外，回傳 500 Internal Server Error。"""
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": None,
            }
        },
    )
