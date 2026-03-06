#!/usr/bin/env python3
"""一鍵匯入 Pipeline 數據到 Supabase。

使用方式：
    # 1. 確保 .env 有 DATABASE_URL
    # 2. 執行：
    python scripts/import_to_supabase.py
"""

import logging
import sys
from pathlib import Path

# 確保可以 import 專案模組
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text

from config.settings import DATABASE_URL

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

GRID_PATH = Path("data/output/taipei_pilot_grid.gpkg")
CORRIDOR_PATH = Path("data/output/taipei_pilot_corridors.gpkg")
MIGRATION_PATH = Path("src/db/migrations/001_init_postgis.sql")


def run_migration(engine):
    """執行 PostGIS schema migration。"""
    logger.info("Running PostGIS migration...")
    sql = MIGRATION_PATH.read_text(encoding="utf-8")

    # 分割成獨立的 SQL 語句執行
    statements = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]

    with engine.begin() as conn:
        for stmt in statements:
            if stmt:
                try:
                    conn.execute(text(stmt))
                except Exception as e:
                    # CREATE IF NOT EXISTS 等語句可能已存在，跳過
                    logger.warning("Statement warning: %s", str(e)[:100])

    logger.info("Migration completed.")


def import_data(engine):
    """匯入 grid + corridor 數據。"""
    from src.db.queries import import_corridors_to_db, import_grid_to_db

    if GRID_PATH.exists():
        n = import_grid_to_db(GRID_PATH, city="taipei", engine=engine)
        logger.info("Imported %d grid cells.", n)
    else:
        logger.error("Grid file not found: %s", GRID_PATH)

    if CORRIDOR_PATH.exists():
        n = import_corridors_to_db(CORRIDOR_PATH, city="taipei", engine=engine)
        logger.info("Imported %d corridors.", n)
    else:
        logger.error("Corridor file not found: %s", CORRIDOR_PATH)


def verify(engine):
    """驗證匯入結果。"""
    with engine.connect() as conn:
        grid_count = conn.execute(text("SELECT COUNT(*) FROM grid_cells")).scalar()
        corridor_count = conn.execute(text("SELECT COUNT(*) FROM wind_corridors")).scalar()

    logger.info("=== Verification ===")
    logger.info("grid_cells: %d rows", grid_count)
    logger.info("wind_corridors: %d rows", corridor_count)

    if grid_count > 0 and corridor_count > 0:
        logger.info("SUCCESS - Data imported to Supabase!")
    else:
        logger.error("FAILED - Missing data!")
        return False
    return True


def main():
    if not DATABASE_URL or "localhost" in DATABASE_URL:
        logger.error("DATABASE_URL not set or pointing to localhost.")
        logger.error("Set it in .env: DATABASE_URL=postgresql://postgres:PASSWORD@db.xxx.supabase.co:5432/postgres")
        sys.exit(1)

    logger.info("Connecting to: %s...%s", DATABASE_URL[:30], DATABASE_URL[-20:])
    engine = create_engine(DATABASE_URL)

    # Test connection
    with engine.connect() as conn:
        ver = conn.execute(text("SELECT version()")).scalar()
        logger.info("Connected: %s", ver[:60])

    run_migration(engine)
    import_data(engine)
    verify(engine)

    logger.info("")
    logger.info("Next step: Set DATABASE_URL in Vercel Dashboard -> Settings -> Environment Variables")


if __name__ == "__main__":
    main()
