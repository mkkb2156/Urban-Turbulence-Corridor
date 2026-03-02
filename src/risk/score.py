"""綜合風險分數計算。

結合多維度指標計算 0-100 的風險分數：
- 風速（主要因子）
- FAI（建物阻擋程度）
- 是否位於風廊
- 街谷效應
- SVF
"""

from __future__ import annotations

import logging

import geopandas as gpd
import numpy as np

logger = logging.getLogger(__name__)

# 風險指標權重
DEFAULT_WEIGHTS = {
    "wind_speed": 0.50,  # 風速是最直接的風險因子
    "fai": 0.15,  # 高 FAI = 高擾流風險
    "corridor": 0.15,  # 風廊 = 較高風速
    "canyon": 0.10,  # 深街谷 = 渦流
    "svf": 0.10,  # 低 SVF = 高遮蔽
}


def normalize_0_1(values: np.ndarray) -> np.ndarray:
    """正規化至 0-1 範圍。"""
    vmin, vmax = values.min(), values.max()
    if vmax == vmin:
        return np.zeros_like(values)
    return (values - vmin) / (vmax - vmin)


def compute_risk_score(
    grid: gpd.GeoDataFrame,
    wind_col: str = "wind_50m",
    fai_col: str = "fai_ne",
    weights: dict[str, float] | None = None,
) -> gpd.GeoDataFrame:
    """計算綜合風險分數。

    Args:
        grid: 分析網格，需含風速、FAI、風廊等欄位。
        wind_col: 風速欄位。
        fai_col: FAI 欄位。
        weights: 各指標權重。

    Returns:
        grid 新增 'risk_score'（0-100）欄位。
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    grid = grid.copy()
    score = np.zeros(len(grid))

    # 風速分數：越高越危險
    if wind_col in grid.columns:
        wind_normalized = normalize_0_1(grid[wind_col].values)
        score += wind_normalized * weights["wind_speed"] * 100

    # FAI 分數：高 FAI = 高擾流（但也可能擋風）
    if fai_col in grid.columns:
        fai_normalized = normalize_0_1(grid[fai_col].values)
        score += fai_normalized * weights["fai"] * 100

    # 風廊分數：在風廊上的網格風險較高
    if "is_corridor" in grid.columns:
        corridor_score = grid["is_corridor"].astype(float).values
        score += corridor_score * weights["corridor"] * 100

    # 街谷分數
    if "mean_hw_ratio" in grid.columns:
        hw_normalized = normalize_0_1(
            grid["mean_hw_ratio"].clip(0, 5).values
        )
        score += hw_normalized * weights["canyon"] * 100

    # SVF 分數：低 SVF = 高遮蔽 = 可能有渦流
    if "svf" in grid.columns:
        svf_inverted = 1 - grid["svf"].values  # 反轉：低 SVF → 高風險
        score += svf_inverted * weights["svf"] * 100

    grid["risk_score"] = np.clip(score, 0, 100).round(1)

    logger.info(
        "Risk score stats: min=%.1f, max=%.1f, mean=%.1f, median=%.1f",
        grid["risk_score"].min(),
        grid["risk_score"].max(),
        grid["risk_score"].mean(),
        grid["risk_score"].median(),
    )

    return grid
