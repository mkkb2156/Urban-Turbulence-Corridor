"""FastAPI 端點測試。

測試 /health、/api/v1/wind、/api/v1/risk 端點，
確認回應狀態碼、Pydantic 模型驗證以及輸入範圍檢查。
使用 fastapi.testclient.TestClient 進行同步測試。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

# raise_server_exceptions=False 讓測試不因後端缺少資料庫而拋出例外，
# 而是回傳 500 狀態碼，使我們能正確測試 Pydantic 驗證行為。
client = TestClient(app, raise_server_exceptions=False)


class TestHealthEndpoint:
    """GET /health 端點測試。"""

    def test_health_returns_200(self):
        """健康檢查應回傳 200。"""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_body(self):
        """健康檢查回應應包含 status、version、city。"""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "city" in data

    def test_health_default_city(self):
        """預設城市應為 taipei。"""
        response = client.get("/health")
        data = response.json()
        assert data["city"] == "taipei"

    def test_health_version_format(self):
        """版本格式應為 x.y.z。"""
        response = client.get("/health")
        data = response.json()
        parts = data["version"].split(".")
        assert len(parts) == 3


class TestWindEndpoint:
    """POST /api/v1/wind 端點測試。"""

    def test_wind_validates_lon_range(self):
        """經度超出台灣範圍應回傳 422。"""
        response = client.post("/api/v1/wind", json={
            "lon": 100.0,  # 太西邊，不在 119-123 範圍
            "lat": 25.0,
            "height": 50.0,
        })
        assert response.status_code == 422

    def test_wind_validates_lat_range(self):
        """緯度超出台灣範圍應回傳 422。"""
        response = client.post("/api/v1/wind", json={
            "lon": 121.5,
            "lat": 30.0,  # 太北，不在 21-26 範圍
            "height": 50.0,
        })
        assert response.status_code == 422

    def test_wind_validates_lon_too_high(self):
        """經度超過上限應回傳 422。"""
        response = client.post("/api/v1/wind", json={
            "lon": 125.0,  # > 123
            "lat": 25.0,
            "height": 50.0,
        })
        assert response.status_code == 422

    def test_wind_validates_lat_too_low(self):
        """緯度低於下限應回傳 422。"""
        response = client.post("/api/v1/wind", json={
            "lon": 121.5,
            "lat": 20.0,  # < 21
            "height": 50.0,
        })
        assert response.status_code == 422

    def test_wind_missing_required_field(self):
        """缺少必要欄位應回傳 422。"""
        response = client.post("/api/v1/wind", json={
            "lon": 121.5,
            # 缺少 lat
        })
        assert response.status_code == 422

    def test_wind_empty_body(self):
        """空請求體應回傳 422。"""
        response = client.post("/api/v1/wind", json={})
        assert response.status_code == 422

    def test_wind_invalid_type(self):
        """非數值型別應回傳 422。"""
        response = client.post("/api/v1/wind", json={
            "lon": "not_a_number",
            "lat": 25.0,
        })
        assert response.status_code == 422

    def test_wind_height_validation(self):
        """飛行高度超出範圍應回傳 422。"""
        response = client.post("/api/v1/wind", json={
            "lon": 121.5,
            "lat": 25.0,
            "height": 600.0,  # > 500
        })
        assert response.status_code == 422

    def test_wind_negative_height(self):
        """負高度應回傳 422。"""
        response = client.post("/api/v1/wind", json={
            "lon": 121.5,
            "lat": 25.0,
            "height": -10.0,
        })
        assert response.status_code == 422

    def test_wind_boundary_lon_min(self):
        """經度下限（119）應為有效值，不應觸發 Pydantic 422 驗證錯誤。"""
        response = client.post("/api/v1/wind", json={
            "lon": 119.0,
            "lat": 25.0,
        })
        # 驗證通過（非 422），可能是 500（資料庫不可用）或 404
        assert response.status_code in (200, 404, 500)

    def test_wind_boundary_lon_max(self):
        """經度上限（123）應為有效值，不應觸發 Pydantic 422 驗證錯誤。"""
        response = client.post("/api/v1/wind", json={
            "lon": 123.0,
            "lat": 25.0,
        })
        assert response.status_code in (200, 404, 500)


class TestRiskEndpoint:
    """POST /api/v1/risk 端點測試。"""

    def test_risk_validates_lon_range(self):
        """經度超出範圍應回傳 422。"""
        response = client.post("/api/v1/risk", json={
            "lon": 100.0,
            "lat": 25.0,
        })
        assert response.status_code == 422

    def test_risk_validates_lat_range(self):
        """緯度超出範圍應回傳 422。"""
        response = client.post("/api/v1/risk", json={
            "lon": 121.5,
            "lat": 28.0,
        })
        assert response.status_code == 422

    def test_risk_missing_required_field(self):
        """缺少必要欄位應回傳 422。"""
        response = client.post("/api/v1/risk", json={
            "lat": 25.0,
        })
        assert response.status_code == 422

    def test_risk_empty_body(self):
        """空請求體應回傳 422。"""
        response = client.post("/api/v1/risk", json={})
        assert response.status_code == 422

    def test_risk_with_drone_id_validates(self):
        """附帶 drone_id 的請求在格式正確時不應因驗證失敗。"""
        response = client.post("/api/v1/risk", json={
            "lon": 121.5,
            "lat": 25.0,
            "drone_id": "dji_mini_4_pro",
        })
        # 驗證通過（非 422），可能因無資料庫而回傳 500
        assert response.status_code in (200, 404, 500)

    def test_risk_height_default_50(self):
        """未指定高度時預設為 50m，不應驗證失敗。"""
        response = client.post("/api/v1/risk", json={
            "lon": 121.5,
            "lat": 25.0,
        })
        assert response.status_code in (200, 404, 500)


class TestPydanticSchemaValidation:
    """Pydantic 模型驗證測試。"""

    def test_point_query_valid(self):
        """有效 PointQuery 不應驗證失敗。"""
        response = client.post("/api/v1/wind", json={
            "lon": 121.5,
            "lat": 25.0,
            "height": 80.0,
        })
        # 驗證通過（非 422），可能因無資料庫而回傳 500
        assert response.status_code in (200, 404, 500)

    def test_point_query_extra_fields_ignored(self):
        """多餘欄位應被忽略（不影響驗證）。"""
        response = client.post("/api/v1/wind", json={
            "lon": 121.5,
            "lat": 25.0,
            "extra_field": "ignored",
        })
        assert response.status_code in (200, 404, 500)

    def test_multiple_validation_errors(self):
        """多個欄位錯誤應一併回傳。"""
        response = client.post("/api/v1/wind", json={
            "lon": 200.0,  # 超出範圍
            "lat": 50.0,   # 超出範圍
            "height": -5.0, # 負值
        })
        assert response.status_code == 422
        data = response.json()
        # FastAPI 回傳 validation error 列表
        assert "detail" in data
        assert len(data["detail"]) >= 2  # 至少兩個驗證錯誤
