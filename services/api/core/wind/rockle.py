"""Röckle (1990) 簡化 2.5D 診斷風場模型。

基於 URock 方法，實作建築物繞流效應：
1. 位移區 (Displacement) — 迎風面，風減速
2. 空腔區 (Cavity) — 正後方回流
3. 尾流區 (Wake) — 風速逐漸恢復

不依賴 QGIS/H2GIS，使用 NumPy 實作獨立運算。

參考:
- Röckle (1990) "Bestimmung der Strömungsverhältnisse im Bereich komplexer Bebauungsstrukturen"
- Kaplan & Dinar (1996) parameterizations
- URock (https://github.com/j3r3m1/urock)
"""

from __future__ import annotations

import logging
import math
from typing import NamedTuple

import numpy as np

logger = logging.getLogger(__name__)


class BuildingInfo(NamedTuple):
    """建築物簡化資訊（軸對齊矩形）。"""
    cx: float       # 中心 x (m)
    cy: float       # 中心 y (m)
    width: float    # 迎風面寬度 (m)
    depth: float    # 沿風向深度 (m)
    height: float   # 建築高度 (m)


def _rotate_point(x: float, y: float, angle_rad: float) -> tuple[float, float]:
    """將點繞原點旋轉。"""
    cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
    return x * cos_a - y * sin_a, x * sin_a + y * cos_a


def _building_zones_1d(
    width: float,
    depth: float,
    height: float,
) -> dict:
    """計算單棟建築物的影響區長度。

    Returns:
        dict: displacement_length, cavity_length, wake_length
    """
    # Röckle (1990) 參數化
    ld = 1.5 * width                           # 位移區（迎風）
    lc = min(1.8 * width, depth)               # 空腔區（建築正後方）
    lw = width * height / max(width, height) * 3.0  # 尾流區

    return {
        "displacement_length": ld,
        "cavity_length": lc,
        "wake_length": lw,
    }


def compute_rockle_field(
    buildings: list[dict],
    grid_bounds: tuple[float, float, float, float],
    reference_wind_speed: float,
    reference_wind_direction: float,
    target_height: float = 50.0,
    resolution: float = 10.0,
) -> dict:
    """計算 2D Röckle 風場。

    Args:
        buildings: 建築物列表，每個包含 cx, cy, width, depth, height (EPSG:3826 座標)。
        grid_bounds: (minx, miny, maxx, maxy) 計算範圍 (EPSG:3826)。
        reference_wind_speed: 參考風速 (m/s) at reference height。
        reference_wind_direction: 風向 (deg, 氣象慣例 0=N, 90=E)。
        target_height: 目標飛行高度 (m)。
        resolution: 網格解析度 (m)。

    Returns:
        dict with:
            u: 2D array of wind speed (m/s)
            v: 2D array of v-component (m/s)
            speed: 2D array of wind speed magnitude
            x_coords: 1D array of x coordinates
            y_coords: 1D array of y coordinates
    """
    minx, miny, maxx, maxy = grid_bounds

    # 建立計算網格
    x_coords = np.arange(minx, maxx, resolution)
    y_coords = np.arange(miny, maxy, resolution)
    nx, ny = len(x_coords), len(y_coords)

    if nx == 0 or ny == 0:
        return {"u": np.array([[]]), "v": np.array([[]]), "speed": np.array([[]]),
                "x_coords": x_coords, "y_coords": y_coords}

    # 風向轉換：氣象慣例 → 數學角度（風從哪裡來）
    # 氣象: 0=N(from north), 90=E(from east)
    # 數學: 風向量方向 = 氣象角度 + 180° (風往哪裡去)
    wind_math_deg = (reference_wind_direction + 180) % 360
    wind_rad = math.radians(wind_math_deg)

    # 參考風的 u, v 分量（往哪裡去）
    u_ref = reference_wind_speed * math.sin(wind_rad)
    v_ref = reference_wind_speed * math.cos(wind_rad)

    # 初始化風場為均勻參考風
    u_field = np.full((ny, nx), u_ref, dtype=np.float64)
    v_field = np.full((ny, nx), v_ref, dtype=np.float64)

    # 高度衰減因子：飛行高度越高，建築效應越弱
    for bld in buildings:
        bh = bld.get("height", 20.0)
        if target_height > bh * 2.5:
            continue  # 飛行高度遠高於建築，略過
        height_factor = max(0.0, 1.0 - (target_height - bh) / (bh * 1.5))
        height_factor = min(1.0, height_factor)

        _apply_building_effect(
            u_field, v_field,
            x_coords, y_coords,
            bld, reference_wind_speed, reference_wind_direction,
            height_factor,
        )

    speed_field = np.sqrt(u_field ** 2 + v_field ** 2)

    logger.info(
        "Röckle field: %dx%d, speed min=%.1f max=%.1f mean=%.1f m/s",
        nx, ny,
        speed_field.min(), speed_field.max(), speed_field.mean(),
    )

    return {
        "u": u_field,
        "v": v_field,
        "speed": speed_field,
        "x_coords": x_coords,
        "y_coords": y_coords,
    }


def _apply_building_effect(
    u_field: np.ndarray,
    v_field: np.ndarray,
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    building: dict,
    ref_speed: float,
    ref_direction: float,
    height_factor: float,
):
    """將單棟建築的 Röckle 效應套用到風場。"""
    cx = building["cx"]
    cy = building["cy"]
    width = building.get("width", 30.0)
    depth = building.get("depth", 30.0)
    height = building.get("height", 20.0)

    zones = _building_zones_1d(width, depth, height)
    ld = zones["displacement_length"]
    lc = zones["cavity_length"]
    lw = zones["wake_length"]

    # 風向角（風從哪裡來的方向）
    wind_from_rad = math.radians(ref_direction)

    # 沿風向的單位向量（從上風到下風）
    dx_wind = math.sin(wind_from_rad)
    dy_wind = math.cos(wind_from_rad)

    # 計算每個格點相對於建築中心的位置
    xx, yy = np.meshgrid(x_coords, y_coords)
    rel_x = xx - cx
    rel_y = yy - cy

    # 沿風向和垂直風向的投影
    along_wind = rel_x * dx_wind + rel_y * dy_wind     # 正=下風
    cross_wind = -rel_x * dy_wind + rel_y * dx_wind     # 橫風

    # 橫風影響範圍：建築寬度的一半 + buffer
    half_w = width / 2
    in_cross_range = np.abs(cross_wind) < half_w * 1.5

    # === 位移區（迎風面） ===
    displacement_mask = (
        in_cross_range &
        (along_wind < 0) &
        (along_wind > -ld) &
        (np.abs(cross_wind) < half_w * 1.2)
    )
    if np.any(displacement_mask):
        # 風速隨接近建築而降低
        dist_ratio = np.clip(-along_wind / ld, 0, 1)
        reduction = 0.5 * (1 - dist_ratio) * height_factor  # 最多減速 50%
        u_field[displacement_mask] *= (1 - reduction[displacement_mask])
        v_field[displacement_mask] *= (1 - reduction[displacement_mask])

    # === 建築物本體 ===
    in_building = (
        (np.abs(along_wind) < depth / 2) &
        (np.abs(cross_wind) < half_w)
    )
    if np.any(in_building):
        u_field[in_building] = 0
        v_field[in_building] = 0

    # === 空腔區（建築正後方） ===
    cavity_mask = (
        (along_wind >= depth / 2) &
        (along_wind < depth / 2 + lc) &
        (np.abs(cross_wind) < half_w * 1.1)
    )
    if np.any(cavity_mask):
        # 回流：反向風速約 -0.3 × 參考風速
        recirculation = -0.3 * ref_speed * height_factor
        cavity_dist = (along_wind[cavity_mask] - depth / 2) / lc
        # 回流隨距離衰減
        u_field[cavity_mask] = recirculation * (1 - cavity_dist) * dx_wind
        v_field[cavity_mask] = recirculation * (1 - cavity_dist) * dy_wind

    # === 尾流區 ===
    wake_start = depth / 2 + lc
    wake_mask = (
        in_cross_range &
        (along_wind >= wake_start) &
        (along_wind < wake_start + lw)
    )
    if np.any(wake_mask):
        # 風速逐漸恢復
        wake_dist = (along_wind[wake_mask] - wake_start) / lw
        recovery = 1 - np.exp(-2.0 * wake_dist)  # 指數恢復
        # 橫風方向衰減
        cross_decay = np.exp(-(cross_wind[wake_mask] / half_w) ** 2)
        deficit = (1 - recovery) * cross_decay * height_factor * 0.5
        u_field[wake_mask] *= (1 - deficit)
        v_field[wake_mask] *= (1 - deficit)

    # === 角落加速 ===
    # 建築兩側加速效應（文氏效應/流線收縮）
    corner_mask = (
        (np.abs(along_wind) < depth / 2 + width * 0.5) &
        (np.abs(cross_wind) >= half_w * 0.8) &
        (np.abs(cross_wind) < half_w * 2.5)
    )
    if np.any(corner_mask):
        # 加速因子：最大約 1.3×
        side_dist = (np.abs(cross_wind[corner_mask]) - half_w) / half_w
        acceleration = 1.0 + 0.3 * np.exp(-side_dist) * height_factor
        u_field[corner_mask] *= acceleration
        v_field[corner_mask] *= acceleration


def rockle_wind_at_point(
    x: float,
    y: float,
    buildings: list[dict],
    reference_wind_speed: float,
    reference_wind_direction: float,
    target_height: float = 50.0,
) -> dict:
    """單點 Röckle 風速查詢。

    Args:
        x, y: 查詢點座標 (EPSG:3826)。
        buildings: 附近建築物列表。
        reference_wind_speed: 參考風速 (m/s)。
        reference_wind_direction: 風向角度。
        target_height: 目標高度 (m)。

    Returns:
        dict: speed, u, v, zone (displacement/cavity/wake/freestream)
    """
    # 建立以查詢點為中心的小範圍網格
    buf = 200.0  # 200m buffer
    result = compute_rockle_field(
        buildings,
        grid_bounds=(x - buf, y - buf, x + buf, y + buf),
        reference_wind_speed=reference_wind_speed,
        reference_wind_direction=reference_wind_direction,
        target_height=target_height,
        resolution=10.0,
    )

    # 找最近的格點
    x_idx = np.argmin(np.abs(result["x_coords"] - x))
    y_idx = np.argmin(np.abs(result["y_coords"] - y))

    speed = float(result["speed"][y_idx, x_idx])
    u = float(result["u"][y_idx, x_idx])
    v = float(result["v"][y_idx, x_idx])

    # 判斷區域
    if speed < 0.1:
        zone = "building"
    elif speed < reference_wind_speed * 0.3:
        zone = "cavity"
    elif speed < reference_wind_speed * 0.7:
        zone = "wake"
    elif speed > reference_wind_speed * 1.1:
        zone = "acceleration"
    else:
        zone = "freestream"

    return {
        "speed": round(speed, 2),
        "u": round(u, 2),
        "v": round(v, 2),
        "zone": zone,
        "reference_speed": reference_wind_speed,
        "speed_ratio": round(speed / reference_wind_speed, 3) if reference_wind_speed > 0 else 1.0,
    }


def buildings_from_grid(
    grid_cells: list[dict],
) -> list[dict]:
    """從 grid_cells 資料推算建築物列表。

    使用 mean_height、max_height、bcr 等指標估算建築尺寸。

    Args:
        grid_cells: 網格資料列表，需含 lon, lat, mean_height, bcr 等。

    Returns:
        建築物列表（簡化矩形）。
    """
    buildings = []
    for cell in grid_cells:
        height = cell.get("mean_height") or cell.get("max_height")
        bcr = cell.get("bcr", 0)
        if not height or height < 5 or bcr < 0.1:
            continue

        # 從 grid cell 中心建立代表性建築
        # 假設 100m 網格，bcr 決定建築佔比
        grid_size = 100.0  # meters
        building_side = grid_size * math.sqrt(bcr)  # 等效建築邊長

        buildings.append({
            "cx": cell.get("cx", cell.get("lon", 0)),
            "cy": cell.get("cy", cell.get("lat", 0)),
            "width": building_side,
            "depth": building_side,
            "height": height,
        })

    return buildings
