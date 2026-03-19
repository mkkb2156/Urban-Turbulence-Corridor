"""風險等級分類器（綠/黃/紅/黑）。

依據估算風速將網格分類為四級風險。
"""

from __future__ import annotations

import logging
from pathlib import Path

import geopandas as gpd
import numpy as np
import yaml

from config.settings import CRS_INTERNAL, PROJECT_ROOT

logger = logging.getLogger(__name__)


def load_risk_thresholds(
    config_path: Path | str | None = None,
) -> dict:
    """載入風險等級門檻設定。

    Args:
        config_path: YAML 設定檔路徑。

    Returns:
        風險等級設定字典。
    """
    if config_path is None:
        config_path = PROJECT_ROOT / "config" / "risk_thresholds.yaml"
    config_path = Path(config_path)

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config["risk_levels"]


def classify_wind_risk(
    grid: gpd.GeoDataFrame,
    wind_col: str = "wind_50m",
    thresholds: dict | None = None,
) -> gpd.GeoDataFrame:
    """依據風速分類風險等級。

    等級定義：
    - green:  <= 5 m/s  安全
    - yellow: <= 8 m/s  注意
    - red:    <= 12 m/s 危險
    - black:  > 12 m/s  極度危險

    Args:
        grid: 分析網格，需含風速欄位。
        wind_col: 風速欄位名稱。
        thresholds: 風險門檻，None 時從 YAML 載入。

    Returns:
        grid GeoDataFrame 新增 'risk_level'、'risk_label'、'risk_color' 欄位。
    """
    if wind_col not in grid.columns:
        raise ValueError(f"Grid must have '{wind_col}' column")

    if thresholds is None:
        thresholds = load_risk_thresholds()

    grid = grid.copy()
    wind_speed = grid[wind_col].values

    levels = np.full(len(grid), "black", dtype=object)
    labels = np.full(len(grid), "極度危險", dtype=object)
    colors = np.full(len(grid), "#2c3e50", dtype=object)

    # 由高到低判斷（最高級別優先）
    for level_name in ["red", "yellow", "green"]:
        level_config = thresholds[level_name]
        max_speed = level_config["max_wind_speed"]
        mask = wind_speed <= max_speed
        levels[mask] = level_name
        labels[mask] = level_config["label"]
        colors[mask] = level_config["color"]

    grid["risk_level"] = levels
    grid["risk_label"] = labels
    grid["risk_color"] = colors

    # 統計
    for level in ["green", "yellow", "red", "black"]:
        count = (levels == level).sum()
        pct = count / len(grid) * 100
        logger.info("Risk level %s: %d cells (%.1f%%)", level, count, pct)

    return grid


def classify_multi_height_risk(
    grid: gpd.GeoDataFrame,
    heights: list[int] = [50, 80, 120],
    thresholds: dict | None = None,
) -> gpd.GeoDataFrame:
    """為多個高度計算風險等級。

    Args:
        grid: 含多高度風速欄位的網格。
        heights: 高度列表（公尺）。
        thresholds: 風險門檻。

    Returns:
        grid 新增每個高度的 risk 欄位。
    """
    for height in heights:
        wind_col = f"wind_{height}m"
        if wind_col in grid.columns:
            grid = classify_wind_risk(grid, wind_col, thresholds)
            # 重命名為帶高度的欄位
            grid = grid.rename(columns={
                "risk_level": f"risk_level_{height}m",
                "risk_label": f"risk_label_{height}m",
                "risk_color": f"risk_color_{height}m",
            })

    return grid


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    city = sys.argv[sys.argv.index("--city") + 1] if "--city" in sys.argv else "taipei"
    logger.info("Risk classification for %s", city)
