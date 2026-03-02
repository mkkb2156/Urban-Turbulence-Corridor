"""對數風速剖面測試。"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import box

from src.wind.log_profile import (
    compute_wind_speed_ratio,
    downscale_wind_to_grid,
    estimate_friction_velocity,
    log_wind_profile,
)


class TestLogWindProfile:
    """對數風速剖面公式測試。"""

    def test_basic_profile(self):
        """基本對數剖面計算。"""
        # 典型都市環境：z₀=1.0m, zd=10m
        speed = log_wind_profile(z=50, u_star=1.0, z0=1.0, zd=10)
        assert speed > 0
        assert speed < 20  # 合理範圍

    def test_height_monotonic(self):
        """風速應隨高度單調遞增。"""
        speeds = [
            log_wind_profile(z=z, u_star=1.0, z0=1.0, zd=10)
            for z in [30, 50, 80, 120]
        ]
        for i in range(len(speeds) - 1):
            assert speeds[i] < speeds[i + 1]

    def test_roughness_effect(self):
        """較高粗糙度應降低風速。"""
        speed_smooth = log_wind_profile(z=50, u_star=1.0, z0=0.03, zd=0)
        speed_rough = log_wind_profile(z=50, u_star=1.0, z0=2.0, zd=15)
        assert speed_smooth > speed_rough

    def test_below_displacement_height(self):
        """高度低於零平面位移時應拋出錯誤。"""
        with pytest.raises(ValueError):
            log_wind_profile(z=5, u_star=1.0, z0=1.0, zd=10)

    def test_zero_roughness(self):
        """零粗糙度應拋出錯誤。"""
        with pytest.raises(ValueError):
            log_wind_profile(z=50, u_star=1.0, z0=0.0, zd=0)

    def test_von_karman_constant(self):
        """使用自定義 κ 值。"""
        speed_default = log_wind_profile(z=50, u_star=1.0, z0=1.0, zd=0)
        speed_custom = log_wind_profile(z=50, u_star=1.0, z0=1.0, zd=0, kappa=0.41)
        assert speed_default != speed_custom


class TestFrictionVelocity:
    """摩擦速度反推測試。"""

    def test_roundtrip(self):
        """u* 反推後再計算應得回原始風速。"""
        u_ref = 5.0
        z_ref = 10.0
        z0, zd = 0.5, 3.0

        u_star = estimate_friction_velocity(u_ref, z_ref, z0, zd)
        u_check = log_wind_profile(z_ref, u_star, z0, zd)
        assert abs(u_check - u_ref) < 0.01

    def test_positive_u_star(self):
        """摩擦速度應為正值。"""
        u_star = estimate_friction_velocity(5.0, 10.0, 1.0, 3.0)
        assert u_star > 0

    def test_high_displacement(self):
        """零平面位移接近參考高度時應自動調整。"""
        u_star = estimate_friction_velocity(5.0, 10.0, 1.0, 9.0)
        assert u_star > 0


class TestDownscaleToGrid:
    """網格降尺度測試。"""

    def test_basic_downscale(self):
        """基本網格降尺度。"""
        grid = gpd.GeoDataFrame(
            {
                "grid_id": ["test_000_000", "test_000_001"],
                "row": [0, 0],
                "col": [0, 1],
                "z0": [0.5, 2.0],
                "zd": [3.0, 15.0],
            },
            geometry=[box(0, 0, 100, 100), box(100, 0, 200, 100)],
            crs="EPSG:3826",
        )

        result = downscale_wind_to_grid(grid, reference_speed=6.0)
        assert "wind_50m" in result.columns
        assert "wind_80m" in result.columns
        assert "wind_120m" in result.columns
        assert all(result["wind_50m"] >= 0)

    def test_smooth_vs_rough(self):
        """光滑地表風速應高於粗糙地表。"""
        grid = gpd.GeoDataFrame(
            {
                "grid_id": ["smooth", "rough"],
                "row": [0, 0],
                "col": [0, 1],
                "z0": [0.03, 2.0],
                "zd": [0.0, 15.0],
            },
            geometry=[box(0, 0, 100, 100), box(100, 0, 200, 100)],
            crs="EPSG:3826",
        )

        result = downscale_wind_to_grid(grid, reference_speed=6.0, target_heights=[50.0])
        smooth = result[result["grid_id"] == "smooth"]["wind_50m"].values[0]
        rough = result[result["grid_id"] == "rough"]["wind_50m"].values[0]
        assert smooth > rough


class TestWindSpeedRatio:
    """風速比測試。"""

    def test_ratio_range(self):
        """風速比應在合理範圍。"""
        grid = gpd.GeoDataFrame(
            {
                "grid_id": ["test"],
                "row": [0],
                "col": [0],
                "z0": [1.0],
                "zd": [5.0],
            },
            geometry=[box(0, 0, 100, 100)],
            crs="EPSG:3826",
        )

        result = compute_wind_speed_ratio(grid, target_height=50.0)
        assert "wind_speed_ratio" in result.columns
        ratio = result["wind_speed_ratio"].values[0]
        assert 0 < ratio < 10  # 合理範圍
