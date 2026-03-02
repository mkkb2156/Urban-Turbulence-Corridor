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
               estimated_width, wind_direction,
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
    gdf.to_postgis("grid_cells", engine, if_exists="replace", index=False)
    logger.info("Imported %d grid cells to database", len(gdf))
    return len(gdf)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    if "--import-grid" in sys.argv:
        path = sys.argv[sys.argv.index("--import-grid") + 1]
        import_grid_to_db(path)
