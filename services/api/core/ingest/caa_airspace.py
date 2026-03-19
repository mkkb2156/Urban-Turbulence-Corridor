"""CAA 無人機空域圖層下載與處理。

從民航局無人機管理平台取得禁/限飛區圖層，
供飛行規劃時進行合規性檢查。

來源: https://drone.caa.gov.tw
格式: GeoJSON / KML

Usage:
    python -m src.ingest.caa_airspace --city taipei
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import geopandas as gpd
from shapely.geometry import shape, Point

from config.settings import CRS_INTERNAL, PROCESSED_DIR, RAW_DIR, get_city_config

logger = logging.getLogger(__name__)

# 空域類型分類
AIRSPACE_TYPES = {
    "prohibited": "禁飛區",        # 完全禁止
    "restricted": "限飛區",        # 需申請
    "airport": "機場周邊限制區",   # 高度限制
    "military": "軍事管制區",      # 禁止
    "special": "特殊管制區",       # 特定條件
}

# CAA 無人機管理平台 API endpoints（如有公開 API）
CAA_API_BASE = "https://drone.caa.gov.tw"


def load_airspace_geojson(path: Path | str) -> gpd.GeoDataFrame:
    """從 GeoJSON 載入空域圖層。

    Args:
        path: GeoJSON 檔案路徑。

    Returns:
        空域 GeoDataFrame（EPSG:3826）。
    """
    path = Path(path)
    gdf = gpd.read_file(path)

    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    gdf = gdf.to_crs(CRS_INTERNAL)

    logger.info("Loaded %d airspace zones from %s", len(gdf), path)
    return gdf


def create_taipei_airspace_mock() -> gpd.GeoDataFrame:
    """建立台北區域無人機空域 mock data。

    基於公開資訊建立主要禁/限飛區，供 demo 使用。
    正式版本應從 CAA 取得完整圖層。
    """
    from shapely.geometry import Polygon
    from shapely.ops import transform
    from pyproj import Transformer

    transformer = Transformer.from_crs("EPSG:4326", CRS_INTERNAL, always_xy=True)

    zones = [
        # 松山機場（完全禁飛）
        {
            "name": "臺北松山機場",
            "type": "airport",
            "restriction": "prohibited",
            "max_height_m": 0,
            "geometry_4326": Polygon([
                (121.5439, 25.0627), (121.5614, 25.0627),
                (121.5614, 25.0726), (121.5439, 25.0726),
            ]),
        },
        # 松山機場限制區（60m 以下可飛）
        {
            "name": "松山機場周邊限制區",
            "type": "airport",
            "restriction": "restricted",
            "max_height_m": 60,
            "geometry_4326": Polygon([
                (121.5300, 25.0500), (121.5800, 25.0500),
                (121.5800, 25.0850), (121.5300, 25.0850),
            ]),
        },
        # 總統府周邊禁飛
        {
            "name": "總統府周邊",
            "type": "prohibited",
            "restriction": "prohibited",
            "max_height_m": 0,
            "geometry_4326": Point(121.5120, 25.0400).buffer(0.005),
        },
        # 軍事設施
        {
            "name": "圓山營區",
            "type": "military",
            "restriction": "prohibited",
            "max_height_m": 0,
            "geometry_4326": Point(121.5245, 25.0755).buffer(0.003),
        },
        # 河濱公園（開放區，120m 限高）
        {
            "name": "基隆河沿岸河濱公園",
            "type": "special",
            "restriction": "open_with_limit",
            "max_height_m": 120,
            "geometry_4326": Polygon([
                (121.5100, 25.0600), (121.5600, 25.0600),
                (121.5600, 25.0650), (121.5100, 25.0650),
            ]),
        },
    ]

    rows = []
    for z in zones:
        geom_4326 = z.pop("geometry_4326")
        geom_3826 = transform(transformer.transform, geom_4326)
        rows.append({**z, "geometry": geom_3826})

    gdf = gpd.GeoDataFrame(rows, crs=CRS_INTERNAL)
    logger.info("Created %d mock airspace zones for Taipei", len(gdf))
    return gdf


def save_airspace(
    gdf: gpd.GeoDataFrame,
    city: str = "taipei",
    output_path: Path | str | None = None,
) -> Path:
    """儲存空域圖層。"""
    if output_path is None:
        output_path = PROCESSED_DIR / "airspace" / f"{city}_airspace.gpkg"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    gdf.to_file(output_path, driver="GPKG")
    logger.info("Saved %d airspace zones to %s", len(gdf), output_path)
    return output_path


def check_point_airspace(
    lon: float, lat: float, height: float,
    airspace_gdf: gpd.GeoDataFrame,
) -> dict:
    """檢查某點是否在禁/限飛區內。

    Args:
        lon: 經度 (WGS84)。
        lat: 緯度 (WGS84)。
        height: 飛行高度 (m)。
        airspace_gdf: 空域 GeoDataFrame (EPSG:3826)。

    Returns:
        檢查結果字典。
    """
    from pyproj import Transformer

    transformer = Transformer.from_crs("EPSG:4326", CRS_INTERNAL, always_xy=True)
    x, y = transformer.transform(lon, lat)
    point = Point(x, y)

    violations = []
    for _, zone in airspace_gdf.iterrows():
        if zone.geometry.contains(point):
            if zone["restriction"] == "prohibited":
                violations.append({
                    "zone": zone["name"],
                    "type": zone["type"],
                    "restriction": "prohibited",
                    "message": f"禁飛區：{zone['name']}",
                })
            elif zone["restriction"] == "restricted" and height > zone.get("max_height_m", 0):
                violations.append({
                    "zone": zone["name"],
                    "type": zone["type"],
                    "restriction": "height_exceeded",
                    "max_height_m": zone["max_height_m"],
                    "message": f"限飛區 {zone['name']}：飛行高度 {height}m 超過限制 {zone['max_height_m']}m",
                })

    return {
        "lon": lon,
        "lat": lat,
        "height": height,
        "flyable": len(violations) == 0,
        "violations": violations,
    }


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    city = sys.argv[sys.argv.index("--city") + 1] if "--city" in sys.argv else "taipei"

    gdf = create_taipei_airspace_mock()
    save_airspace(gdf, city=city)
