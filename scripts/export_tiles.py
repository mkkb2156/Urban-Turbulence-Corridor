#!/usr/bin/env python3
"""匯出向量圖磚與靜態互動地圖。

Usage:
    python scripts/export_tiles.py --city taipei --format html
    python scripts/export_tiles.py --city taipei --format geojson
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from config.settings import CRS_OUTPUT, OUTPUT_DIR

logger = logging.getLogger("utc.export")


def export_to_geojson(city: str = "taipei") -> Path:
    """匯出網格結果為 GeoJSON（EPSG:4326）。"""
    import geopandas as gpd

    grid_path = OUTPUT_DIR / f"{city}_grid.gpkg"
    if not grid_path.exists():
        raise FileNotFoundError(f"Grid not found: {grid_path}. Run pipeline first.")

    gdf = gpd.read_file(grid_path)
    gdf = gdf.to_crs(CRS_OUTPUT)

    output = OUTPUT_DIR / f"{city}_grid.geojson"
    gdf.to_file(output, driver="GeoJSON")
    logger.info("Exported GeoJSON to %s", output)
    return output


def export_to_html_map(city: str = "taipei") -> Path:
    """產出 Folium 互動地圖。"""
    import folium
    import geopandas as gpd
    from folium.features import GeoJsonTooltip

    grid_path = OUTPUT_DIR / f"{city}_grid.gpkg"
    if not grid_path.exists():
        raise FileNotFoundError(f"Grid not found: {grid_path}. Run pipeline first.")

    gdf = gpd.read_file(grid_path)
    gdf = gdf.to_crs(CRS_OUTPUT)

    # 地圖中心
    center_lat = gdf.geometry.centroid.y.mean()
    center_lon = gdf.geometry.centroid.x.mean()

    m = folium.Map(location=[center_lat, center_lon], zoom_start=14)

    # 風險等級圖層
    if "risk_level" in gdf.columns:
        color_map = {
            "green": "#2ecc71",
            "yellow": "#f1c40f",
            "red": "#e74c3c",
            "black": "#2c3e50",
        }

        def style_function(feature):
            risk = feature["properties"].get("risk_level", "unknown")
            return {
                "fillColor": color_map.get(risk, "#999999"),
                "color": "#333333",
                "weight": 0.5,
                "fillOpacity": 0.6,
            }

        tooltip_fields = ["grid_id", "risk_level"]
        if "risk_score" in gdf.columns:
            tooltip_fields.append("risk_score")
        if "wind_50m" in gdf.columns:
            tooltip_fields.append("wind_50m")

        folium.GeoJson(
            gdf[["geometry"] + [c for c in tooltip_fields if c in gdf.columns]].to_json(),
            style_function=style_function,
            tooltip=GeoJsonTooltip(fields=[c for c in tooltip_fields if c in gdf.columns]),
            name="Wind Risk",
        ).add_to(m)

    # 風廊圖層
    corridor_path = OUTPUT_DIR / f"{city}_corridors.gpkg"
    if corridor_path.exists():
        corridors = gpd.read_file(corridor_path).to_crs(CRS_OUTPUT)
        folium.GeoJson(
            corridors.to_json(),
            style_function=lambda x: {
                "color": "#3498db" if x["properties"].get("corridor_class") == "primary" else "#95a5a6",
                "weight": 4 if x["properties"].get("corridor_class") == "primary" else 2,
            },
            name="Wind Corridors",
        ).add_to(m)

    folium.LayerControl().add_to(m)

    output = OUTPUT_DIR / f"{city}_risk_map.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output))
    logger.info("Exported HTML map to %s", output)
    return output


def main():
    parser = argparse.ArgumentParser(description="UTC Export")
    parser.add_argument("--city", default="taipei")
    parser.add_argument("--format", choices=["geojson", "html", "both"], default="both")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.format in ("geojson", "both"):
        export_to_geojson(args.city)
    if args.format in ("html", "both"):
        export_to_html_map(args.city)


if __name__ == "__main__":
    main()
