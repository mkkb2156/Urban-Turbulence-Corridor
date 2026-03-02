"""風險等級分類器模組測試。

測試 load_risk_thresholds()、classify_wind_risk()、classify_multi_height_risk()，
確認四級風險分類（green/yellow/red/black）、邊界值處理、
缺少風速欄位錯誤以及多高度分類。
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import box

from src.risk.classifier import (
    classify_multi_height_risk,
    classify_wind_risk,
    load_risk_thresholds,
)


@pytest.fixture
def risk_thresholds() -> dict:
    """直接定義的風險門檻（避免依賴 YAML 檔案）。"""
    return {
        "green": {
            "max_wind_speed": 5.0,
            "label": "安全",
            "color": "#2ecc71",
        },
        "yellow": {
            "max_wind_speed": 8.0,
            "label": "注意",
            "color": "#f1c40f",
        },
        "red": {
            "max_wind_speed": 12.0,
            "label": "危險",
            "color": "#e74c3c",
        },
        "black": {
            "max_wind_speed": None,
            "label": "極度危險",
            "color": "#2c3e50",
        },
    }


def _make_wind_grid(wind_speeds: list[float]) -> gpd.GeoDataFrame:
    """建立含風速的測試網格。"""
    n = len(wind_speeds)
    geoms = [box(i * 100, 0, (i + 1) * 100, 100) for i in range(n)]
    return gpd.GeoDataFrame(
        {
            "grid_id": [f"cell_{i:03d}" for i in range(n)],
            "wind_50m": wind_speeds,
        },
        geometry=geoms,
        crs="EPSG:3826",
    )


class TestLoadRiskThresholds:
    """load_risk_thresholds() 功能測試。"""

    def test_loads_from_yaml(self):
        """應能從 YAML 檔案載入風險門檻。"""
        thresholds = load_risk_thresholds()
        assert "green" in thresholds
        assert "yellow" in thresholds
        assert "red" in thresholds
        assert "black" in thresholds

    def test_green_threshold(self):
        """green 門檻應為 5.0 m/s。"""
        thresholds = load_risk_thresholds()
        assert thresholds["green"]["max_wind_speed"] == 5.0

    def test_yellow_threshold(self):
        """yellow 門檻應為 8.0 m/s。"""
        thresholds = load_risk_thresholds()
        assert thresholds["yellow"]["max_wind_speed"] == 8.0

    def test_red_threshold(self):
        """red 門檻應為 12.0 m/s。"""
        thresholds = load_risk_thresholds()
        assert thresholds["red"]["max_wind_speed"] == 12.0

    def test_invalid_path_raises_error(self):
        """無效路徑應拋出錯誤。"""
        with pytest.raises(FileNotFoundError):
            load_risk_thresholds("/nonexistent/path/risk.yaml")


class TestClassifyWindRisk:
    """classify_wind_risk() 功能測試。"""

    def test_green_level(self, risk_thresholds):
        """風速 <= 5 m/s 應分類為 green。"""
        grid = _make_wind_grid([2.0, 4.5, 5.0])
        result = classify_wind_risk(grid, thresholds=risk_thresholds)
        assert all(result["risk_level"] == "green")

    def test_yellow_level(self, risk_thresholds):
        """5 < 風速 <= 8 m/s 應分類為 yellow。"""
        grid = _make_wind_grid([6.0, 7.5, 8.0])
        result = classify_wind_risk(grid, thresholds=risk_thresholds)
        assert all(result["risk_level"] == "yellow")

    def test_red_level(self, risk_thresholds):
        """8 < 風速 <= 12 m/s 應分類為 red。"""
        grid = _make_wind_grid([9.0, 10.5, 12.0])
        result = classify_wind_risk(grid, thresholds=risk_thresholds)
        assert all(result["risk_level"] == "red")

    def test_black_level(self, risk_thresholds):
        """風速 > 12 m/s 應分類為 black。"""
        grid = _make_wind_grid([13.0, 20.0, 50.0])
        result = classify_wind_risk(grid, thresholds=risk_thresholds)
        assert all(result["risk_level"] == "black")

    def test_edge_case_exactly_5(self, risk_thresholds):
        """風速恰好 5.0 m/s 應為 green。"""
        grid = _make_wind_grid([5.0])
        result = classify_wind_risk(grid, thresholds=risk_thresholds)
        assert result["risk_level"].iloc[0] == "green"

    def test_edge_case_exactly_8(self, risk_thresholds):
        """風速恰好 8.0 m/s 應為 yellow。"""
        grid = _make_wind_grid([8.0])
        result = classify_wind_risk(grid, thresholds=risk_thresholds)
        assert result["risk_level"].iloc[0] == "yellow"

    def test_edge_case_exactly_12(self, risk_thresholds):
        """風速恰好 12.0 m/s 應為 red。"""
        grid = _make_wind_grid([12.0])
        result = classify_wind_risk(grid, thresholds=risk_thresholds)
        assert result["risk_level"].iloc[0] == "red"

    def test_mixed_risk_levels(self, risk_thresholds):
        """混合風速應產生不同風險等級。"""
        grid = _make_wind_grid([3.0, 6.0, 10.0, 15.0])
        result = classify_wind_risk(grid, thresholds=risk_thresholds)
        levels = result["risk_level"].tolist()
        assert levels == ["green", "yellow", "red", "black"]

    def test_missing_wind_column_raises_error(self, risk_thresholds):
        """缺少風速欄位應拋出 ValueError。"""
        grid = gpd.GeoDataFrame(
            {"grid_id": ["cell_000"]},
            geometry=[box(0, 0, 100, 100)],
            crs="EPSG:3826",
        )
        with pytest.raises(ValueError, match="wind_50m"):
            classify_wind_risk(grid, thresholds=risk_thresholds)

    def test_output_columns(self, risk_thresholds):
        """應新增 risk_level、risk_label、risk_color 欄位。"""
        grid = _make_wind_grid([5.0])
        result = classify_wind_risk(grid, thresholds=risk_thresholds)
        assert "risk_level" in result.columns
        assert "risk_label" in result.columns
        assert "risk_color" in result.columns

    def test_risk_label_matches_level(self, risk_thresholds):
        """risk_label 應與門檻定義的 label 一致。"""
        grid = _make_wind_grid([3.0])
        result = classify_wind_risk(grid, thresholds=risk_thresholds)
        assert result["risk_label"].iloc[0] == "安全"

    def test_risk_color_matches_level(self, risk_thresholds):
        """risk_color 應與門檻定義的 color 一致。"""
        grid = _make_wind_grid([3.0])
        result = classify_wind_risk(grid, thresholds=risk_thresholds)
        assert result["risk_color"].iloc[0] == "#2ecc71"

    def test_custom_wind_column(self, risk_thresholds):
        """支援自訂風速欄位名稱。"""
        grid = gpd.GeoDataFrame(
            {"grid_id": ["cell_000"], "wind_80m": [7.0]},
            geometry=[box(0, 0, 100, 100)],
            crs="EPSG:3826",
        )
        result = classify_wind_risk(
            grid, wind_col="wind_80m", thresholds=risk_thresholds
        )
        assert result["risk_level"].iloc[0] == "yellow"

    def test_zero_wind_speed(self, risk_thresholds):
        """風速為 0 應分類為 green。"""
        grid = _make_wind_grid([0.0])
        result = classify_wind_risk(grid, thresholds=risk_thresholds)
        assert result["risk_level"].iloc[0] == "green"


class TestClassifyMultiHeightRisk:
    """classify_multi_height_risk() 功能測試。"""

    def test_multi_height_columns(self, risk_thresholds):
        """應為每個高度建立帶後綴的 risk 欄位。"""
        grid = gpd.GeoDataFrame(
            {
                "grid_id": ["cell_000"],
                "wind_50m": [4.0],
                "wind_80m": [7.0],
                "wind_120m": [11.0],
            },
            geometry=[box(0, 0, 100, 100)],
            crs="EPSG:3826",
        )
        result = classify_multi_height_risk(
            grid, heights=[50, 80, 120], thresholds=risk_thresholds
        )
        assert "risk_level_50m" in result.columns
        assert "risk_level_80m" in result.columns
        assert "risk_level_120m" in result.columns

    def test_different_heights_different_risks(self, risk_thresholds):
        """不同高度可能有不同風險等級。"""
        grid = gpd.GeoDataFrame(
            {
                "grid_id": ["cell_000"],
                "wind_50m": [3.0],   # green
                "wind_80m": [7.0],   # yellow
                "wind_120m": [15.0], # black
            },
            geometry=[box(0, 0, 100, 100)],
            crs="EPSG:3826",
        )
        result = classify_multi_height_risk(
            grid, heights=[50, 80, 120], thresholds=risk_thresholds
        )
        assert result["risk_level_50m"].iloc[0] == "green"
        assert result["risk_level_80m"].iloc[0] == "yellow"
        assert result["risk_level_120m"].iloc[0] == "black"

    def test_missing_height_column_skipped(self, risk_thresholds):
        """缺少某高度的風速欄位時應跳過。"""
        grid = gpd.GeoDataFrame(
            {
                "grid_id": ["cell_000"],
                "wind_50m": [4.0],
                # 缺少 wind_80m 和 wind_120m
            },
            geometry=[box(0, 0, 100, 100)],
            crs="EPSG:3826",
        )
        result = classify_multi_height_risk(
            grid, heights=[50, 80, 120], thresholds=risk_thresholds
        )
        assert "risk_level_50m" in result.columns
        # 80m 和 120m 因沒有對應風速欄位不會產生 risk 欄位
        assert "risk_level_80m" not in result.columns
