"""Open-Meteo 氣象資料串接。

從 Open-Meteo API 取得歷史與即時風場資料，
產出風速統計與風花圖所需的逐時觀測。

Open-Meteo 提供：
- 即時預報 (forecast API)
- 歷史重分析 (archive API)
- 10m 高風速、風向、陣風

Usage:
    python -m src.ingest.open_meteo --city taipei --days 365
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from config.settings import PROCESSED_DIR, RAW_DIR, get_city_config

logger = logging.getLogger(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Open-Meteo API key（免費 tier 不需要，付費 tier 可設定）
OPEN_METEO_API_KEY = ""  # 付費用戶填入 API key


def fetch_historical_wind(
    city: str = "taipei",
    days: int = 365,
    api_key: str | None = None,
) -> pd.DataFrame:
    """取得歷史風場資料。

    Args:
        city: 城市名稱。
        days: 回溯天數。
        api_key: Open-Meteo API key（付費用戶）。

    Returns:
        包含 time, wind_speed, wind_direction, wind_gusts 的 DataFrame。
    """
    config = get_city_config(city)
    minx, miny, maxx, maxy = config.bounds_4326
    center_lat = (miny + maxy) / 2
    center_lon = (minx + maxx) / 2

    end_date = datetime.now() - timedelta(days=5)  # archive 有數天延遲
    start_date = end_date - timedelta(days=days)

    params = {
        "latitude": round(center_lat, 4),
        "longitude": round(center_lon, 4),
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "hourly": "wind_speed_10m,wind_direction_10m,wind_gusts_10m",
        "timezone": "Asia/Taipei",
    }
    if api_key:
        params["apikey"] = api_key

    logger.info(
        "Fetching Open-Meteo historical data: %s to %s at (%.4f, %.4f)",
        params["start_date"],
        params["end_date"],
        center_lat,
        center_lon,
    )

    response = requests.get(ARCHIVE_URL, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    hourly = data.get("hourly", {})
    df = pd.DataFrame({
        "time": pd.to_datetime(hourly["time"]),
        "wind_speed": hourly["wind_speed_10m"],
        "wind_direction": hourly["wind_direction_10m"],
        "wind_gusts": hourly.get("wind_gusts_10m"),
    })

    # 移除無效值
    df = df.dropna(subset=["wind_speed", "wind_direction"])
    df["wind_speed"] = df["wind_speed"].astype(float)
    df["wind_direction"] = df["wind_direction"].astype(float)

    logger.info(
        "Historical wind: %d records, speed min=%.1f max=%.1f mean=%.1f m/s",
        len(df),
        df["wind_speed"].min(),
        df["wind_speed"].max(),
        df["wind_speed"].mean(),
    )

    return df


def fetch_current_wind(
    city: str = "taipei",
    api_key: str | None = None,
) -> pd.DataFrame:
    """取得最近 24 小時即時風場資料。

    Args:
        city: 城市名稱。
        api_key: Open-Meteo API key。

    Returns:
        包含 time, wind_speed, wind_direction 的 DataFrame。
    """
    config = get_city_config(city)
    minx, miny, maxx, maxy = config.bounds_4326
    center_lat = (miny + maxy) / 2
    center_lon = (minx + maxx) / 2

    params = {
        "latitude": round(center_lat, 4),
        "longitude": round(center_lon, 4),
        "hourly": "wind_speed_10m,wind_direction_10m,wind_gusts_10m",
        "past_days": 1,
        "forecast_days": 1,
        "timezone": "Asia/Taipei",
    }
    if api_key:
        params["apikey"] = api_key

    logger.info("Fetching Open-Meteo current data for %s", city)

    response = requests.get(FORECAST_URL, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    hourly = data.get("hourly", {})
    df = pd.DataFrame({
        "time": pd.to_datetime(hourly["time"]),
        "wind_speed": hourly["wind_speed_10m"],
        "wind_direction": hourly["wind_direction_10m"],
        "wind_gusts": hourly.get("wind_gusts_10m"),
    })

    df = df.dropna(subset=["wind_speed", "wind_direction"])
    logger.info("Current wind: %d records", len(df))
    return df


def compute_wind_statistics(df: pd.DataFrame) -> dict:
    """計算風場統計。

    Args:
        df: 含有 wind_speed, wind_direction 的 DataFrame。

    Returns:
        統計摘要字典。
    """
    stats = {
        "record_count": len(df),
        "mean_speed": round(float(df["wind_speed"].mean()), 2),
        "max_speed": round(float(df["wind_speed"].max()), 2),
        "median_speed": round(float(df["wind_speed"].median()), 2),
        "std_speed": round(float(df["wind_speed"].std()), 2),
        "p95_speed": round(float(df["wind_speed"].quantile(0.95)), 2),
        "calm_pct": round(float((df["wind_speed"] < 0.5).mean() * 100), 1),
    }

    # 主風向（最頻繁的 8 方位）
    bins = np.arange(-22.5, 360, 45)
    labels = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    dirs = (df["wind_direction"] + 22.5) % 360
    df_copy = df.copy()
    df_copy["dir_bin"] = pd.cut(dirs, bins=np.arange(0, 361, 45), labels=labels, right=False)
    dominant = df_copy["dir_bin"].mode()
    stats["dominant_direction"] = str(dominant.iloc[0]) if len(dominant) > 0 else "N"

    return stats


def compute_wind_rose(df: pd.DataFrame, n_sectors: int = 16) -> list[dict]:
    """計算風花圖資料（16 方位扇區）。

    Args:
        df: 含有 wind_speed, wind_direction 的 DataFrame。
        n_sectors: 扇區數量。

    Returns:
        各扇區 frequency (%) 與 mean_speed 列表。
    """
    sector_width = 360.0 / n_sectors
    direction_names = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
    ]

    sectors = []
    for i in range(n_sectors):
        center_angle = i * sector_width
        lo = (center_angle - sector_width / 2) % 360
        hi = (center_angle + sector_width / 2) % 360

        if lo < hi:
            mask = (df["wind_direction"] >= lo) & (df["wind_direction"] < hi)
        else:
            mask = (df["wind_direction"] >= lo) | (df["wind_direction"] < hi)

        subset = df[mask]
        freq = round(len(subset) / len(df) * 100, 1) if len(df) > 0 else 0.0
        mean_speed = round(float(subset["wind_speed"].mean()), 2) if len(subset) > 0 else 0.0

        sectors.append({
            "direction": direction_names[i],
            "angle": center_angle,
            "frequency": freq,
            "mean_speed": mean_speed,
        })

    return sectors


def save_wind_data(
    df: pd.DataFrame,
    city: str = "taipei",
    output_path: Path | str | None = None,
) -> Path:
    """儲存風場資料與統計。

    Args:
        df: 風場 DataFrame。
        city: 城市名稱。
        output_path: 輸出目錄。

    Returns:
        輸出目錄路徑。
    """
    if output_path is None:
        output_dir = PROCESSED_DIR / "weather"
    else:
        output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 原始逐時資料
    csv_path = output_dir / f"{city}_wind_hourly.csv"
    df.to_csv(csv_path, index=False)
    logger.info("Saved %d hourly records to %s", len(df), csv_path)

    # 風場統計
    stats = compute_wind_statistics(df)
    stats_path = output_dir / f"{city}_wind_stats.json"
    import json
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    logger.info("Saved wind stats to %s", stats_path)

    # 風花圖資料
    rose = compute_wind_rose(df)
    rose_path = output_dir / f"{city}_wind_rose.json"
    with open(rose_path, "w", encoding="utf-8") as f:
        json.dump(rose, f, indent=2, ensure_ascii=False)
    logger.info("Saved wind rose to %s", rose_path)

    return output_dir


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    city = sys.argv[sys.argv.index("--city") + 1] if "--city" in sys.argv else "taipei"
    days = int(sys.argv[sys.argv.index("--days") + 1]) if "--days" in sys.argv else 365

    logger.info("Fetching %d days of wind data for %s", days, city)
    df = fetch_historical_wind(city, days=days)
    save_wind_data(df, city=city)

    stats = compute_wind_statistics(df)
    logger.info("Wind stats: %s", stats)

    rose = compute_wind_rose(df)
    logger.info("Wind rose (top 3 sectors by frequency):")
    for s in sorted(rose, key=lambda x: x["frequency"], reverse=True)[:3]:
        logger.info("  %s: freq=%.1f%%, mean=%.1f m/s", s["direction"], s["frequency"], s["mean_speed"])
