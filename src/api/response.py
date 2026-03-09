"""統一 API Response Envelope。

所有 API 回傳統一使用 envelope 格式：
- 單筆: {"data": {...}, "meta": {...}}
- 列表: {"data": [...], "meta": {"total": N, ...}}
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


APP_VERSION = "0.1.0"


def success(
    data: Any,
    meta: dict | None = None,
) -> dict:
    """包裝成功回應。

    Args:
        data: 回傳資料（可以是 dict、list、Pydantic model）
        meta: 額外的 metadata（pagination、timing 等）
    """
    base_meta = {
        "version": APP_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    if meta:
        base_meta.update(meta)

    return {
        "data": data,
        "meta": base_meta,
    }


def success_list(
    data: list,
    total: int | None = None,
    page: int | None = None,
    per_page: int | None = None,
    meta: dict | None = None,
) -> dict:
    """包裝列表回應（含分頁資訊）。"""
    base_meta = {
        "version": APP_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": total if total is not None else len(data),
    }
    if page is not None:
        base_meta["page"] = page
    if per_page is not None:
        base_meta["per_page"] = per_page
    if meta:
        base_meta.update(meta)

    return {
        "data": data,
        "meta": base_meta,
    }
