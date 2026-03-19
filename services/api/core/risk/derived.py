"""衍生數據計算模組。

從 grid_cells 現有欄位計算對無人機航線有價值的衍生指標：
- 湍流強度 (Turbulence Intensity, TI)
- 風切變指數 (Wind Shear Exponent)
- 陣風因子 (Gust Factor)
- 建築遮蔽指數 (Shelter Index)
- 可用飛行高度範圍
- 逆風/側風分量 (Headwind / Crosswind)
- Weibull 超越機率 (Exceedance Probability)
"""

from __future__ import annotations

import math
import logging

logger = logging.getLogger(__name__)


# ── 湍流強度 ──────────────────────────────────────────────────────

def turbulence_intensity(z: float, z0: float, zd: float) -> float | None:
    """計算指定高度的湍流強度。

    TI ≈ 1 / ln((z - zd) / z0)

    城市環境 TI 通常 0.2-0.5，開闊地約 0.1。
    TI > 0.3 建議消費級無人機避開。
    """
    if z0 <= 0 or z <= zd or (z - zd) <= z0:
        return None
    return 1.0 / math.log((z - zd) / z0)


# ── 風切變指數 ────────────────────────────────────────────────────

def wind_shear_exponent(u1: float, u2: float, z1: float, z2: float) -> float | None:
    """計算兩高度間的風切變指數 α。

    α = ln(U₂/U₁) / ln(z₂/z₁)

    α > 0.3 表示強風切變，起降時需特別注意。
    正常範圍 0.1-0.5。
    """
    if u1 <= 0 or u2 <= 0 or z1 <= 0 or z2 <= 0 or z1 == z2:
        return None
    return math.log(u2 / u1) / math.log(z2 / z1)


# ── 陣風因子 ──────────────────────────────────────────────────────

def gust_factor(ti: float, fai_max: float, peak_factor: float = 3.0) -> float | None:
    """計算陣風因子。

    GF = 1 + g × TI × (1 + 0.5 × fai_max)

    g = 3.0 (尖峰因子，3σ 機率)
    預測最大瞬間風速 = U_mean × GF
    城市環境 GF 通常 1.5-3.0。
    """
    if ti is None or ti <= 0:
        return None
    fai_capped = min(fai_max or 0, 1.0)
    return 1.0 + peak_factor * ti * (1.0 + 0.5 * fai_capped)


# ── 建築遮蔽指數 ──────────────────────────────────────────────────

def shelter_index(svf: float, fai_ne: float, fai_sw: float, bcr: float) -> float | None:
    """計算建築遮蔽效果。

    shelter = (1 - SVF) × (1 + FAI_dominant) × BCR

    高 shelter = 建築物擋風，實際風速較低，但也意味著更多亂流。
    範圍 0-1。
    """
    if svf is None or bcr is None:
        return None
    fai_dominant = max(fai_ne or 0, fai_sw or 0)
    raw = (1.0 - svf) * (1.0 + fai_dominant) * bcr
    return min(max(raw, 0.0), 1.0)


# ── 可用飛行高度範圍 ──────────────────────────────────────────────

def flyable_altitude_range(
    mean_height: float,
    max_height: float,
    airspace_ceiling: float = 120.0,
) -> tuple[float, float]:
    """計算無人機可用高度範圍。

    min_safe = max(mean_height + 20m, max_height + 10m)
    max_legal = min(120m, airspace_ceiling)

    Returns:
        (min_safe_alt, max_legal_alt)
    """
    min_safe = max(
        (mean_height or 0) + 20.0,
        (max_height or 0) + 10.0,
    )
    max_legal = min(120.0, airspace_ceiling)
    return (round(min_safe, 1), round(max_legal, 1))


# ── 逆風/側風分量 ────────────────────────────────────────────────

def headwind_crosswind(
    wind_speed: float,
    wind_direction_deg: float,
    route_bearing_deg: float,
) -> dict:
    """計算路線的逆風與側風分量。

    headwind > 0: 逆風（增加電池消耗）
    headwind < 0: 順風（節省電力）
    crosswind: 側風絕對值（影響穩定性）

    Args:
        wind_speed: 風速 (m/s)
        wind_direction_deg: 風向角度 (degrees, 0=N, 風從哪裡來)
        route_bearing_deg: 路線方位角 (degrees, 0=N)

    Returns:
        dict with headwind, crosswind, effective_groundspeed
    """
    # 風向是「風從哪裡來」，轉為「風往哪裡去」
    wind_to_deg = (wind_direction_deg + 180.0) % 360.0
    angle_diff = math.radians(wind_to_deg - route_bearing_deg)

    headwind = -wind_speed * math.cos(angle_diff)  # 正值=逆風
    crosswind = abs(wind_speed * math.sin(angle_diff))

    # 假設無人機巡航速度 10 m/s
    cruise_speed = 10.0
    effective_groundspeed = max(2.0, cruise_speed - headwind)

    return {
        "headwind": round(headwind, 2),
        "crosswind": round(crosswind, 2),
        "effective_groundspeed": round(effective_groundspeed, 2),
        "wind_effect_pct": round(headwind / cruise_speed * 100, 1),
    }


# ── Weibull 超越機率 ─────────────────────────────────────────────

def weibull_exceedance(
    threshold_speed: float,
    weibull_k: float,
    weibull_c: float,
) -> float | None:
    """計算風速超越指定閾值的機率。

    P(V > V_threshold) = exp(-(V_threshold / c)^k)

    Args:
        threshold_speed: 無人機最大抗風能力 (m/s)
        weibull_k: Weibull 形狀參數
        weibull_c: Weibull 尺度參數

    Returns:
        超越機率 (0-1)
    """
    if weibull_k <= 0 or weibull_c <= 0 or threshold_speed < 0:
        return None
    return math.exp(-((threshold_speed / weibull_c) ** weibull_k))


# ── 最佳飛行時段 ─────────────────────────────────────────────────

def find_best_flight_windows(
    forecasts: list[dict],
    max_wind_speed: float,
    min_consecutive_hours: int = 2,
) -> list[dict]:
    """從預報數據中找出最佳飛行時段。

    Args:
        forecasts: 逐時預報列表，每筆需含 time, wind_speed, risk_level
        max_wind_speed: 無人機最大容忍風速 (m/s)
        min_consecutive_hours: 最少連續適飛時數

    Returns:
        list of {start, end, hours, avg_wind, max_wind, risk_level}
    """
    # 先安全地取得閾值（70% 作為安全裕度）
    safe_speed = max_wind_speed * 0.7

    windows: list[dict] = []
    current_start = None
    current_speeds: list[float] = []

    for fc in forecasts:
        speed = fc.get("wind_speed", 999)
        if speed <= safe_speed:
            if current_start is None:
                current_start = fc["time"]
            current_speeds.append(speed)
        else:
            # 結束目前窗口
            if current_start and len(current_speeds) >= min_consecutive_hours:
                windows.append({
                    "start": current_start,
                    "end": fc["time"],
                    "hours": len(current_speeds),
                    "avg_wind": round(sum(current_speeds) / len(current_speeds), 1),
                    "max_wind": round(max(current_speeds), 1),
                    "min_wind": round(min(current_speeds), 1),
                })
            current_start = None
            current_speeds = []

    # 處理最後一個窗口
    if current_start and len(current_speeds) >= min_consecutive_hours:
        windows.append({
            "start": current_start,
            "end": forecasts[-1]["time"],
            "hours": len(current_speeds),
            "avg_wind": round(sum(current_speeds) / len(current_speeds), 1),
            "max_wind": round(max(current_speeds), 1),
            "min_wind": round(min(current_speeds), 1),
        })

    return windows


# ── 批量計算所有衍生欄位 ─────────────────────────────────────────

def compute_all_derived(row: dict) -> dict:
    """從單筆 grid_cell 資料計算所有衍生指標。

    Args:
        row: dict with z0, zd, wind_50m, wind_80m, wind_120m,
             svf, bcr, fai_ne, fai_sw, fai_max, mean_height, max_height

    Returns:
        dict with all derived fields
    """
    z0 = row.get("z0") or 0
    zd = row.get("zd") or 0
    fai_max_val = row.get("fai_max") or 0

    # 湍流強度
    ti_50 = turbulence_intensity(50, z0, zd)
    ti_80 = turbulence_intensity(80, z0, zd)
    ti_120 = turbulence_intensity(120, z0, zd)

    # 風切變
    w50 = row.get("wind_50m") or 0
    w80 = row.get("wind_80m") or 0
    w120 = row.get("wind_120m") or 0
    shear_50_80 = wind_shear_exponent(w50, w80, 50, 80)
    shear_80_120 = wind_shear_exponent(w80, w120, 80, 120)

    # 陣風因子
    gf = gust_factor(ti_50, fai_max_val)

    # 遮蔽指數
    si = shelter_index(
        row.get("svf"),
        row.get("fai_ne"),
        row.get("fai_sw"),
        row.get("bcr"),
    )

    # 高度範圍
    min_alt, max_alt = flyable_altitude_range(
        row.get("mean_height") or 0,
        row.get("max_height") or 0,
    )

    return {
        "turbulence_50m": round(ti_50, 4) if ti_50 else None,
        "turbulence_80m": round(ti_80, 4) if ti_80 else None,
        "turbulence_120m": round(ti_120, 4) if ti_120 else None,
        "shear_50_80": round(shear_50_80, 4) if shear_50_80 else None,
        "shear_80_120": round(shear_80_120, 4) if shear_80_120 else None,
        "gust_factor": round(gf, 3) if gf else None,
        "shelter_index": round(si, 4) if si else None,
        "min_safe_alt": min_alt,
        "max_legal_alt": max_alt,
        "flyable_range_m": round(max_alt - min_alt, 1),
        "gust_speed_50m": round(w50 * gf, 1) if gf and w50 else None,
        "gust_speed_80m": round(w80 * gf, 1) if gf and w80 else None,
        "gust_speed_120m": round(w120 * gf, 1) if gf and w120 else None,
    }
