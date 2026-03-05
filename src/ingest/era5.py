"""ERA5 再分析風場資料下載與處理。

從 ECMWF CDS (Climate Data Store) 下載 ERA5 逐時再分析資料，
計算長期氣候學統計（風玫瑰歷史基線、月份別統計、日變化週期）。

⚠️ 僅供離線使用（本機或 GitHub Actions），不在 Vercel runtime 執行。
   ERA5 單年台北區域約 50-200 MB，處理需 1-5 分鐘/年。

來源: https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels
格式: NetCDF (.nc)
解析度: 0.25° (~31 km)，逐時
時間範圍: 1940–至今

前置需求:
    1. 註冊 CDS 帳號: https://cds.climate.copernicus.eu/
    2. 取得 Personal Access Token
    3. 建立 ~/.cdsapirc:
       url: https://cds.climate.copernicus.eu/api
       key: <YOUR-PERSONAL-ACCESS-TOKEN>
    4. pip install "cdsapi>=0.7.7"

Usage:
    python -m src.ingest.era5 --city taipei --start-year 2020 --end-year 2024
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from config.settings import PROCESSED_DIR, RAW_DIR, get_city_config

logger = logging.getLogger(__name__)


def fetch_era5_wind(
    city: str = "taipei",
    start_year: int = 2020,
    end_year: int | None = None,
    output_dir: Path | str | None = None,
) -> list[Path]:
    """從 CDS 下載 ERA5 逐時 10m 風場資料。

    按年下載以避免單次請求過大。每年台北區域約 50-200 MB。

    Args:
        city: 城市名稱。
        start_year: 起始年份。
        end_year: 結束年份（預設為前一年，避免不完整資料）。
        output_dir: 下載目標目錄。

    Returns:
        下載的 NetCDF 檔案路徑列表。
    """
    import cdsapi

    if end_year is None:
        end_year = datetime.now().year - 1

    config = get_city_config(city)
    minx, miny, maxx, maxy = config.bounds_4326

    # 加 0.5° buffer 確保覆蓋
    area = [
        math.ceil(maxy + 0.5),   # North
        math.floor(minx - 0.5),  # West
        math.floor(miny - 0.5),  # South
        math.ceil(maxx + 0.5),   # East
    ]

    if output_dir is None:
        output_dir = RAW_DIR / "weather" / "era5"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    client = cdsapi.Client()
    downloaded: list[Path] = []

    for year in range(start_year, end_year + 1):
        output_file = output_dir / f"{city}_era5_{year}.nc"

        if output_file.exists():
            logger.info("ERA5 %d already downloaded: %s", year, output_file)
            downloaded.append(output_file)
            continue

        logger.info("Downloading ERA5 %d for %s (area: %s)...", year, city, area)

        request = {
            "product_type": ["reanalysis"],
            "variable": [
                "10m_u_component_of_wind",
                "10m_v_component_of_wind",
                "instantaneous_10m_wind_gust",
            ],
            "year": [str(year)],
            "month": [f"{m:02d}" for m in range(1, 13)],
            "day": [f"{d:02d}" for d in range(1, 32)],
            "time": [f"{h:02d}:00" for h in range(24)],
            "area": area,
            "data_format": "netcdf",
        }

        try:
            client.retrieve(
                "reanalysis-era5-single-levels",
                request,
                str(output_file),
            )
            size_mb = output_file.stat().st_size / 1e6
            logger.info("Downloaded ERA5 %d: %.1f MB", year, size_mb)
            downloaded.append(output_file)
        except Exception as e:
            logger.error("Failed to download ERA5 %d: %s", year, e)

    return downloaded


def process_era5_wind(nc_path: Path | str) -> pd.DataFrame:
    """將 ERA5 NetCDF 轉換為風速/風向 DataFrame。

    u/v 分量 → 風速 + 風向：
        speed = sqrt(u² + v²)
        direction = (270 - atan2(v, u) × 180/π) % 360

    Args:
        nc_path: ERA5 NetCDF 檔案路徑。

    Returns:
        DataFrame: time, wind_speed, wind_direction, wind_gusts
    """
    import xarray as xr

    ds = xr.open_dataset(nc_path)

    # ERA5 變數名稱（可能因版本不同）
    u_var = "u10" if "u10" in ds else "10m_u_component_of_wind"
    v_var = "v10" if "v10" in ds else "10m_v_component_of_wind"
    gust_var = "i10fg" if "i10fg" in ds else "instantaneous_10m_wind_gust"

    u = ds[u_var]
    v = ds[v_var]

    # 空間平均（取城市區域平均值）
    if "latitude" in u.dims:
        u = u.mean(dim=["latitude", "longitude"])
        v = v.mean(dim=["latitude", "longitude"])

    speed = np.sqrt(u**2 + v**2)
    direction = (270 - np.degrees(np.arctan2(v, u))) % 360

    df = pd.DataFrame({
        "time": pd.to_datetime(speed.time.values),
        "wind_speed": speed.values.round(2),
        "wind_direction": direction.values.round(1),
    })

    # 陣風（若有）
    if gust_var in ds:
        gusts = ds[gust_var]
        if "latitude" in gusts.dims:
            gusts = gusts.mean(dim=["latitude", "longitude"])
        df["wind_gusts"] = gusts.values.round(2)

    ds.close()

    df = df.dropna(subset=["wind_speed"])
    logger.info(
        "Processed ERA5: %d records, speed %.1f–%.1f m/s",
        len(df), df["wind_speed"].min(), df["wind_speed"].max(),
    )
    return df


def compute_era5_climatology(
    city: str = "taipei",
    start_year: int = 2020,
    end_year: int | None = None,
    output_path: Path | str | None = None,
) -> dict:
    """計算 ERA5 長期氣候學統計。

    輸出：
    - monthly_wind_rose: 月份別風玫瑰（12 月 × 16 方位）
    - seasonal_stats: 季節別統計（mean/p95/max 風速）
    - diurnal_cycle: 日變化週期（逐時平均風速）
    - overall_stats: 全期統計

    Args:
        city: 城市名稱。
        start_year: 起始年份。
        end_year: 結束年份。
        output_path: 輸出 JSON 路徑。

    Returns:
        氣候學統計字典。
    """
    from src.ingest.open_meteo import compute_wind_rose, compute_wind_statistics

    if end_year is None:
        end_year = datetime.now().year - 1

    raw_dir = RAW_DIR / "weather" / "era5"

    # 合併所有年份
    all_dfs = []
    for year in range(start_year, end_year + 1):
        nc_path = raw_dir / f"{city}_era5_{year}.nc"
        if nc_path.exists():
            df = process_era5_wind(nc_path)
            all_dfs.append(df)
        else:
            logger.warning("ERA5 file not found: %s", nc_path)

    if not all_dfs:
        raise FileNotFoundError(f"No ERA5 data found for {city} ({start_year}-{end_year})")

    df = pd.concat(all_dfs, ignore_index=True)
    df["time"] = pd.to_datetime(df["time"])
    df["month"] = df["time"].dt.month
    df["hour"] = df["time"].dt.hour

    logger.info("Total ERA5 records: %d (%d-%d)", len(df), start_year, end_year)

    # 1. 全期統計
    overall = compute_wind_statistics(df)

    # 2. 月份別風玫瑰
    monthly_rose = {}
    for month in range(1, 13):
        month_df = df[df["month"] == month]
        if len(month_df) > 0:
            monthly_rose[month] = compute_wind_rose(month_df)

    # 3. 季節別統計
    season_map = {12: "DJF", 1: "DJF", 2: "DJF",
                  3: "MAM", 4: "MAM", 5: "MAM",
                  6: "JJA", 7: "JJA", 8: "JJA",
                  9: "SON", 10: "SON", 11: "SON"}
    df["season"] = df["month"].map(season_map)
    seasonal = {}
    for season in ["DJF", "MAM", "JJA", "SON"]:
        s_df = df[df["season"] == season]
        if len(s_df) > 0:
            seasonal[season] = {
                "mean_speed": round(float(s_df["wind_speed"].mean()), 2),
                "p95_speed": round(float(s_df["wind_speed"].quantile(0.95)), 2),
                "max_speed": round(float(s_df["wind_speed"].max()), 2),
                "record_count": len(s_df),
            }

    # 4. 日變化週期（台北時間 UTC+8）
    df["taipei_hour"] = (df["hour"] + 8) % 24
    diurnal = {}
    for h in range(24):
        h_df = df[df["taipei_hour"] == h]
        if len(h_df) > 0:
            diurnal[h] = {
                "mean_speed": round(float(h_df["wind_speed"].mean()), 2),
                "std_speed": round(float(h_df["wind_speed"].std()), 2),
            }

    result = {
        "city": city,
        "period": f"{start_year}-{end_year}",
        "total_records": len(df),
        "overall_stats": overall,
        "monthly_wind_rose": monthly_rose,
        "seasonal_stats": seasonal,
        "diurnal_cycle": diurnal,
        "generated_at": datetime.now().isoformat(),
    }

    # 儲存
    if output_path is None:
        output_path = PROCESSED_DIR / "weather" / f"{city}_era5_climatology.json"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)

    logger.info("Saved ERA5 climatology to %s", output_path)
    return result


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    city = sys.argv[sys.argv.index("--city") + 1] if "--city" in sys.argv else "taipei"
    start = int(sys.argv[sys.argv.index("--start-year") + 1]) if "--start-year" in sys.argv else 2020
    end = int(sys.argv[sys.argv.index("--end-year") + 1]) if "--end-year" in sys.argv else None

    # Step 1: 下載
    logger.info("=== Fetching ERA5 data ===")
    files = fetch_era5_wind(city, start_year=start, end_year=end)
    logger.info("Downloaded %d files", len(files))

    # Step 2: 計算氣候學統計
    logger.info("=== Computing climatology ===")
    result = compute_era5_climatology(city, start_year=start, end_year=end)
    logger.info("Overall: mean=%.1f m/s, p95=%.1f m/s, dominant=%s",
                result["overall_stats"]["mean_speed"],
                result["overall_stats"]["p95_speed"],
                result["overall_stats"]["dominant_direction"])
