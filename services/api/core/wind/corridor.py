"""風廊分類（主廊道/次廊道）。

根據 LCP 結果與形態學指標將風廊分級。
"""

from __future__ import annotations

import logging

import geopandas as gpd
import numpy as np

from config.settings import CRS_INTERNAL

logger = logging.getLogger(__name__)


def classify_corridors(
    corridors: gpd.GeoDataFrame,
    n_primary: int = 3,
) -> gpd.GeoDataFrame:
    """將風廊分為主廊道與次廊道。

    分類標準：
    1. 成本排序：低成本路徑為主廊道
    2. 長度考量：過短的路徑降級

    Args:
        corridors: LCP 風廊 GeoDataFrame，需含 'total_cost' 欄位。
        n_primary: 主廊道數量上限。

    Returns:
        corridors 新增 'corridor_class' 欄位。
    """
    if corridors.empty:
        return corridors

    corridors = corridors.copy()
    corridors = corridors.sort_values("total_cost").reset_index(drop=True)

    # 前 n_primary 為主廊道，其餘為次廊道
    corridors["corridor_class"] = "secondary"
    corridors.iloc[:n_primary, corridors.columns.get_loc("corridor_class")] = "primary"

    # 過短路徑降級
    if "length_cells" in corridors.columns:
        min_length = corridors["length_cells"].median() * 0.3
        short_mask = corridors["length_cells"] < min_length
        corridors.loc[short_mask, "corridor_class"] = "minor"

    logger.info(
        "Corridor classification: primary=%d, secondary=%d, minor=%d",
        (corridors["corridor_class"] == "primary").sum(),
        (corridors["corridor_class"] == "secondary").sum(),
        (corridors["corridor_class"] == "minor").sum(),
    )

    return corridors


def compute_corridor_width(
    corridor: gpd.GeoDataFrame,
    grid: gpd.GeoDataFrame,
    fai_col: str = "fai_ne",
    fai_threshold: float = 0.15,
) -> gpd.GeoDataFrame:
    """估算風廊有效寬度。

    沿風廊路徑，計算兩側 FAI 低於門檻的連續網格寬度。

    Args:
        corridor: 風廊 GeoDataFrame。
        grid: 分析網格。
        fai_col: FAI 欄位名稱。
        fai_threshold: FAI 門檻。

    Returns:
        corridor 新增 'estimated_width' 欄位。
    """
    corridor = corridor.copy()

    widths = []
    for _, row in corridor.iterrows():
        # 簡化：以風廊緩衝區內低 FAI 網格面積估算寬度
        buffer = row.geometry.buffer(200)
        nearby = grid[grid.intersects(buffer)]
        if fai_col in nearby.columns:
            low_fai = nearby[nearby[fai_col] < fai_threshold]
            if len(low_fai) > 0:
                width = low_fai.geometry.area.sum() / row.geometry.length
                widths.append(width)
            else:
                widths.append(0.0)
        else:
            widths.append(0.0)

    corridor["estimated_width"] = widths

    return corridor


def merge_nearby_corridors(
    corridors: gpd.GeoDataFrame,
    merge_distance: float = 100.0,
) -> gpd.GeoDataFrame:
    """合併相近的風廊。

    Args:
        corridors: 風廊 GeoDataFrame。
        merge_distance: 合併距離門檻（公尺）。

    Returns:
        合併後的風廊 GeoDataFrame。
    """
    if len(corridors) <= 1:
        return corridors

    corridors = corridors.copy()
    buffered = corridors.geometry.buffer(merge_distance)

    # 找出重疊的風廊群組
    groups = []
    assigned = set()

    for i in range(len(corridors)):
        if i in assigned:
            continue
        group = {i}
        for j in range(i + 1, len(corridors)):
            if j not in assigned and buffered.iloc[i].intersects(buffered.iloc[j]):
                group.add(j)
                assigned.add(j)
        groups.append(group)
        assigned.add(i)

    # 每個群組保留成本最低的
    keep_indices = []
    for group in groups:
        best = min(group, key=lambda idx: corridors.iloc[idx]["total_cost"])
        keep_indices.append(best)

    result = corridors.iloc[keep_indices].reset_index(drop=True)
    logger.info("Merged %d corridors to %d", len(corridors), len(result))
    return result
