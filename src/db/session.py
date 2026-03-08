"""資料庫連線與 Session 管理。

使用 FastAPI Depends() 注入 DB session，
確保每個 request 有獨立的 session lifecycle。
"""

from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from config.settings import DATABASE_URL

logger = logging.getLogger(__name__)

# 全域 engine（connection pool），應用程式生命週期內只建立一次
_engine = None


def get_engine():
    """取得或建立全域 SQLAlchemy engine。"""
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=300,
        )
    return _engine


_SessionLocal = None


def _get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — 提供 DB session，request 結束時自動關閉。

    Usage:
        @router.get("/example")
        async def example(db: Session = Depends(get_db)):
            result = db.execute(text("SELECT 1"))
    """
    factory = _get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()


def check_db_available() -> bool:
    """快速檢查 DB 是否可連線。"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def table_exists(conn, table_name: str) -> bool:
    """檢查資料庫中是否存在指定的資料表。"""
    result = conn.execute(
        text(
            "SELECT EXISTS ("
            "  SELECT FROM information_schema.tables "
            "  WHERE table_name = :tbl"
            ")"
        ),
        {"tbl": table_name},
    ).scalar()
    return bool(result)
