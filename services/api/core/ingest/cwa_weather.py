"""中央氣象署 API 串接（風速、風向）。

從 CWA 開放資料平台取得自動氣象站觀測資料。
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

from config.settings import CWA_API_KEY, PROCESSED_DIR, RAW_DIR

logger = logging.getLogger(__name__)

CWA_BASE_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"
AUTO_STATION_DATASET = "O-A0001-001"

# 台北區域測站代碼（主要氣象站）
TAIPEI_STATIONS = {
    "466920": "臺北",
    "466910": "鞍部",
    "C0A980": "大直",
    "C0A9C0": "內湖",
    "C0A9E0": "士林",
    "C0A9F0": "社子",
    "C0A9A0": "信義",
    "C0ACA0": "文山",
    "C0AC40": "大安森林",
}


def fetch_current_observations(
    api_key: str | None = None,
    dataset_id: str = AUTO_STATION_DATASET,
) -> pd.DataFrame:
    """取得最新自動氣象站觀測資料。

    Args:
        api_key: CWA API 金鑰，None 時使用環境變數。
        dataset_id: 資料集 ID。

    Returns:
        包含測站位置與風場觀測的 DataFrame。
    """
    if api_key is None:
        api_key = CWA_API_KEY
    if not api_key:
        raise ValueError("CWA_API_KEY not set. Please set it in .env file.")

    url = f"{CWA_BASE_URL}/{dataset_id}"
    params = {"Authorization": api_key, "format": "JSON"}

    logger.info("Fetching observations from CWA dataset %s", dataset_id)
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    records = data.get("records", {}).get("Station", [])

    rows = []
    for station in records:
        station_id = station.get("StationId", "")
        station_name = station.get("StationName", "")
        lat = station.get("GeoInfo", {}).get("Coordinates", [{}])[0].get(
            "StationLatitude"
        )
        lon = station.get("GeoInfo", {}).get("Coordinates", [{}])[0].get(
            "StationLongitude"
        )

        weather = station.get("WeatherElement", {})
        rows.append({
            "station_id": station_id,
            "station_name": station_name,
            "latitude": lat,
            "longitude": lon,
            "wind_speed": weather.get("WindSpeed", None),
            "wind_direction": weather.get("WindDirection", None),
            "gust_speed": weather.get("GustInfo", {}).get("PeakGustSpeed", None),
            "observation_time": station.get("ObsTime", {}).get("DateTime"),
        })

    df = pd.DataFrame(rows)
    df["wind_speed"] = pd.to_numeric(df["wind_speed"], errors="coerce")
    df["wind_direction"] = pd.to_numeric(df["wind_direction"], errors="coerce")
    df["gust_speed"] = pd.to_numeric(df["gust_speed"], errors="coerce")

    logger.info("Fetched %d station observations", len(df))
    return df


def filter_taipei_stations(df: pd.DataFrame) -> pd.DataFrame:
    """篩選台北區域測站。

    Args:
        df: 全台站觀測 DataFrame。

    Returns:
        台北區域的觀測 DataFrame。
    """
    taipei_ids = set(TAIPEI_STATIONS.keys())
    mask = df["station_id"].isin(taipei_ids)

    # 也用經緯度範圍篩選（台北盆地附近）
    geo_mask = (
        (df["latitude"] >= 24.95)
        & (df["latitude"] <= 25.22)
        & (df["longitude"] >= 121.45)
        & (df["longitude"] <= 121.67)
    )

    result = df[mask | geo_mask].copy()
    logger.info("Filtered to %d Taipei-area stations", len(result))
    return result


def save_observations(
    df: pd.DataFrame,
    output_path: Path | str | None = None,
    city: str = "taipei",
) -> Path:
    """儲存觀測資料。

    Args:
        df: 觀測 DataFrame。
        output_path: 輸出路徑。
        city: 城市名稱。

    Returns:
        輸出檔案路徑。
    """
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        output_path = RAW_DIR / "weather" / f"{city}_wind_{timestamp}.csv"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info("Saved %d records to %s", len(df), output_path)
    return output_path


def load_historical_wind(
    path: Path | str,
) -> pd.DataFrame:
    """讀取歷史風場資料（CSV 格式）。

    Args:
        path: CSV 檔案路徑或目錄。

    Returns:
        合併後的風場 DataFrame。
    """
    path = Path(path)
    if path.is_dir():
        csv_files = sorted(path.glob("*.csv"))
        if not csv_files:
            raise FileNotFoundError(f"No CSV files found in {path}")
        df = pd.concat([pd.read_csv(f) for f in csv_files], ignore_index=True)
    else:
        df = pd.read_csv(path)

    df["wind_speed"] = pd.to_numeric(df["wind_speed"], errors="coerce")
    df["wind_direction"] = pd.to_numeric(df["wind_direction"], errors="coerce")

    logger.info("Loaded %d historical wind records", len(df))
    return df


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    region = sys.argv[sys.argv.index("--region") + 1] if "--region" in sys.argv else "taipei"
    df = fetch_current_observations()
    df = filter_taipei_stations(df)
    save_observations(df, city=region)
