"""風花圖建立與季節分析。

從 CWA 歷史風場資料建立風花圖，分析主要風向頻率與強度。
"""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config.settings import OUTPUT_DIR

logger = logging.getLogger(__name__)


def build_wind_rose_data(
    wind_df: pd.DataFrame,
    speed_col: str = "wind_speed",
    direction_col: str = "wind_direction",
    n_sectors: int = 16,
) -> pd.DataFrame:
    """從觀測資料建立風花圖統計。

    Args:
        wind_df: 風場觀測 DataFrame。
        speed_col: 風速欄位。
        direction_col: 風向欄位。
        n_sectors: 方向扇區數（16 或 36）。

    Returns:
        風花圖統計 DataFrame，含方向、頻率、平均風速。
    """
    df = wind_df[[speed_col, direction_col]].dropna().copy()

    sector_width = 360 / n_sectors
    df["sector"] = ((df[direction_col] + sector_width / 2) % 360 // sector_width).astype(int)
    df["sector_center"] = df["sector"] * sector_width

    stats = df.groupby("sector_center").agg(
        frequency=(speed_col, "count"),
        mean_speed=(speed_col, "mean"),
        max_speed=(speed_col, "max"),
        std_speed=(speed_col, "std"),
    ).reset_index()

    total = len(df)
    stats["frequency_pct"] = stats["frequency"] / total * 100

    return stats


def get_dominant_direction(
    wind_rose: pd.DataFrame,
    season: str | None = None,
) -> tuple[float, float]:
    """取得主要風向與平均風速。

    Args:
        wind_rose: 風花圖統計 DataFrame。
        season: 季節篩選（'northeast'/'southwest'/None）。

    Returns:
        (主要風向角度, 該方向平均風速) 元組。
    """
    row = wind_rose.loc[wind_rose["frequency_pct"].idxmax()]
    return float(row["sector_center"]), float(row["mean_speed"])


def filter_by_season(
    wind_df: pd.DataFrame,
    season: str,
    time_col: str = "observation_time",
) -> pd.DataFrame:
    """依季節篩選風場資料。

    Args:
        wind_df: 風場 DataFrame。
        season: 'northeast'（10-4月）或 'southwest'（6-9月）。
        time_col: 時間欄位。

    Returns:
        篩選後的 DataFrame。
    """
    df = wind_df.copy()
    if time_col in df.columns:
        df[time_col] = pd.to_datetime(df[time_col])
        month = df[time_col].dt.month
    else:
        logger.warning("No time column found, returning all data")
        return df

    if season == "northeast":
        mask = (month >= 10) | (month <= 4)
    elif season == "southwest":
        mask = (month >= 6) & (month <= 9)
    elif season == "transition":
        mask = month.isin([5, 9, 10])
    else:
        raise ValueError(f"Unknown season: {season}. Use 'northeast'/'southwest'/'transition'.")

    result = df[mask]
    logger.info("Filtered to %d records for %s season", len(result), season)
    return result


def plot_wind_rose(
    wind_rose: pd.DataFrame,
    title: str = "Wind Rose",
    output_path: Path | str | None = None,
) -> None:
    """繪製風花圖。

    Args:
        wind_rose: 風花圖統計 DataFrame。
        title: 圖表標題。
        output_path: 圖片輸出路徑。
    """
    fig, ax = plt.subplots(subplot_kw={"projection": "polar"}, figsize=(8, 8))

    angles = np.radians(wind_rose["sector_center"].values)
    # 氣象慣例：0°=N 在頂部，順時針
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)

    bars = ax.bar(
        angles,
        wind_rose["frequency_pct"].values,
        width=np.radians(360 / len(wind_rose)),
        bottom=0,
        alpha=0.7,
        edgecolor="black",
        linewidth=0.5,
    )

    # 以平均風速著色
    speeds = wind_rose["mean_speed"].values
    norm = plt.Normalize(speeds.min(), speeds.max())
    cmap = plt.cm.YlOrRd
    for bar, speed in zip(bars, speeds):
        bar.set_facecolor(cmap(norm(speed)))

    ax.set_title(title, pad=20, fontsize=14)

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        logger.info("Saved wind rose to %s", output_path)

    plt.close(fig)
