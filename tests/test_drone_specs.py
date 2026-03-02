"""無人機規格與可飛性評估模組測試。

測試 get_drone_spec()、check_flyability()，確認規格查詢、
未知無人機錯誤處理、安全裕度計算以及邊界風速判定。
"""

from __future__ import annotations

import pytest

from src.risk.drone_specs import (
    DRONE_DATABASE,
    DroneSpec,
    check_flyability,
    get_drone_spec,
)


class TestGetDroneSpec:
    """get_drone_spec() 功能測試。"""

    def test_known_drone_found(self):
        """已知無人機 ID 應回傳 DroneSpec 物件。"""
        spec = get_drone_spec("dji_mini_4_pro")
        assert isinstance(spec, DroneSpec)
        assert spec.name == "DJI Mini 4 Pro"

    def test_all_drones_in_database(self):
        """資料庫中所有無人機都應可查詢。"""
        for drone_id in DRONE_DATABASE:
            spec = get_drone_spec(drone_id)
            assert spec is not None
            assert isinstance(spec, DroneSpec)

    def test_unknown_drone_raises_error(self):
        """未知無人機 ID 應拋出 ValueError。"""
        with pytest.raises(ValueError, match="Unknown drone"):
            get_drone_spec("nonexistent_drone_xyz")

    def test_error_message_includes_available(self):
        """錯誤訊息應包含可用的無人機列表。"""
        with pytest.raises(ValueError, match="Available"):
            get_drone_spec("bad_id")

    def test_dji_mini_4_pro_specs(self):
        """DJI Mini 4 Pro 規格驗證。"""
        spec = get_drone_spec("dji_mini_4_pro")
        assert spec.category == "consumer"
        assert spec.max_wind_tolerance == 10.7
        assert spec.weight_kg == 0.249

    def test_dji_matrice_350_specs(self):
        """DJI Matrice 350 RTK 規格驗證。"""
        spec = get_drone_spec("dji_matrice_350")
        assert spec.category == "industrial"
        assert spec.max_wind_tolerance == 15.0
        assert spec.weight_kg == 6.47

    def test_dji_air_3_specs(self):
        """DJI Air 3 規格驗證。"""
        spec = get_drone_spec("dji_air_3")
        assert spec.category == "consumer"
        assert spec.max_wind_tolerance == 12.0

    def test_all_drones_have_positive_tolerance(self):
        """所有無人機最大抗風能力應為正值。"""
        for drone_id in DRONE_DATABASE:
            spec = get_drone_spec(drone_id)
            assert spec.max_wind_tolerance > 0

    def test_all_drones_have_positive_weight(self):
        """所有無人機重量應為正值。"""
        for drone_id in DRONE_DATABASE:
            spec = get_drone_spec(drone_id)
            assert spec.weight_kg > 0

    def test_all_drones_have_category(self):
        """所有無人機應有分類。"""
        valid_categories = {"consumer", "professional", "industrial"}
        for drone_id in DRONE_DATABASE:
            spec = get_drone_spec(drone_id)
            assert spec.category in valid_categories


class TestCheckFlyability:
    """check_flyability() 功能測試。"""

    def test_safe_wind_flyable(self):
        """低風速應可安全飛行。"""
        result = check_flyability(3.0, "dji_mini_4_pro")
        assert result["flyable"] is True
        assert result["margin"] > 0

    def test_high_wind_not_flyable(self):
        """高風速應不可飛行。"""
        result = check_flyability(15.0, "dji_mini_4_pro")
        assert result["flyable"] is False
        assert result["margin"] < 0

    def test_safety_margin_default_0_7(self):
        """預設安全裕度為 0.7。"""
        # DJI Mini 4 Pro: max_tolerance = 10.7, safe_limit = 10.7 * 0.7 = 7.49
        result = check_flyability(7.0, "dji_mini_4_pro")
        assert result["safe_limit"] == pytest.approx(10.7 * 0.7, abs=0.01)
        assert result["flyable"] is True

    def test_custom_safety_margin(self):
        """自訂安全裕度。"""
        # 安全裕度 0.5: safe_limit = 10.7 * 0.5 = 5.35
        result = check_flyability(5.0, "dji_mini_4_pro", safety_margin=0.5)
        assert result["safe_limit"] == pytest.approx(5.35, abs=0.01)
        assert result["flyable"] is True

    def test_at_safe_limit_still_flyable(self):
        """風速恰好等於安全限制時應可飛行。"""
        spec = get_drone_spec("dji_mini_4_pro")
        safe_limit = spec.max_wind_tolerance * 0.7
        result = check_flyability(safe_limit, "dji_mini_4_pro")
        assert result["flyable"] is True

    def test_just_above_safe_limit_not_flyable(self):
        """風速剛超過安全限制時不可飛行。"""
        spec = get_drone_spec("dji_mini_4_pro")
        safe_limit = spec.max_wind_tolerance * 0.7
        result = check_flyability(safe_limit + 0.01, "dji_mini_4_pro")
        assert result["flyable"] is False

    def test_between_safe_and_max_recommendation(self):
        """風速在安全限制與最大容忍之間應建議謹慎。"""
        spec = get_drone_spec("dji_mini_4_pro")
        safe_limit = spec.max_wind_tolerance * 0.7
        wind = (safe_limit + spec.max_wind_tolerance) / 2
        result = check_flyability(wind, "dji_mini_4_pro")
        assert "謹慎" in result["recommendation"]

    def test_above_max_tolerance_recommendation(self):
        """風速超過最大容忍時應建議禁飛。"""
        result = check_flyability(20.0, "dji_mini_4_pro")
        assert "禁止" in result["recommendation"]

    def test_unknown_drone_raises_error(self):
        """未知無人機 ID 應拋出 ValueError。"""
        with pytest.raises(ValueError, match="Unknown drone"):
            check_flyability(5.0, "nonexistent_drone")

    def test_zero_wind_speed(self):
        """零風速應可飛行。"""
        result = check_flyability(0.0, "dji_mini_4_pro")
        assert result["flyable"] is True
        assert result["margin"] > 0

    def test_result_contains_all_keys(self):
        """回傳字典應包含所有必要鍵。"""
        result = check_flyability(5.0, "dji_mini_4_pro")
        expected_keys = {
            "flyable", "wind_speed", "safe_limit",
            "max_tolerance", "margin", "recommendation", "drone_name",
        }
        assert expected_keys == set(result.keys())

    def test_result_wind_speed_echo(self):
        """回傳字典中的 wind_speed 應與輸入一致。"""
        result = check_flyability(7.5, "dji_air_3")
        assert result["wind_speed"] == 7.5

    def test_result_drone_name(self):
        """回傳字典中的 drone_name 應正確。"""
        result = check_flyability(5.0, "dji_mavic_3")
        assert result["drone_name"] == "DJI Mavic 3"

    def test_industrial_drone_higher_tolerance(self):
        """工業級無人機在高風速下仍可飛行。"""
        # DJI Matrice 350: max_tolerance = 15.0, safe_limit = 10.5
        result_consumer = check_flyability(10.0, "dji_mini_4_pro")
        result_industrial = check_flyability(10.0, "dji_matrice_350")
        assert result_consumer["flyable"] is False  # 10.0 > 7.49
        assert result_industrial["flyable"] is True  # 10.0 < 10.5
