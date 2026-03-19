"""Local Climate Zone (LCZ) 分類。

基於 Stewart & Oke (2012) LCZ 分類方案，使用已有的形態學指標：
- SVF (Sky View Factor)
- H/W (Height-to-Width ratio, 即 street canyon ratio)
- BCR (Building Coverage Ratio)
- mean_height (平均建築高度)

分類邏輯提取自 GeoClimate 的 LCZ 分類方法，使用純 Python 實作。

參考:
- Stewart & Oke (2012) "Local Climate Zones for Urban Temperature Studies"
- GeoClimate (https://github.com/orbisgis/geoclimate)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class LCZDefinition:
    """LCZ 類型定義與形態學指標範圍。"""

    lcz_class: int
    label: str
    label_zh: str
    svf_range: tuple[float, float]      # (min, max)
    hw_range: tuple[float, float]       # (min, max) height/width
    bcr_range: tuple[float, float]      # (min, max)
    height_range: tuple[float, float]   # (min, max) meters
    ventilation_potential: float         # 0-1 通風潛力


# LCZ 1-8 建成區類型（LCZ 9-10 為自然類型，此處略）
LCZ_DEFINITIONS: list[LCZDefinition] = [
    LCZDefinition(
        lcz_class=1, label="Compact high-rise", label_zh="密集高層",
        svf_range=(0.0, 0.4), hw_range=(2.0, 99.0),
        bcr_range=(0.5, 1.0), height_range=(25.0, 999.0),
        ventilation_potential=0.15,
    ),
    LCZDefinition(
        lcz_class=2, label="Compact mid-rise", label_zh="密集中層",
        svf_range=(0.3, 0.6), hw_range=(0.75, 2.0),
        bcr_range=(0.4, 0.7), height_range=(10.0, 25.0),
        ventilation_potential=0.25,
    ),
    LCZDefinition(
        lcz_class=3, label="Compact low-rise", label_zh="密集低層",
        svf_range=(0.2, 0.6), hw_range=(0.75, 1.5),
        bcr_range=(0.4, 0.7), height_range=(3.0, 10.0),
        ventilation_potential=0.30,
    ),
    LCZDefinition(
        lcz_class=4, label="Open high-rise", label_zh="開放高層",
        svf_range=(0.5, 1.0), hw_range=(0.75, 1.25),
        bcr_range=(0.2, 0.4), height_range=(25.0, 999.0),
        ventilation_potential=0.55,
    ),
    LCZDefinition(
        lcz_class=5, label="Open mid-rise", label_zh="開放中層",
        svf_range=(0.5, 1.0), hw_range=(0.3, 0.75),
        bcr_range=(0.2, 0.4), height_range=(10.0, 25.0),
        ventilation_potential=0.65,
    ),
    LCZDefinition(
        lcz_class=6, label="Open low-rise", label_zh="開放低層",
        svf_range=(0.6, 1.0), hw_range=(0.3, 0.75),
        bcr_range=(0.2, 0.4), height_range=(3.0, 10.0),
        ventilation_potential=0.75,
    ),
    LCZDefinition(
        lcz_class=7, label="Lightweight low-rise", label_zh="輕量低層",
        svf_range=(0.2, 0.5), hw_range=(1.0, 2.0),
        bcr_range=(0.6, 1.0), height_range=(2.0, 4.0),
        ventilation_potential=0.20,
    ),
    LCZDefinition(
        lcz_class=8, label="Large low-rise", label_zh="大型低層",
        svf_range=(0.7, 1.0), hw_range=(0.1, 0.3),
        bcr_range=(0.3, 0.5), height_range=(3.0, 10.0),
        ventilation_potential=0.60,
    ),
]

# 快速查詢
LCZ_BY_CLASS: dict[int, LCZDefinition] = {d.lcz_class: d for d in LCZ_DEFINITIONS}


def _score_lcz_match(
    svf: float, hw: float, bcr: float, height: float,
    defn: LCZDefinition,
) -> float:
    """計算一個網格與 LCZ 定義的匹配分數（0-1, 越高越匹配）。"""
    score = 0.0
    n = 0

    def _range_score(val: float, lo: float, hi: float) -> float:
        if lo <= val <= hi:
            return 1.0
        # 容許 20% 超出範圍
        margin = (hi - lo) * 0.2
        if lo - margin <= val <= hi + margin:
            return 0.5
        return 0.0

    if svf is not None and not np.isnan(svf):
        score += _range_score(svf, *defn.svf_range)
        n += 1
    if hw is not None and not np.isnan(hw):
        score += _range_score(hw, *defn.hw_range)
        n += 1
    if bcr is not None and not np.isnan(bcr):
        score += _range_score(bcr, *defn.bcr_range)
        n += 1
    if height is not None and not np.isnan(height):
        score += _range_score(height, *defn.height_range)
        n += 1

    return score / n if n > 0 else 0.0


def classify_lcz_single(
    svf: float | None = None,
    hw_ratio: float | None = None,
    bcr: float | None = None,
    mean_height: float | None = None,
) -> tuple[int, str, str, float]:
    """分類單個網格的 LCZ。

    Args:
        svf: Sky View Factor (0-1)。
        hw_ratio: Height-to-Width ratio。
        bcr: Building Coverage Ratio (0-1)。
        mean_height: 平均建築高度 (m)。

    Returns:
        (lcz_class, label, label_zh, confidence)
    """
    # 若無足夠資料，歸為 LCZ 6 (Open low-rise) 作為預設
    if all(v is None for v in [svf, hw_ratio, bcr, mean_height]):
        return (6, "Open low-rise", "開放低層", 0.0)

    # 無建築指標 → 可能是開放空間
    if (mean_height is not None and mean_height < 2) or (bcr is not None and bcr < 0.05):
        return (0, "Open land", "開放地", 0.9)

    best_class = 6
    best_score = 0.0

    for defn in LCZ_DEFINITIONS:
        score = _score_lcz_match(
            svf or 0.5,
            hw_ratio or 0.5,
            bcr or 0.2,
            mean_height or 10.0,
            defn,
        )
        if score > best_score:
            best_score = score
            best_class = defn.lcz_class

    defn = LCZ_BY_CLASS[best_class]
    return (best_class, defn.label, defn.label_zh, round(best_score, 2))


def classify_lcz_grid(
    grid_data: list[dict],
    svf_key: str = "svf",
    bcr_key: str = "bcr",
    height_key: str = "mean_height",
    hw_key: str | None = None,
) -> list[dict]:
    """批量分類 LCZ。

    Args:
        grid_data: 網格資料列表。
        svf_key, bcr_key, height_key: 欄位名稱。
        hw_key: H/W ratio 欄位名稱，None 時從 height / grid_size 估算。

    Returns:
        每個元素新增 lcz_class, lcz_label, lcz_label_zh, lcz_confidence。
    """
    results = []
    for cell in grid_data:
        svf = cell.get(svf_key)
        bcr = cell.get(bcr_key)
        height = cell.get(height_key)

        hw = cell.get(hw_key) if hw_key else None
        if hw is None and height and bcr and bcr > 0:
            # 從建築高度和 BCR 估算 H/W
            # 假設街道寬度 ≈ grid_size × (1 - sqrt(bcr))
            import math
            street_w = 100 * (1 - math.sqrt(bcr))
            hw = height / street_w if street_w > 1 else height / 10

        lcz_class, label, label_zh, confidence = classify_lcz_single(
            svf=svf, hw_ratio=hw, bcr=bcr, mean_height=height,
        )

        cell_result = dict(cell)
        cell_result["lcz_class"] = lcz_class
        cell_result["lcz_label"] = label
        cell_result["lcz_label_zh"] = label_zh
        cell_result["lcz_confidence"] = confidence
        results.append(cell_result)

    # 統計
    from collections import Counter
    counts = Counter(r["lcz_class"] for r in results)
    logger.info("LCZ distribution: %s", dict(counts))

    return results


def lcz_ventilation_potential(lcz_class: int) -> float:
    """LCZ 類型的通風潛力評分 (0-1)。

    高密集低層（LCZ 1-3, 7）= 低通風潛力。
    開放區（LCZ 4-6, 8）= 高通風潛力。
    """
    if lcz_class == 0:
        return 0.90  # 開放地
    defn = LCZ_BY_CLASS.get(lcz_class)
    return defn.ventilation_potential if defn else 0.50


# LCZ 色碼（用於地圖渲染）
LCZ_COLORS: dict[int, str] = {
    0: "#CCCCCC",   # Open land
    1: "#8C0000",   # Compact high-rise (dark red)
    2: "#D10000",   # Compact mid-rise (red)
    3: "#FF0000",   # Compact low-rise (bright red)
    4: "#BF4D00",   # Open high-rise (dark orange)
    5: "#FF6600",   # Open mid-rise (orange)
    6: "#FF9955",   # Open low-rise (light orange)
    7: "#FAEE05",   # Lightweight low-rise (yellow)
    8: "#BCBCBC",   # Large low-rise (gray)
}
