"""風場 PNG Texture 編碼器。

將 U/V 風速分量編碼為 PNG 圖片：
  R 通道 = U 分量（正規化至 0-255）
  G 通道 = V 分量（正規化至 0-255）
  B 通道 = 0（保留）

供 WebGL GPU 粒子風場渲染使用。
每像素代表一個網格點，台北市約 38×35 = 1,330 像素，< 5KB。
"""

from __future__ import annotations

import hashlib
import io
import logging
import math
from typing import NamedTuple

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# 風速正規化範圍（m/s）
DEFAULT_WIND_MIN = -25.0
DEFAULT_WIND_MAX = 25.0


class WindTextureResult(NamedTuple):
    """Wind texture PNG 編碼結果。"""
    png_bytes: bytes
    width: int
    height: int
    bounds: tuple[float, float, float, float]  # lng_min, lat_min, lng_max, lat_max
    wind_min: float
    wind_max: float


def _wind_to_uint8(values: np.ndarray, wind_min: float, wind_max: float) -> np.ndarray:
    """將風速值正規化至 0-255。"""
    normalized = (values - wind_min) / (wind_max - wind_min)
    clamped = np.clip(normalized, 0.0, 1.0)
    return np.round(clamped * 255).astype(np.uint8)


def encode_wind_texture(
    u_field: np.ndarray,
    v_field: np.ndarray,
    bounds: tuple[float, float, float, float],
    wind_min: float = DEFAULT_WIND_MIN,
    wind_max: float = DEFAULT_WIND_MAX,
) -> WindTextureResult:
    """將 U/V 風場陣列編碼為 PNG。

    Args:
        u_field: U 風速分量 2D 陣列 (lat, lon)，單位 m/s
        v_field: V 風速分量 2D 陣列 (lat, lon)，單位 m/s
        bounds: 經緯度邊界 (lng_min, lat_min, lng_max, lat_max)
        wind_min: 正規化最小值（m/s）
        wind_max: 正規化最大值（m/s）

    Returns:
        WindTextureResult 含 PNG bytes 和解碼元資料。
    """
    assert u_field.shape == v_field.shape, "U/V 陣列形狀不一致"

    n_lat, n_lon = u_field.shape

    r_channel = _wind_to_uint8(u_field, wind_min, wind_max)
    g_channel = _wind_to_uint8(v_field, wind_min, wind_max)
    b_channel = np.zeros_like(r_channel)

    rgb = np.stack([r_channel, g_channel, b_channel], axis=2)
    img = Image.fromarray(rgb, mode="RGB")

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    png_bytes = buf.getvalue()

    logger.info(
        "Wind texture encoded: %dx%d px, %d bytes, bounds=%s",
        n_lon, n_lat, len(png_bytes), bounds,
    )

    return WindTextureResult(
        png_bytes=png_bytes,
        width=n_lon,
        height=n_lat,
        bounds=bounds,
        wind_min=wind_min,
        wind_max=wind_max,
    )


def generate_wind_field_from_grids(
    grid_data: list[dict],
    bbox: tuple[float, float, float, float],
    altitude: float = 80.0,
    resolution: float = 100.0,
    ref_wind_speed: float = 5.0,
    ref_wind_direction: float = 45.0,
) -> tuple[np.ndarray, np.ndarray]:
    """從 morphology_grids 資料生成 U/V 風場。

    使用 Log Profile 降尺度 + z0/zd 空間變化。

    Args:
        grid_data: grid_cells 資料（含 lon, lat, z0, zd, wind_speed 等）
        bbox: 邊界 (lng_min, lat_min, lng_max, lat_max)
        altitude: 目標高度（m AGL）
        resolution: 網格解析度（m）
        ref_wind_speed: 參考風速（m/s）
        ref_wind_direction: 參考風向（度，氣象慣例，北=0）

    Returns:
        (u_field, v_field) 2D 陣列
    """
    lng_min, lat_min, lng_max, lat_max = bbox

    # 計算網格尺寸（約 111km/度）
    n_lon = max(1, int((lng_max - lng_min) * 111000 / resolution))
    n_lat = max(1, int((lat_max - lat_min) * 111000 / resolution))

    # 風向轉換為數學角度（氣象慣例：北=0，順時針）
    wind_rad = math.radians(270.0 - ref_wind_direction)
    base_u = ref_wind_speed * math.cos(wind_rad)
    base_v = ref_wind_speed * math.sin(wind_rad)

    # 初始化風場
    u_field = np.full((n_lat, n_lon), base_u, dtype=np.float32)
    v_field = np.full((n_lat, n_lon), base_v, dtype=np.float32)

    # 如果有網格資料，用 z0/zd 修正風場
    if grid_data:
        lons = np.linspace(lng_min, lng_max, n_lon)
        lats = np.linspace(lat_max, lat_min, n_lat)  # 由上到下

        for cell in grid_data:
            cell_lon = cell.get("lon", 0)
            cell_lat = cell.get("lat", 0)
            z0 = cell.get("z0", 0.5)
            zd = cell.get("zd", 5.0)

            # 找到最近的網格索引
            i_lon = np.argmin(np.abs(lons - cell_lon))
            i_lat = np.argmin(np.abs(lats - cell_lat))

            # Log profile 修正因子
            if z0 > 0 and altitude > zd:
                try:
                    ratio = np.log((altitude - zd) / z0) / np.log((80.0 - 5.0) / 0.5)
                    ratio = np.clip(ratio, 0.3, 2.0)
                    u_field[i_lat, i_lon] *= ratio
                    v_field[i_lat, i_lon] *= ratio
                except (ValueError, ZeroDivisionError):
                    pass

    return u_field, v_field


def compute_cache_key(
    bbox: tuple[float, float, float, float],
    datetime_str: str,
    altitude: float,
    resolution: float,
) -> str:
    """計算風場 texture 快取鍵。"""
    raw = f"{bbox}|{datetime_str}|{altitude}|{resolution}"
    return hashlib.sha256(raw.encode()).hexdigest()
