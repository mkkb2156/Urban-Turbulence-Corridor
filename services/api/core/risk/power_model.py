"""無人機功率與續航模型 — 基於 drone_awe 方法。

核心公式：
- 懸停功率: P_hover = (mg)^1.5 / sqrt(2 * ρ * A * η²)
- 前飛功率: P_forward = P_hover × (V/V_h)^correction + 0.5 * ρ * V³ * Cd * S
- 含風效應: 地面速度 = 空速向量 - 風向量
- 續航: endurance = battery_Wh / P_total (hours)
- 航程: range = endurance × groundspeed (km)

參考:
- Stolaroff et al., "Energy use and life cycle greenhouse gas emissions of drones" (2018)
- drone_awe package (https://github.com/TUDELFT-DCC/drone_awe)
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 物理常數
AIR_DENSITY_SEA = 1.225  # kg/m³ 海平面標準大氣密度
GRAVITY = 9.81  # m/s²
LAPSE_RATE = 0.00012  # kg/m³ per meter (air density decrease with altitude)


@dataclass
class DronePowerSpec:
    """無人機功率計算用物理規格。"""

    name: str
    mass_kg: float              # 起飛全重 (kg)
    n_rotors: int               # 旋翼數
    rotor_radius_m: float       # 單旋翼半徑 (m)
    battery_wh: float           # 電池容量 (Wh)
    drag_coeff: float           # 機體阻力係數
    frontal_area_m2: float      # 迎風截面積 (m²)
    cruise_speed_ms: float      # 設計巡航速度 (m/s)
    motor_efficiency: float     # 馬達+ESC 效率 (0-1)
    max_wind_tolerance: float   # 最大抗風 (m/s)

    @property
    def total_rotor_area(self) -> float:
        """總旋翼掃掠面積 (m²)。"""
        return self.n_rotors * math.pi * self.rotor_radius_m ** 2

    @property
    def disc_loading(self) -> float:
        """旋翼盤載荷 (N/m²)。"""
        return (self.mass_kg * GRAVITY) / self.total_rotor_area


# 5 款 DJI 無人機的功率規格
# 資料來源：DJI 官方規格書 + 公開功率測試
POWER_DATABASE: dict[str, DronePowerSpec] = {
    "dji_mini_4_pro": DronePowerSpec(
        name="DJI Mini 4 Pro",
        mass_kg=0.249,
        n_rotors=4,
        rotor_radius_m=0.077,      # ~3" props
        battery_wh=19.6,           # 2590mAh × 7.58V
        drag_coeff=1.0,
        frontal_area_m2=0.012,
        cruise_speed_ms=10.0,
        motor_efficiency=0.70,
        max_wind_tolerance=10.7,
    ),
    "dji_air_3": DronePowerSpec(
        name="DJI Air 3",
        mass_kg=0.720,
        n_rotors=4,
        rotor_radius_m=0.095,      # ~3.8" props
        battery_wh=47.8,           # 4241mAh × 11.27V
        drag_coeff=0.9,
        frontal_area_m2=0.020,
        cruise_speed_ms=12.0,
        motor_efficiency=0.72,
        max_wind_tolerance=12.0,
    ),
    "dji_mavic_3": DronePowerSpec(
        name="DJI Mavic 3",
        mass_kg=0.895,
        n_rotors=4,
        rotor_radius_m=0.107,      # ~4.25" props
        battery_wh=77.0,           # 5000mAh × 15.4V
        drag_coeff=0.85,
        frontal_area_m2=0.025,
        cruise_speed_ms=14.0,
        motor_efficiency=0.73,
        max_wind_tolerance=12.0,
    ),
    "dji_matrice_350": DronePowerSpec(
        name="DJI Matrice 350 RTK",
        mass_kg=6.47,
        n_rotors=4,
        rotor_radius_m=0.265,      # ~21" props
        battery_wh=522.0,          # 2× TB65 batteries
        drag_coeff=0.8,
        frontal_area_m2=0.15,
        cruise_speed_ms=15.0,
        motor_efficiency=0.80,
        max_wind_tolerance=15.0,
    ),
    "dji_matrice_30": DronePowerSpec(
        name="DJI Matrice 30",
        mass_kg=3.77,
        n_rotors=4,
        rotor_radius_m=0.200,      # ~16" props
        battery_wh=264.0,          # TB30 battery
        drag_coeff=0.8,
        frontal_area_m2=0.08,
        cruise_speed_ms=15.0,
        motor_efficiency=0.78,
        max_wind_tolerance=15.0,
    ),
}

# ID 別名對照（前端使用連字號）
_ALIAS_MAP = {
    "dji_mini4_pro": "dji_mini_4_pro",
    "dji_air3": "dji_air_3",
    "dji_mavic3": "dji_mavic_3",
    "dji_matrice350": "dji_matrice_350",
    "dji_matrice30": "dji_matrice_30",
}


def get_power_spec(drone_id: str) -> DronePowerSpec:
    """取得無人機功率規格。"""
    normalized = drone_id.replace("-", "_")
    normalized = _ALIAS_MAP.get(normalized, normalized)
    if normalized not in POWER_DATABASE:
        raise ValueError(
            f"Unknown drone: {drone_id}. Available: {list(POWER_DATABASE.keys())}"
        )
    return POWER_DATABASE[normalized]


def air_density(altitude_m: float) -> float:
    """根據高度計算空氣密度。簡化的線性遞減模型。"""
    return max(0.5, AIR_DENSITY_SEA - LAPSE_RATE * altitude_m)


def hover_power(spec: DronePowerSpec, altitude_m: float = 0) -> float:
    """計算懸停功率 (W)。

    基於動量理論 (momentum theory):
    P = (mg)^1.5 / sqrt(2 * ρ * A) / η
    """
    rho = air_density(altitude_m)
    weight = spec.mass_kg * GRAVITY
    p_ideal = weight ** 1.5 / math.sqrt(2 * rho * spec.total_rotor_area)
    return p_ideal / spec.motor_efficiency


def forward_power(
    spec: DronePowerSpec,
    airspeed_ms: float,
    altitude_m: float = 0,
) -> float:
    """計算前飛功率 (W)。

    包含：
    1. 誘導功率（隨速度下降）
    2. 寄生阻力功率（隨速度³增加）
    3. 翼型阻力功率
    """
    rho = air_density(altitude_m)
    weight = spec.mass_kg * GRAVITY
    p_hover = hover_power(spec, altitude_m)

    if airspeed_ms < 0.5:
        return p_hover

    # 誘導速度 at hover
    v_hover = math.sqrt(weight / (2 * rho * spec.total_rotor_area))

    # 速度比
    mu = airspeed_ms / v_hover

    # 誘導功率：在高速飛行時降低（~1/mu）
    if mu > 0.1:
        p_induced = p_hover / (mu * spec.motor_efficiency)
    else:
        p_induced = p_hover

    # 寄生阻力功率
    p_parasite = 0.5 * rho * airspeed_ms ** 3 * spec.drag_coeff * spec.frontal_area_m2

    # 翼型阻力（簡化：固定比例 of hover power）
    p_profile = 0.1 * p_hover

    return (p_induced + p_parasite + p_profile) / spec.motor_efficiency


def power_with_wind(
    spec: DronePowerSpec,
    cruise_speed_ms: float | None = None,
    wind_speed_ms: float = 0.0,
    wind_angle_deg: float = 0.0,
    altitude_m: float = 0.0,
) -> dict:
    """計算含風效應的功率、續航與航程。

    Args:
        spec: 無人機功率規格。
        cruise_speed_ms: 空速（巡航速度），None 時使用設計巡航速度。
        wind_speed_ms: 風速 (m/s)。
        wind_angle_deg: 風相對於飛行方向的角度（0=正逆風, 90=正側風, 180=正順風）。
        altitude_m: 飛行高度。

    Returns:
        dict: power_w, groundspeed_ms, endurance_min, range_km, battery_impact_pct
    """
    if cruise_speed_ms is None:
        cruise_speed_ms = spec.cruise_speed_ms

    # 計算地面速度
    wind_angle_rad = math.radians(wind_angle_deg)
    headwind = wind_speed_ms * math.cos(wind_angle_rad)  # 正=逆風
    crosswind = abs(wind_speed_ms * math.sin(wind_angle_rad))

    # 需要增加空速來補償側風（蟹角修正）
    if crosswind > 0 and cruise_speed_ms > crosswind:
        # 實際前進分量 = sqrt(airspeed² - crosswind²)
        forward_component = math.sqrt(cruise_speed_ms ** 2 - crosswind ** 2)
    else:
        forward_component = cruise_speed_ms

    groundspeed = max(0.1, forward_component - headwind)

    # 等效空速（需要更大的空速來維持航跡）
    effective_airspeed = math.sqrt(
        (forward_component) ** 2 + crosswind ** 2
    )

    # 功率計算
    p_flight = forward_power(spec, effective_airspeed, altitude_m)

    # 無風參考功率
    p_no_wind = forward_power(spec, cruise_speed_ms, altitude_m)

    # 續航與航程
    endurance_h = spec.battery_wh / p_flight if p_flight > 0 else 0
    endurance_min = endurance_h * 60
    range_km = groundspeed * endurance_h * 3.6  # m/s → km/h × h

    # 無風續航作為基準
    endurance_no_wind_h = spec.battery_wh / p_no_wind if p_no_wind > 0 else 0
    battery_impact_pct = (1 - endurance_h / endurance_no_wind_h) * 100 if endurance_no_wind_h > 0 else 0

    return {
        "power_w": round(p_flight, 1),
        "hover_power_w": round(hover_power(spec, altitude_m), 1),
        "groundspeed_ms": round(groundspeed, 2),
        "endurance_min": round(endurance_min, 1),
        "range_km": round(range_km, 2),
        "battery_impact_pct": round(battery_impact_pct, 1),
        "headwind_ms": round(headwind, 2),
        "crosswind_ms": round(crosswind, 2),
    }


def mission_feasibility(
    spec: DronePowerSpec,
    segments: list[dict],
    reserve_pct: float = 20.0,
    altitude_m: float = 50.0,
) -> dict:
    """評估路線任務可行性。

    Args:
        spec: 無人機功率規格。
        segments: 路線分段列表，每段需有:
            - distance_m: 距離 (m)
            - bearing: 航向 (deg)
            - wind_speed: 風速 (m/s)
            - wind_direction: 風向 (deg, 氣象慣例)
        reserve_pct: 電池預留百分比。
        altitude_m: 飛行高度。

    Returns:
        dict: feasible, total_energy_wh, battery_remaining_pct, segments_detail, recommended_speed
    """
    total_energy_wh = 0.0
    total_time_s = 0.0
    segments_detail = []
    critical_count = 0

    for seg in segments:
        distance_m = seg.get("distance_m", 0)
        bearing = seg.get("bearing", 0)
        wind_speed = seg.get("wind_speed", 0)
        wind_direction = seg.get("wind_direction", 0)

        # 計算風相對於飛行方向的角度
        # 氣象風向是風「從」哪裡來，飛行方向是航向
        relative_wind_angle = (wind_direction - bearing + 180) % 360

        result = power_with_wind(
            spec,
            wind_speed_ms=wind_speed,
            wind_angle_deg=relative_wind_angle,
            altitude_m=altitude_m,
        )

        # 飛行時間 = 距離 / 地面速度
        if result["groundspeed_ms"] > 0:
            travel_time_s = distance_m / result["groundspeed_ms"]
        else:
            travel_time_s = float("inf")

        # 段能量消耗
        energy_wh = result["power_w"] * travel_time_s / 3600

        total_energy_wh += energy_wh
        total_time_s += travel_time_s

        is_critical = result["battery_impact_pct"] > 30 or wind_speed > spec.max_wind_tolerance * 0.8
        if is_critical:
            critical_count += 1

        segments_detail.append({
            "distance_m": distance_m,
            "bearing": bearing,
            "wind_speed": wind_speed,
            "power_w": result["power_w"],
            "groundspeed_ms": result["groundspeed_ms"],
            "travel_time_s": round(travel_time_s, 1),
            "energy_wh": round(energy_wh, 2),
            "battery_impact_pct": result["battery_impact_pct"],
            "is_critical": is_critical,
        })

    # 可用電池 = 總容量 × (1 - 預留)
    usable_wh = spec.battery_wh * (1 - reserve_pct / 100)
    battery_remaining_pct = max(0, (usable_wh - total_energy_wh) / spec.battery_wh * 100)
    feasible = total_energy_wh <= usable_wh

    # 推薦速度（如果任務不可行，降速可延長航程）
    recommended_speed = spec.cruise_speed_ms
    if not feasible and total_energy_wh > 0:
        # 粗略估算：降速比例
        ratio = usable_wh / total_energy_wh
        recommended_speed = round(spec.cruise_speed_ms * ratio ** 0.5, 1)
        recommended_speed = max(3.0, recommended_speed)  # 不低於 3 m/s

    return {
        "feasible": feasible,
        "total_energy_wh": round(total_energy_wh, 2),
        "battery_capacity_wh": spec.battery_wh,
        "battery_remaining_pct": round(battery_remaining_pct, 1),
        "total_time_s": round(total_time_s, 1),
        "total_time_min": round(total_time_s / 60, 1),
        "critical_segments": critical_count,
        "recommended_speed_ms": recommended_speed,
        "reserve_pct": reserve_pct,
        "segments_detail": segments_detail,
    }
