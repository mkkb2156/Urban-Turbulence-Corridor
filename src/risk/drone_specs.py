"""無人機規格對照（抗風能力）。

提供各類無人機的風速容忍上限，用於風險等級計算。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DroneSpec:
    """無人機規格。"""

    name: str
    category: str  # consumer / professional / industrial
    max_wind_tolerance: float  # m/s
    max_altitude: float  # m
    weight_kg: float
    description: str = ""


# 常見無人機規格
DRONE_DATABASE: dict[str, DroneSpec] = {
    "dji_mini_4_pro": DroneSpec(
        name="DJI Mini 4 Pro",
        category="consumer",
        max_wind_tolerance=10.7,
        max_altitude=120.0,
        weight_kg=0.249,
        description="消費級，Level 5 抗風",
    ),
    "dji_air_3": DroneSpec(
        name="DJI Air 3",
        category="consumer",
        max_wind_tolerance=12.0,
        max_altitude=120.0,
        weight_kg=0.720,
        description="消費級，Level 5 抗風",
    ),
    "dji_mavic_3": DroneSpec(
        name="DJI Mavic 3",
        category="professional",
        max_wind_tolerance=12.0,
        max_altitude=120.0,
        weight_kg=0.895,
        description="專業級",
    ),
    "dji_matrice_350": DroneSpec(
        name="DJI Matrice 350 RTK",
        category="industrial",
        max_wind_tolerance=15.0,
        max_altitude=120.0,
        weight_kg=6.47,
        description="工業級，Level 7 抗風",
    ),
    "dji_matrice_30": DroneSpec(
        name="DJI Matrice 30",
        category="industrial",
        max_wind_tolerance=15.0,
        max_altitude=120.0,
        weight_kg=3.77,
        description="工業級",
    ),
}


def get_drone_spec(drone_id: str) -> DroneSpec:
    """取得無人機規格。

    Args:
        drone_id: 無人機 ID。

    Returns:
        DroneSpec 物件。
    """
    if drone_id not in DRONE_DATABASE:
        raise ValueError(
            f"Unknown drone: {drone_id}. "
            f"Available: {list(DRONE_DATABASE.keys())}"
        )
    return DRONE_DATABASE[drone_id]


def check_flyability(
    wind_speed: float,
    drone_id: str,
    safety_margin: float = 0.7,
) -> dict:
    """檢查指定風速下無人機是否可飛。

    Args:
        wind_speed: 風速（m/s）。
        drone_id: 無人機 ID。
        safety_margin: 安全裕度（0-1），0.7 = 風速不超過最大容忍的 70%。

    Returns:
        含 flyable、margin、recommendation 的字典。
    """
    spec = get_drone_spec(drone_id)
    safe_limit = spec.max_wind_tolerance * safety_margin
    margin = (safe_limit - wind_speed) / safe_limit

    if wind_speed <= safe_limit:
        recommendation = "可安全飛行"
    elif wind_speed <= spec.max_wind_tolerance:
        recommendation = "接近極限，建議謹慎"
    else:
        recommendation = "超過最大抗風能力，禁止飛行"

    return {
        "flyable": wind_speed <= safe_limit,
        "wind_speed": wind_speed,
        "safe_limit": safe_limit,
        "max_tolerance": spec.max_wind_tolerance,
        "margin": margin,
        "recommendation": recommendation,
        "drone_name": spec.name,
    }
