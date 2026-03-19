"""粗糙度長度 z₀ 與零平面位移 zd 計算。

基於 Grimmond & Oke (1999) 形態學方法：
- zd = (1 + α^(-λp)) × (λp - 1) × Hav    （MacDonald et al. 1998）
- z₀ = (1 - zd/Hav) × exp(-(0.5×β×Cd/κ² × (1-zd/Hav) × λf)^(-0.5)) × Hav

其中：
- Hav = 平均建物高度
- λp = plan area ratio (BCR)
- λf = frontal area ratio (FAI)
- α = 4.43, β = 1.0, Cd = 1.2（經驗常數）
- κ = 0.4（von Kármán 常數）
"""

from __future__ import annotations

import logging

import geopandas as gpd
import numpy as np

from config.settings import CRS_INTERNAL, VON_KARMAN

logger = logging.getLogger(__name__)

# MacDonald et al. (1998) 經驗常數
ALPHA = 4.43
BETA = 1.0
CD = 1.2  # 建物阻力係數


def compute_roughness_params(
    grid: gpd.GeoDataFrame,
    buildings: gpd.GeoDataFrame,
    fai_col: str = "fai_ne",
) -> gpd.GeoDataFrame:
    """計算粗糙度長度 z₀ 與零平面位移 zd。

    Args:
        grid: 分析網格（EPSG:3826），需含 'bcr' 與 FAI 欄位。
        buildings: 建物資料（EPSG:3826），需含 'height' 欄位。
        fai_col: 使用的 FAI 欄位名稱。

    Returns:
        grid GeoDataFrame 新增 'z0'、'zd'、'mean_height' 欄位。
    """
    grid = grid.copy()

    # 計算每個網格的平均建物高度
    intersected = gpd.sjoin(
        buildings[["geometry", "height"]],
        grid[["grid_id", "geometry"]],
        how="inner",
        predicate="intersects",
    )

    stats = intersected.groupby("grid_id").agg(
        mean_height=("height", "mean"),
        max_height=("height", "max"),
        std_height=("height", "std"),
        n_buildings=("height", "count"),
    ).reset_index()

    grid = grid.merge(stats, on="grid_id", how="left")
    grid["mean_height"] = grid["mean_height"].fillna(0.0)
    grid["max_height"] = grid["max_height"].fillna(0.0)
    grid["std_height"] = grid["std_height"].fillna(0.0)
    grid["n_buildings"] = grid["n_buildings"].fillna(0).astype(int)

    # BCR (λp) 與 FAI (λf)
    if "bcr" not in grid.columns:
        raise ValueError("Grid must have 'bcr' column. Run compute_bcr() first.")
    if fai_col not in grid.columns:
        raise ValueError(f"Grid must have '{fai_col}' column. Run compute_fai() first.")

    hav = grid["mean_height"].values
    lambda_p = grid["bcr"].values
    lambda_f = grid[fai_col].values

    # 避免除以零
    hav_safe = np.where(hav > 0, hav, 1.0)
    lambda_p_safe = np.clip(lambda_p, 0.001, 0.999)
    lambda_f_safe = np.clip(lambda_f, 0.001, None)

    # zd: MacDonald et al. (1998)
    zd = (1 + ALPHA ** (-lambda_p_safe)) * (lambda_p_safe - 1) * hav_safe
    zd = np.clip(zd, 0, hav_safe * 0.9)  # zd 不超過 0.9 × 平均高度

    # z₀: MacDonald et al. (1998)
    zd_ratio = zd / hav_safe
    inner = 0.5 * BETA * CD / (VON_KARMAN ** 2) * (1 - zd_ratio) * lambda_f_safe
    # 避免 inner 為 0 或負值
    inner = np.clip(inner, 0.001, None)
    z0 = (1 - zd_ratio) * np.exp(-inner ** (-0.5)) * hav_safe

    # 無建物區域設定最小粗糙度
    no_buildings = hav <= 0
    z0[no_buildings] = 0.03  # 開放平地
    zd[no_buildings] = 0.0

    grid["zd"] = zd
    grid["z0"] = z0

    logger.info(
        "Roughness stats: z0 min=%.3f, max=%.3f, mean=%.3f; "
        "zd min=%.1f, max=%.1f, mean=%.1f",
        grid["z0"].min(), grid["z0"].max(), grid["z0"].mean(),
        grid["zd"].min(), grid["zd"].max(), grid["zd"].mean(),
    )

    return grid
