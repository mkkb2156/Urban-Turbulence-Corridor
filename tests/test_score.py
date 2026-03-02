"""綜合風險分數計算模組測試。

測試 normalize_0_1()、compute_risk_score()，
確認分數範圍、正規化行為、權重敏感性以及部分欄位處理。
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import box

from src.risk.score import DEFAULT_WEIGHTS, compute_risk_score, normalize_0_1


class TestNormalize01:
    """normalize_0_1() 功能測試。"""

    def test_basic_normalization(self):
        """基本正規化：最小值 -> 0，最大值 -> 1。"""
        values = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        result = normalize_0_1(values)
        assert result[0] == pytest.approx(0.0)
        assert result[-1] == pytest.approx(1.0)

    def test_constant_values_return_zero(self):
        """所有值相同時應回傳全零陣列。"""
        values = np.array([5.0, 5.0, 5.0])
        result = normalize_0_1(values)
        assert all(result == 0.0)

    def test_output_range(self):
        """正規化後值應在 [0, 1] 範圍。"""
        values = np.array([1, 5, 10, 100, 1000])
        result = normalize_0_1(values.astype(float))
        assert result.min() >= 0.0
        assert result.max() <= 1.0

    def test_two_values(self):
        """兩個不同值應正規化為 0 和 1。"""
        values = np.array([3.0, 7.0])
        result = normalize_0_1(values)
        assert result[0] == pytest.approx(0.0)
        assert result[1] == pytest.approx(1.0)

    def test_negative_values(self):
        """負值也應正確正規化。"""
        values = np.array([-10.0, 0.0, 10.0])
        result = normalize_0_1(values)
        assert result[0] == pytest.approx(0.0)
        assert result[1] == pytest.approx(0.5)
        assert result[2] == pytest.approx(1.0)

    def test_single_value_returns_zero(self):
        """單一值應回傳 0。"""
        values = np.array([42.0])
        result = normalize_0_1(values)
        assert result[0] == 0.0

    def test_preserves_order(self):
        """正規化應保持原始排序。"""
        values = np.array([1.0, 3.0, 2.0, 5.0, 4.0])
        result = normalize_0_1(values)
        for i in range(len(values)):
            for j in range(len(values)):
                if values[i] < values[j]:
                    assert result[i] < result[j]


def _make_full_grid(
    wind_speeds: list[float],
    fai_values: list[float] | None = None,
    is_corridor: list[bool] | None = None,
    hw_ratios: list[float] | None = None,
    svf_values: list[float] | None = None,
) -> gpd.GeoDataFrame:
    """建立含完整指標的測試網格。"""
    n = len(wind_speeds)
    data = {
        "grid_id": [f"cell_{i:03d}" for i in range(n)],
        "wind_50m": wind_speeds,
    }
    if fai_values is not None:
        data["fai_ne"] = fai_values
    if is_corridor is not None:
        data["is_corridor"] = is_corridor
    if hw_ratios is not None:
        data["mean_hw_ratio"] = hw_ratios
    if svf_values is not None:
        data["svf"] = svf_values

    geoms = [box(i * 100, 0, (i + 1) * 100, 100) for i in range(n)]
    return gpd.GeoDataFrame(data, geometry=geoms, crs="EPSG:3826")


class TestComputeRiskScore:
    """compute_risk_score() 功能測試。"""

    def test_score_in_0_100_range(self):
        """風險分數應在 [0, 100] 範圍。"""
        grid = _make_full_grid(
            wind_speeds=[2.0, 5.0, 10.0, 15.0],
            fai_values=[0.1, 0.3, 0.5, 0.8],
            is_corridor=[False, False, True, True],
            hw_ratios=[0.3, 1.0, 2.5, 4.0],
            svf_values=[0.9, 0.7, 0.4, 0.2],
        )
        result = compute_risk_score(grid)
        assert "risk_score" in result.columns
        assert result["risk_score"].min() >= 0.0
        assert result["risk_score"].max() <= 100.0

    def test_higher_wind_higher_score(self):
        """較高風速應產生較高風險分數。"""
        grid = _make_full_grid(
            wind_speeds=[2.0, 15.0],
            fai_values=[0.1, 0.1],
            svf_values=[0.8, 0.8],
        )
        result = compute_risk_score(grid)
        low_score = result[result["grid_id"] == "cell_000"]["risk_score"].values[0]
        high_score = result[result["grid_id"] == "cell_001"]["risk_score"].values[0]
        assert high_score > low_score

    def test_corridor_increases_score(self):
        """位於風廊上的網格風險分數應較高。"""
        grid = _make_full_grid(
            wind_speeds=[8.0, 8.0],
            fai_values=[0.2, 0.2],
            is_corridor=[False, True],
            svf_values=[0.6, 0.6],
        )
        result = compute_risk_score(grid)
        no_corridor = result[result["grid_id"] == "cell_000"]["risk_score"].values[0]
        on_corridor = result[result["grid_id"] == "cell_001"]["risk_score"].values[0]
        assert on_corridor > no_corridor

    def test_partial_columns_wind_only(self):
        """只有風速欄位時也能計算分數。"""
        grid = _make_full_grid(wind_speeds=[3.0, 8.0, 12.0])
        result = compute_risk_score(grid)
        assert "risk_score" in result.columns
        # 分數應基於風速排序
        scores = result["risk_score"].tolist()
        assert scores == sorted(scores)

    def test_partial_columns_no_wind(self):
        """缺少風速欄位時分數僅基於其他指標。"""
        grid = gpd.GeoDataFrame(
            {
                "grid_id": ["cell_000", "cell_001"],
                "fai_ne": [0.1, 0.5],
                "svf": [0.9, 0.3],
            },
            geometry=[box(0, 0, 100, 100), box(100, 0, 200, 100)],
            crs="EPSG:3826",
        )
        result = compute_risk_score(grid)
        assert "risk_score" in result.columns

    def test_custom_weights(self):
        """自訂權重應影響分數計算。"""
        grid = _make_full_grid(
            wind_speeds=[10.0, 10.0],
            fai_values=[0.1, 0.8],
        )
        # 將 FAI 權重設為很高
        high_fai_weights = {
            "wind_speed": 0.1,
            "fai": 0.8,
            "corridor": 0.05,
            "canyon": 0.025,
            "svf": 0.025,
        }
        result = compute_risk_score(grid, weights=high_fai_weights)
        low_fai = result[result["grid_id"] == "cell_000"]["risk_score"].values[0]
        high_fai = result[result["grid_id"] == "cell_001"]["risk_score"].values[0]
        # 高 FAI 權重 + 高 FAI 值 => 更高分數
        assert high_fai > low_fai

    def test_low_svf_increases_score(self):
        """低 SVF（高遮蔽）應增加風險分數。"""
        grid = _make_full_grid(
            wind_speeds=[8.0, 8.0],
            fai_values=[0.2, 0.2],
            svf_values=[0.9, 0.2],  # 一個開闊，一個遮蔽
        )
        result = compute_risk_score(grid)
        open_score = result[result["grid_id"] == "cell_000"]["risk_score"].values[0]
        shaded_score = result[result["grid_id"] == "cell_001"]["risk_score"].values[0]
        assert shaded_score > open_score

    def test_all_zeros_score_zero(self):
        """所有指標為最低時分數應為 0。"""
        grid = _make_full_grid(
            wind_speeds=[0.0, 0.0],
            fai_values=[0.0, 0.0],
            is_corridor=[False, False],
            hw_ratios=[0.0, 0.0],
            svf_values=[1.0, 1.0],  # SVF 1 = 開闊 = 低風險
        )
        result = compute_risk_score(grid)
        assert all(result["risk_score"] == 0.0)

    def test_default_weights_sum_to_one(self):
        """預設權重總和應為 1.0。"""
        total = sum(DEFAULT_WEIGHTS.values())
        assert total == pytest.approx(1.0, abs=0.001)

    def test_score_rounded_to_one_decimal(self):
        """風險分數應四捨五入至小數點後一位。"""
        grid = _make_full_grid(
            wind_speeds=[3.33, 7.77, 11.11],
            fai_values=[0.123, 0.456, 0.789],
        )
        result = compute_risk_score(grid)
        for score in result["risk_score"]:
            assert score == round(score, 1)

    def test_preserves_grid_columns(self):
        """計算後應保留原始欄位。"""
        grid = _make_full_grid(
            wind_speeds=[5.0],
            fai_values=[0.3],
        )
        result = compute_risk_score(grid)
        assert "grid_id" in result.columns
        assert "wind_50m" in result.columns
        assert "fai_ne" in result.columns
