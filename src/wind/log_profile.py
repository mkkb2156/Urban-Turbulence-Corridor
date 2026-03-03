"""對數風速剖面降尺度。

U(z) = (u* / κ) × ln((z - zd) / z₀)

將氣象站風速觀測降尺度至無人機飛行高度，
考慮都市粗糙度長度 z₀ 與零平面位移 zd。
"""

from __future__ import annotations

import logging

import geopandas as gpd
import numpy as np

from config.settings import CRS_INTERNAL, DRONE_HEIGHTS, VON_KARMAN

logger = logging.getLogger(__name__)


def log_wind_profile(
    z: float,
    u_star: float,
    z0: float,
    zd: float,
    kappa: float = VON_KARMAN,
) -> float:
    """計算指定高度的風速。

    Args:
        z: 目標高度（公尺）。
        u_star: 摩擦速度（m/s）。
        z0: 粗糙度長度（公尺）。
        zd: 零平面位移（公尺）。
        kappa: von Kármán 常數（預設 0.4）。

    Returns:
        高度 z 的風速（m/s）。

    Raises:
        ValueError: 若 z <= zd（高度低於零平面位移）。
    """
    if z <= zd:
        raise ValueError(f"Target height z={z}m must be above zd={zd}m")
    if z0 <= 0:
        raise ValueError(f"Roughness length z0={z0}m must be positive")

    return (u_star / kappa) * np.log((z - zd) / z0)


def estimate_friction_velocity(
    u_ref: float,
    z_ref: float,
    z0: float,
    zd: float,
    kappa: float = VON_KARMAN,
) -> float:
    """從參考高度風速反推摩擦速度 u*。

    Args:
        u_ref: 參考高度風速（m/s）。
        z_ref: 參考高度（公尺），通常為氣象站 10m。
        z0: 粗糙度長度（公尺）。
        zd: 零平面位移（公尺）。
        kappa: von Kármán 常數。

    Returns:
        摩擦速度 u*（m/s）。
    """
    if z_ref <= zd:
        # Reference height is within the urban canopy layer.
        # Estimate u* from open-terrain conditions since the reference
        # wind speed is measured in open terrain (weather station).
        z0_open = 0.03  # open terrain roughness length
        logger.warning(
            "Reference height %.1fm <= zd %.1fm, using open-terrain u* estimation",
            z_ref, zd,
        )
        log_term = np.log(z_ref / z0_open)
        if log_term <= 0:
            return 0.1
        return u_ref * kappa / log_term

    log_term = np.log((z_ref - zd) / z0)
    if log_term <= 0:
        logger.warning("Invalid log term, using minimum friction velocity")
        return 0.1

    return u_ref * kappa / log_term


def downscale_wind_to_grid(
    grid: gpd.GeoDataFrame,
    reference_speed: float,
    reference_height: float = 10.0,
    target_heights: list[float] | None = None,
    z0_col: str = "z0",
    zd_col: str = "zd",
) -> gpd.GeoDataFrame:
    """將參考風速降尺度至每個網格的目標高度。

    Args:
        grid: 分析網格（EPSG:3826），需含 z0 與 zd 欄位。
        reference_speed: 參考風速（m/s），通常來自 CWA 測站。
        reference_height: 參考高度（公尺），CWA 標準為 10m。
        target_heights: 目標高度列表（公尺），None 時使用預設。
        z0_col: 粗糙度長度欄位名稱。
        zd_col: 零平面位移欄位名稱。

    Returns:
        grid GeoDataFrame 新增 'wind_{height}m' 欄位。
    """
    if target_heights is None:
        target_heights = DRONE_HEIGHTS

    grid = grid.copy()

    z0 = grid[z0_col].values
    zd = grid[zd_col].values

    for height in target_heights:
        col_name = f"wind_{int(height)}m"
        speeds = np.zeros(len(grid))

        for i in range(len(grid)):
            z0_i = max(z0[i], 0.001)  # 最小粗糙度
            zd_i = zd[i]

            # 確保目標高度在零平面位移之上
            if height <= zd_i:
                speeds[i] = 0.0
                continue

            try:
                u_star = estimate_friction_velocity(
                    reference_speed, reference_height, z0_i, zd_i
                )
                speeds[i] = log_wind_profile(height, u_star, z0_i, zd_i)
            except (ValueError, RuntimeWarning):
                speeds[i] = reference_speed  # fallback

            # 物理合理性檢查
            speeds[i] = max(0.0, min(speeds[i], reference_speed * 3.0))

        grid[col_name] = speeds

        logger.info(
            "Wind@%dm stats: min=%.1f, max=%.1f, mean=%.1f m/s",
            int(height),
            grid[col_name].min(),
            grid[col_name].max(),
            grid[col_name].mean(),
        )

    return grid


def compute_wind_speed_ratio(
    grid: gpd.GeoDataFrame,
    target_height: float = 50.0,
    reference_speed: float = 1.0,
) -> gpd.GeoDataFrame:
    """計算風速比（相對於參考風速的加速/減速比）。

    Args:
        grid: 含粗糙度參數的網格。
        target_height: 目標高度。
        reference_speed: 參考風速（用 1.0 得到比值）。

    Returns:
        新增 'wind_speed_ratio' 欄位的 grid。
    """
    result = downscale_wind_to_grid(
        grid, reference_speed, target_heights=[target_height]
    )
    col = f"wind_{int(target_height)}m"
    result["wind_speed_ratio"] = result[col] / reference_speed
    return result


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    city = sys.argv[sys.argv.index("--city") + 1] if "--city" in sys.argv else "taipei"
    heights_str = sys.argv[sys.argv.index("--heights") + 1] if "--heights" in sys.argv else "50,80,120"
    heights = [float(h) for h in heights_str.split(",")]
    logger.info("Wind profile for %s at heights %s", city, heights)
