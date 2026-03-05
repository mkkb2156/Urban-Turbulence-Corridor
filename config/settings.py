"""全域設定 — 城市邊界、CRS、網格大小等。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# === 路徑 ===
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = DATA_DIR / "output"

# === 座標系統 ===
CRS_INTERNAL = "EPSG:3826"  # TWD97/TM2 zone 121（公尺）
CRS_OUTPUT = "EPSG:4326"  # WGS 84

# === 網格 ===
DEFAULT_GRID_SIZE: int = int(os.getenv("DEFAULT_GRID_SIZE", "100"))  # 公尺

# === 資料庫 ===
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "utc")
DB_USER = os.getenv("DB_USER", "utc")
DB_PASSWORD = os.getenv("DB_PASSWORD", "utc")
# 優先使用 DATABASE_URL 環境變數（Vercel / Railway 等 PaaS 常用）
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
)

# === Supabase ===
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# === Redis ===
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# === API ===
CWA_API_KEY = os.getenv("CWA_API_KEY", "")
OPEN_METEO_API_KEY = os.getenv("OPEN_METEO_API_KEY", "")
CDS_API_KEY = os.getenv("CDS_API_KEY", "")
CDS_API_URL = os.getenv("CDS_API_URL", "https://cds.climate.copernicus.eu/api")

# === 應用程式 ===
APP_ENV = os.getenv("APP_ENV", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DEFAULT_CITY = os.getenv("DEFAULT_CITY", "taipei")

# === 建物高度清洗 ===
BUILDING_HEIGHT_MIN: float = 3.0  # 公尺
BUILDING_HEIGHT_MAX: float = 300.0  # 公尺
BUILDING_HEIGHT_DEFAULT: float = 12.0  # 台灣 4 層住宅常見高度
BUILDING_HEIGHT_CM_THRESHOLD: float = 500.0  # 高於此值視為公分誤植，除以 100

# === 風向 ===
WIND_DIRECTIONS_16 = [i * 22.5 for i in range(16)]  # 0°, 22.5°, ..., 337.5°

# === 飛行高度 ===
DRONE_HEIGHTS: list[float] = [50.0, 80.0, 120.0]  # 公尺

# === von Kármán 常數 ===
VON_KARMAN: float = 0.4


@dataclass
class CityConfig:
    """城市特定設定。"""

    name: str
    bounds_4326: tuple[float, float, float, float]  # (minx, miny, maxx, maxy) in WGS84
    wind_source_points_desc: list[str] = field(default_factory=list)
    primary_wind_directions: dict[str, tuple[float, float]] = field(default_factory=dict)


# 台北設定
TAIPEI = CityConfig(
    name="taipei",
    bounds_4326=(121.457, 24.960, 121.666, 25.210),
    wind_source_points_desc=[
        "關渡隘口（西北）",
        "基隆河谷（東北）",
        "新店溪谷口（南）",
    ],
    primary_wind_directions={
        "northeast": (22.5, 45.0),  # 東北季風 10-4月
        "southwest": (202.5, 225.0),  # 西南季風 6-9月
    },
)

# 台北信義區+大安區 pilot 測試區
TAIPEI_PILOT = CityConfig(
    name="taipei_pilot",
    bounds_4326=(121.535, 25.020, 121.575, 25.050),
    wind_source_points_desc=["信義區東側（象山方向）", "仁愛路西側入口"],
    primary_wind_directions={
        "northeast": (22.5, 45.0),
        "southwest": (202.5, 225.0),
    },
)

CITY_CONFIGS: dict[str, CityConfig] = {
    "taipei": TAIPEI,
    "taipei_pilot": TAIPEI_PILOT,
}


def get_city_config(city: str) -> CityConfig:
    """取得城市設定。"""
    if city not in CITY_CONFIGS:
        raise ValueError(f"Unknown city: {city}. Available: {list(CITY_CONFIGS.keys())}")
    return CITY_CONFIGS[city]
