"""常用空間查詢。"""

from __future__ import annotations

import logging
from pathlib import Path

import geopandas as gpd
from sqlalchemy import create_engine, text

from config.settings import CRS_INTERNAL, CRS_OUTPUT, DATABASE_URL

logger = logging.getLogger(__name__)


def get_engine(url: str | None = None):
    """建立資料庫連線引擎。"""
    if url is None:
        url = DATABASE_URL
    return create_engine(url)


def query_grid_by_point(
    lon: float,
    lat: float,
    engine=None,
) -> dict | None:
    """查詢某經緯度所在的網格資訊。

    Args:
        lon: 經度（WGS84）。
        lat: 緯度（WGS84）。
        engine: SQLAlchemy engine。

    Returns:
        網格資訊字典，或 None。
    """
    if engine is None:
        engine = get_engine()

    sql = text("""
        SELECT grid_id, bcr, svf, fai_ne, fai_sw,
               wind_50m, wind_80m, wind_120m,
               risk_level, risk_score, is_corridor
        FROM grid_cells
        WHERE ST_Contains(
            geometry,
            ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 3826)
        )
        LIMIT 1
    """)

    with engine.connect() as conn:
        result = conn.execute(sql, {"lon": lon, "lat": lat}).fetchone()

    if result is None:
        return None

    return dict(result._mapping)


def query_grid_by_bbox(
    minx: float,
    miny: float,
    maxx: float,
    maxy: float,
    engine=None,
) -> gpd.GeoDataFrame:
    """查詢 bounding box 範圍內的所有網格。

    Args:
        minx, miny, maxx, maxy: WGS84 經緯度邊界。
        engine: SQLAlchemy engine。

    Returns:
        網格 GeoDataFrame（EPSG:4326）。
    """
    if engine is None:
        engine = get_engine()

    sql = f"""
        SELECT grid_id, bcr, svf, fai_ne, fai_sw,
               wind_50m, wind_80m, wind_120m,
               risk_level, risk_score, is_corridor,
               ST_Transform(geometry, 4326) AS geometry
        FROM grid_cells
        WHERE ST_Intersects(
            geometry,
            ST_Transform(
                ST_MakeEnvelope({minx}, {miny}, {maxx}, {maxy}, 4326),
                3826
            )
        )
    """

    gdf = gpd.read_postgis(sql, engine, geom_col="geometry", crs=CRS_OUTPUT)
    logger.info("Queried %d grid cells in bbox", len(gdf))
    return gdf


def query_corridors_by_city(
    city: str,
    engine=None,
) -> gpd.GeoDataFrame:
    """查詢某城市的所有風廊。

    Args:
        city: 城市名稱。
        engine: SQLAlchemy engine。

    Returns:
        風廊 GeoDataFrame（EPSG:4326）。
    """
    if engine is None:
        engine = get_engine()

    sql = f"""
        SELECT corridor_id, corridor_class, total_cost,
               length_cells,
               ST_Transform(geometry, 4326) AS geometry
        FROM wind_corridors
        WHERE city = '{city}'
        ORDER BY total_cost
    """

    gdf = gpd.read_postgis(sql, engine, geom_col="geometry", crs=CRS_OUTPUT)
    logger.info("Queried %d corridors for %s", len(gdf), city)
    return gdf


def import_grid_to_db(
    grid_path: Path | str,
    city: str = "taipei",
    engine=None,
) -> int:
    """匯入網格計算結果至 PostGIS。

    Args:
        grid_path: GeoPackage 路徑。
        city: 城市名稱。
        engine: SQLAlchemy engine。

    Returns:
        匯入的記錄數。
    """
    if engine is None:
        engine = get_engine()

    gdf = gpd.read_file(grid_path)
    if gdf.crs is None or gdf.crs.to_epsg() != 3826:
        gdf = gdf.to_crs(CRS_INTERNAL)

    gdf["city"] = city

    # 先清除該城市的舊資料，再 append（保留表結構、索引、trigger）
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM grid_cells WHERE city = :city"), {"city": city})

    # 只保留 DB schema 中存在的欄位
    db_columns = [
        "grid_id", "city", "row", "col", "geometry",
        "bcr", "svf", "mean_height", "max_height", "n_buildings", "z0", "zd",
        "fai_ne", "fai_sw", "fai_max", "fai_max_direction",
        "wind_50m", "wind_80m", "wind_120m",
        "is_corridor", "corridor_rank", "risk_level", "risk_score",
    ]
    keep = [c for c in db_columns if c in gdf.columns]
    gdf = gdf[keep]

    gdf.to_postgis("grid_cells", engine, if_exists="append", index=False)
    logger.info("Imported %d grid cells to database", len(gdf))
    return len(gdf)


def import_corridors_to_db(
    corridor_path: Path | str,
    city: str = "taipei",
    engine=None,
) -> int:
    """匯入風廊結果至 PostGIS。

    Args:
        corridor_path: GeoPackage 路徑。
        city: 城市名稱。
        engine: SQLAlchemy engine。

    Returns:
        匯入的記錄數。
    """
    if engine is None:
        engine = get_engine()

    gdf = gpd.read_file(corridor_path)
    if gdf.crs is None or gdf.crs.to_epsg() != 3826:
        gdf = gdf.to_crs(CRS_INTERNAL)

    gdf["city"] = city

    # 先清除該城市的舊資料，再 append（保留表結構、索引、trigger）
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM wind_corridors WHERE city = :city"), {"city": city})

    # 只保留 DB schema 中存在的欄位
    db_columns = [
        "corridor_id", "city", "geometry", "corridor_class",
        "total_cost", "length_cells", "estimated_width", "wind_direction",
    ]
    keep = [c for c in db_columns if c in gdf.columns]
    gdf = gdf[keep]

    gdf.to_postgis("wind_corridors", engine, if_exists="append", index=False)
    logger.info("Imported %d corridors to database", len(gdf))
    return len(gdf)


def update_wind_stats(
    city: str = "taipei",
    engine=None,
) -> None:
    """從本機 processed 風場資料更新 wind_statistics 表。

    Args:
        city: 城市名稱。
        engine: SQLAlchemy engine。
    """
    import json

    from config.settings import PROCESSED_DIR

    if engine is None:
        engine = get_engine()

    stats_path = PROCESSED_DIR / "weather" / f"{city}_wind_stats.json"
    rose_path = PROCESSED_DIR / "weather" / f"{city}_wind_rose.json"

    if not stats_path.exists():
        logger.warning("Wind stats not found at %s", stats_path)
        return

    with open(stats_path, encoding="utf-8") as f:
        stats = json.load(f)

    wind_rose = None
    if rose_path.exists():
        with open(rose_path, encoding="utf-8") as f:
            wind_rose = json.load(f)

    sql = text("""
        INSERT INTO wind_statistics (city, period, mean_speed, median_speed, p95_speed,
                                     dominant_direction, wind_rose, sample_count, updated_at)
        VALUES (:city, :period, :mean_speed, :median_speed, :p95_speed,
                :dominant_direction, :wind_rose, :sample_count, now())
        ON CONFLICT (city, period) DO UPDATE SET
            mean_speed = EXCLUDED.mean_speed,
            median_speed = EXCLUDED.median_speed,
            p95_speed = EXCLUDED.p95_speed,
            dominant_direction = EXCLUDED.dominant_direction,
            wind_rose = EXCLUDED.wind_rose,
            sample_count = EXCLUDED.sample_count,
            updated_at = now()
    """)

    with engine.begin() as conn:
        conn.execute(sql, {
            "city": city,
            "period": "annual",
            "mean_speed": stats.get("mean_speed"),
            "median_speed": stats.get("median_speed"),
            "p95_speed": stats.get("p95_speed"),
            "dominant_direction": None,
            "wind_rose": json.dumps(wind_rose) if wind_rose else None,
            "sample_count": stats.get("record_count"),
        })

    logger.info("Updated wind statistics for %s", city)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    city = "taipei"
    # 嘗試從參數推斷城市名（從檔名）
    for flag in ("--import-grid", "--import-corridors"):
        if flag in sys.argv:
            p = sys.argv[sys.argv.index(flag) + 1]
            name = Path(p).stem  # e.g. "taipei_pilot_grid" -> "taipei_pilot"
            parts = name.rsplit("_", 1)
            if len(parts) == 2:
                city = parts[0]

    if "--import-grid" in sys.argv:
        path = sys.argv[sys.argv.index("--import-grid") + 1]
        import_grid_to_db(path, city=city)

    if "--import-corridors" in sys.argv:
        path = sys.argv[sys.argv.index("--import-corridors") + 1]
        import_corridors_to_db(path, city=city)

    if "--update-wind-stats" in sys.argv:
        update_wind_stats(city=city)
