"""OSM 道路網路提取。

從 OpenStreetMap 提取道路網路，用於街谷方向分析與道路寬度估算。
"""

from __future__ import annotations

import logging
from pathlib import Path

import geopandas as gpd
import numpy as np

from config.settings import CRS_INTERNAL, PROCESSED_DIR, get_city_config

logger = logging.getLogger(__name__)

# 主要道路類型對應寬度估算（公尺）
ROAD_WIDTH_ESTIMATES: dict[str, float] = {
    "motorway": 30.0,
    "trunk": 25.0,
    "primary": 20.0,
    "secondary": 15.0,
    "tertiary": 12.0,
    "residential": 8.0,
    "service": 6.0,
    "unclassified": 8.0,
}


def load_osm_roads(
    city: str = "taipei",
    network_type: str = "drive",
) -> gpd.GeoDataFrame:
    """從 OSM 下載道路網路。

    Args:
        city: 城市名稱。
        network_type: 路網類型（drive/walk/bike/all）。

    Returns:
        道路 GeoDataFrame（EPSG:3826）。
    """
    try:
        import osmnx as ox
    except ImportError:
        raise ImportError("osmnx is required: pip install osmnx")

    config = get_city_config(city)
    minx, miny, maxx, maxy = config.bounds_4326

    logger.info("Downloading OSM roads for %s", city)
    graph = ox.graph_from_bbox(
        bbox=(maxy, miny, maxx, minx),
        network_type=network_type,
    )
    edges = ox.graph_to_gdfs(graph, nodes=False, edges=True)
    edges = edges.to_crs(CRS_INTERNAL)

    logger.info("Downloaded %d road segments", len(edges))
    return edges


def estimate_road_widths(roads: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """估算道路寬度。

    Args:
        roads: 道路 GeoDataFrame，需含 'highway' 欄位。

    Returns:
        新增 'road_width' 欄位的 GeoDataFrame。
    """
    roads = roads.copy()

    def _get_width(highway_type: str | list) -> float:
        if isinstance(highway_type, list):
            highway_type = highway_type[0]
        return ROAD_WIDTH_ESTIMATES.get(str(highway_type), 8.0)

    roads["road_width"] = roads["highway"].apply(_get_width)
    return roads


def compute_road_orientations(roads: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """計算道路方位角。

    Args:
        roads: 道路 GeoDataFrame。

    Returns:
        新增 'orientation' 欄位（0-180°）的 GeoDataFrame。
    """
    roads = roads.copy()

    def _azimuth(geom) -> float:
        coords = list(geom.coords)
        if len(coords) < 2:
            return 0.0
        x0, y0 = coords[0]
        x1, y1 = coords[-1]
        angle = np.degrees(np.arctan2(x1 - x0, y1 - y0)) % 360
        return angle if angle <= 180 else angle - 180

    roads["orientation"] = roads.geometry.apply(_azimuth)
    return roads


def preprocess_roads(
    city: str = "taipei",
    output_path: Path | str | None = None,
) -> gpd.GeoDataFrame:
    """完整道路預處理 pipeline。

    Args:
        city: 城市名稱。
        output_path: 輸出路徑。

    Returns:
        處理後的道路 GeoDataFrame。
    """
    roads = load_osm_roads(city)
    roads = estimate_road_widths(roads)
    roads = compute_road_orientations(roads)

    if output_path is None:
        output_path = PROCESSED_DIR / "roads" / f"{city}_roads.gpkg"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 只保留需要的欄位避免 GPKG 序列化問題
    keep_cols = ["geometry", "highway", "name", "road_width", "orientation"]
    save_cols = [c for c in keep_cols if c in roads.columns]
    roads[save_cols].to_file(output_path, driver="GPKG")
    logger.info("Saved %d roads to %s", len(roads), output_path)
    return roads
