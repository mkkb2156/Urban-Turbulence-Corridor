"""API Key 認證 middleware。

支援兩種認證方式：
1. Header: X-API-Key
2. Query param: ?api_key=xxx

白名單端點不需要認證：/health, /docs, /openapi.json, /redoc
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

# 環境變數控制是否啟用 API Key 認證
API_KEY_REQUIRED = os.getenv("API_KEY_REQUIRED", "false").lower() == "true"
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
DEFAULT_RATE_LIMIT = int(os.getenv("DEFAULT_RATE_LIMIT_PER_MIN", "60"))

# 不需要 API Key 的路徑
PUBLIC_PATHS = {
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
}

# 路徑前綴白名單（靜態資源等）
PUBLIC_PREFIXES = (
    "/assets/",
    "/favicon",
)


@dataclass
class APIKeyInfo:
    """API Key 資訊。"""

    key_id: str
    name: str
    plan: str  # free / pro / enterprise
    rate_limit_per_min: int
    is_admin: bool = False


def hash_key(key: str) -> str:
    """SHA-256 hash API key。"""
    return hashlib.sha256(key.encode()).hexdigest()


# ── In-memory API Key store ──────────────────────────────────────
# 生產環境改用 DB 查詢

_key_store: dict[str, APIKeyInfo] = {}


def register_key(raw_key: str, info: APIKeyInfo) -> None:
    """註冊 API Key（開發用）。"""
    _key_store[hash_key(raw_key)] = info


def _init_default_keys() -> None:
    """初始化預設 API Key（開發環境 + admin key）。"""
    # 開發用 key
    register_key("utc-dev-key", APIKeyInfo(
        key_id="dev-001",
        name="Development Key",
        plan="pro",
        rate_limit_per_min=120,
    ))

    # Admin key（從環境變數讀取）
    if ADMIN_API_KEY:
        register_key(ADMIN_API_KEY, APIKeyInfo(
            key_id="admin-001",
            name="Admin Key",
            plan="enterprise",
            rate_limit_per_min=1000,
            is_admin=True,
        ))


_init_default_keys()


def validate_key(raw_key: str) -> APIKeyInfo | None:
    """驗證 API Key，回傳 key info 或 None。"""
    hashed = hash_key(raw_key)
    return _key_store.get(hashed)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """API Key 認證 middleware。

    當 API_KEY_REQUIRED=true 時：
    - 白名單路徑直接放行
    - 其他路徑需提供有效的 API Key
    - 驗證通過後將 APIKeyInfo 注入 request.state.api_key_info
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # 白名單放行
        if path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES):
            return await call_next(request)

        # 靜態資源放行（SPA fallback）
        if not path.startswith("/api/"):
            return await call_next(request)

        # 未啟用認證時，設定匿名 key info
        if not API_KEY_REQUIRED:
            request.state.api_key_info = APIKeyInfo(
                key_id="anonymous",
                name="Anonymous",
                plan="free",
                rate_limit_per_min=DEFAULT_RATE_LIMIT,
            )
            return await call_next(request)

        # 從 header 或 query param 取得 API Key
        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")

        if not api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "API Key required. Provide via X-API-Key header or ?api_key= query parameter.",
                        "details": None,
                    }
                },
            )

        key_info = validate_key(api_key)
        if key_info is None:
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "INVALID_API_KEY",
                        "message": "Invalid API Key.",
                        "details": None,
                    }
                },
            )

        # 注入 key info
        request.state.api_key_info = key_info
        return await call_next(request)
