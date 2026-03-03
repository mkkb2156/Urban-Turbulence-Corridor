#!/usr/bin/env python3
"""Generate realistic synthetic building data for Taipei and save as GeoPackage.

Output: data/processed/buildings/taipei_buildings.gpkg
CRS:    EPSG:3826 (TWD97 / TM2 zone 121)

Buildings are clustered to mimic real urban density patterns, with height
distributions that reflect residential, commercial, and skyscraper zones.
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
from pyproj import Transformer
from shapely.affinity import rotate
from shapely.geometry import box

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SEED = 42
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "buildings" / "taipei_buildings.gpkg"
TARGET_CRS = "EPSG:3826"

# Taipei bounding box in WGS84
WGS84_BOUNDS = (121.457, 24.960, 121.666, 25.210)  # (minx, miny, maxx, maxy)

# Cluster definitions (lon, lat in WGS84, number of buildings, spatial spread in metres)
# Each tuple: (centre_lon, centre_lat, n_buildings, sigma_x_m, sigma_y_m, description)
CLUSTERS = [
    # Dense commercial / financial cores
    (121.565, 25.033, 600, 600, 600, "Xinyi district – skyscrapers & offices"),
    (121.522, 25.053, 500, 700, 700, "Zhongshan district – mixed commercial"),
    (121.515, 25.042, 400, 600, 600, "Zhongzheng / Main Station area"),
    # Medium-density residential / mixed
    (121.543, 25.060, 350, 900, 800, "Songshan / Nanjing area"),
    (121.505, 25.070, 300, 800, 800, "Datong / Yanping area"),
    (121.560, 25.075, 250, 900, 900, "Neihu technology park"),
    (121.530, 25.020, 300, 800, 800, "Da-an residential"),
    (121.490, 25.030, 250, 700, 700, "Wanhua / Longshan area"),
    # Sparser edges
    (121.585, 25.050, 200, 1200, 1200, "Eastern hills fringe"),
    (121.480, 25.090, 200, 1000, 1000, "Beitou / Shilin fringe"),
    (121.610, 25.060, 150, 1000, 1000, "Far-east Nangang"),
    (121.540, 25.110, 150, 1200, 1200, "Tianmu / Yangmingshan fringe"),
    (121.570, 25.000, 150, 900, 900, "Southern Xinyi edge"),
]

# ---------------------------------------------------------------------------
# Height distribution helpers
# ---------------------------------------------------------------------------

def _sample_heights(rng: np.random.Generator, n: int, cluster_centre_lon: float,
                    cluster_centre_lat: float) -> np.ndarray:
    """Return an array of building heights realistic for the cluster location.

    - Xinyi core (within ~0.01 deg): higher chance of skyscrapers (80-200 m)
    - Commercial cores: more mid-rise offices (30-80 m)
    - Everywhere else: mostly residential (12-30 m)
    """
    heights = np.empty(n, dtype=np.float64)

    # Distance from Xinyi centre (rough degrees)
    d_xinyi = np.hypot(cluster_centre_lon - 121.565, cluster_centre_lat - 25.033)
    # Distance from Zhongshan centre
    d_zhongshan = np.hypot(cluster_centre_lon - 121.522, cluster_centre_lat - 25.053)

    if d_xinyi < 0.012:
        # Xinyi financial district – many tall buildings
        p_skyscraper = 0.08
        p_office = 0.35
    elif d_xinyi < 0.025 or d_zhongshan < 0.015:
        # Near-core commercial
        p_skyscraper = 0.02
        p_office = 0.25
    else:
        # Residential / suburban
        p_skyscraper = 0.005
        p_office = 0.10

    p_residential = 1.0 - p_skyscraper - p_office

    categories = rng.choice(
        ["residential", "office", "skyscraper"],
        size=n,
        p=[p_residential, p_office, p_skyscraper],
    )

    mask_res = categories == "residential"
    mask_off = categories == "office"
    mask_sky = categories == "skyscraper"

    # Residential: 12-30 m (roughly 4-10 floors) – use truncated normal
    n_res = mask_res.sum()
    if n_res:
        h = rng.normal(loc=20.0, scale=5.0, size=n_res)
        heights[mask_res] = np.clip(h, 12.0, 30.0)

    # Office: 30-80 m
    n_off = mask_off.sum()
    if n_off:
        h = rng.normal(loc=50.0, scale=14.0, size=n_off)
        heights[mask_off] = np.clip(h, 30.0, 80.0)

    # Skyscraper: 80-200 m (lognormal-ish, skewed towards lower end)
    n_sky = mask_sky.sum()
    if n_sky:
        h = rng.lognormal(mean=np.log(110.0), sigma=0.3, size=n_sky)
        heights[mask_sky] = np.clip(h, 80.0, 200.0)

    return np.round(heights, 1)


# ---------------------------------------------------------------------------
# Building footprint generator
# ---------------------------------------------------------------------------

def _make_footprint(cx: float, cy: float, rng: np.random.Generator):
    """Create a randomly sized and rotated rectangular polygon centred at (cx, cy).

    Side lengths: 10-80 m, with most buildings in the 15-40 m range.
    """
    # Lognormal gives a realistic right-skewed size distribution
    w = float(np.clip(rng.lognormal(mean=np.log(22.0), sigma=0.45), 10.0, 80.0))
    h = float(np.clip(rng.lognormal(mean=np.log(18.0), sigma=0.45), 10.0, 80.0))
    angle = rng.uniform(0, 180)

    rect = box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    return rotate(rect, angle, origin="centroid")


# ---------------------------------------------------------------------------
# Main generation logic
# ---------------------------------------------------------------------------

def generate_buildings() -> gpd.GeoDataFrame:
    """Generate clustered synthetic buildings for Taipei in EPSG:3826."""
    rng = np.random.default_rng(SEED)

    # Set up coordinate transformer WGS84 -> EPSG:3826
    transformer = Transformer.from_crs("EPSG:4326", TARGET_CRS, always_xy=True)

    # Convert Taipei bounds to projected CRS for clipping
    bx_min, by_min = transformer.transform(WGS84_BOUNDS[0], WGS84_BOUNDS[1])
    bx_max, by_max = transformer.transform(WGS84_BOUNDS[2], WGS84_BOUNDS[3])

    geometries = []
    heights = []

    for lon, lat, n, sigma_x, sigma_y, _desc in CLUSTERS:
        # Project cluster centre
        cx, cy = transformer.transform(lon, lat)

        # Sample building centres from 2-D Gaussian
        xs = rng.normal(loc=cx, scale=sigma_x, size=n)
        ys = rng.normal(loc=cy, scale=sigma_y, size=n)

        # Clip to Taipei bounds
        mask = (xs >= bx_min) & (xs <= bx_max) & (ys >= by_min) & (ys <= by_max)
        xs = xs[mask]
        ys = ys[mask]

        n_kept = len(xs)
        if n_kept == 0:
            continue

        # Heights for this cluster
        h = _sample_heights(rng, n_kept, lon, lat)
        heights.extend(h.tolist())

        # Footprints
        for x, y in zip(xs, ys):
            geometries.append(_make_footprint(x, y, rng))

    gdf = gpd.GeoDataFrame(
        {
            "height": heights,
            "height_source": "synthetic",
        },
        geometry=geometries,
        crs=TARGET_CRS,
    )

    return gdf


def main():
    print("Generating synthetic buildings for Taipei ...")
    gdf = generate_buildings()

    # Ensure output directory exists
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Save
    gdf.to_file(OUTPUT_PATH, driver="GPKG")

    # Report
    print(f"Saved {len(gdf)} buildings to {OUTPUT_PATH}")
    print(f"  CRS : {gdf.crs}")
    print(f"  Columns: {list(gdf.columns)}")
    print(f"  Height range: {gdf['height'].min():.1f} – {gdf['height'].max():.1f} m")
    print(f"  Mean height : {gdf['height'].mean():.1f} m")


if __name__ == "__main__":
    main()
