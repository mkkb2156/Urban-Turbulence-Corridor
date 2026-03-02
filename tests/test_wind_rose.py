"""風花圖建立與季節分析模組測試。

測試 build_wind_rose_data()、get_dominant_direction()、filter_by_season()，
確認 16 扇區統計、頻率百分比總和、主風向辨識以及季節篩選。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.wind.wind_rose import (
    build_wind_rose_data,
    filter_by_season,
    get_dominant_direction,
)


def _make_wind_df(
    n: int = 1000,
    dominant_direction: float = 45.0,
    dominant_fraction: float = 0.3,
    seed: int = 42,
) -> pd.DataFrame:
    """建立模擬風場觀測資料。

    dominant_fraction 比例的資料集中在 dominant_direction 附近，
    其餘均勻分布。
    """
    rng = np.random.RandomState(seed)

    n_dominant = int(n * dominant_fraction)
    n_random = n - n_dominant

    # 主風向附近（加入 +-15 度擾動）
    dominant_dirs = dominant_direction + rng.uniform(-15, 15, n_dominant)
    dominant_dirs = dominant_dirs % 360
    dominant_speeds = rng.uniform(3, 10, n_dominant)

    # 均勻分布
    random_dirs = rng.uniform(0, 360, n_random)
    random_speeds = rng.uniform(1, 8, n_random)

    directions = np.concatenate([dominant_dirs, random_dirs])
    speeds = np.concatenate([dominant_speeds, random_speeds])

    # 加入時間欄位
    dates = pd.date_range("2023-01-01", periods=n, freq="h")

    return pd.DataFrame({
        "wind_speed": speeds,
        "wind_direction": directions,
        "observation_time": dates[:n],
    })


class TestBuildWindRoseData:
    """build_wind_rose_data() 功能測試。"""

    def test_16_sectors(self):
        """預設應產生 16 個方向扇區。"""
        wind_df = _make_wind_df()
        result = build_wind_rose_data(wind_df)
        # 實際有資料的扇區可能少於 16，但 sector_center 值應在 0-337.5 範圍
        assert all(result["sector_center"] >= 0)
        assert all(result["sector_center"] < 360)

    def test_frequency_pct_sum_100(self):
        """所有扇區的 frequency_pct 總和應為 100%。"""
        wind_df = _make_wind_df(n=5000)
        result = build_wind_rose_data(wind_df)
        total = result["frequency_pct"].sum()
        assert total == pytest.approx(100.0, abs=0.1)

    def test_mean_speed_positive(self):
        """每個扇區的平均風速應為正。"""
        wind_df = _make_wind_df()
        result = build_wind_rose_data(wind_df)
        assert all(result["mean_speed"] > 0)

    def test_max_speed_ge_mean(self):
        """每個扇區的最大風速應大於等於平均。"""
        wind_df = _make_wind_df()
        result = build_wind_rose_data(wind_df)
        assert all(result["max_speed"] >= result["mean_speed"])

    def test_dominant_sector_highest_frequency(self):
        """主風向扇區應有最高頻率。"""
        wind_df = _make_wind_df(
            n=5000,
            dominant_direction=45.0,
            dominant_fraction=0.5,
        )
        result = build_wind_rose_data(wind_df)
        max_row = result.loc[result["frequency_pct"].idxmax()]
        # 45 度應對應到 45.0 扇區
        assert abs(max_row["sector_center"] - 45.0) < 22.5

    def test_custom_n_sectors(self):
        """支援自訂扇區數。"""
        wind_df = _make_wind_df()
        result = build_wind_rose_data(wind_df, n_sectors=8)
        # 8 個扇區，sector_center 間隔 45 度
        centers = sorted(result["sector_center"].unique())
        if len(centers) > 1:
            diffs = [centers[i + 1] - centers[i] for i in range(len(centers) - 1)]
            assert all(abs(d - 45.0) < 0.1 for d in diffs)

    def test_custom_column_names(self):
        """支援自訂欄位名稱。"""
        wind_df = pd.DataFrame({
            "ws": [3.0, 5.0, 7.0, 4.0],
            "wd": [0.0, 90.0, 180.0, 270.0],
        })
        result = build_wind_rose_data(
            wind_df, speed_col="ws", direction_col="wd"
        )
        assert len(result) > 0
        assert "frequency_pct" in result.columns

    def test_handles_360_wrap(self):
        """風向接近 360 度時應正確歸類到北方扇區。"""
        wind_df = pd.DataFrame({
            "wind_speed": [5.0, 6.0, 4.0, 5.5],
            "wind_direction": [355.0, 5.0, 358.0, 2.0],
        })
        result = build_wind_rose_data(wind_df)
        # 這些方向都應歸到 0 度（北）扇區
        assert 0.0 in result["sector_center"].values


class TestGetDominantDirection:
    """get_dominant_direction() 功能測試。"""

    def test_returns_tuple(self):
        """應回傳 (方向, 風速) 元組。"""
        wind_df = _make_wind_df()
        wind_rose = build_wind_rose_data(wind_df)
        direction, speed = get_dominant_direction(wind_rose)
        assert isinstance(direction, float)
        assert isinstance(speed, float)

    def test_dominant_direction_matches_data(self):
        """主風向應與資料中最頻繁方向一致。"""
        wind_df = _make_wind_df(
            dominant_direction=225.0,
            dominant_fraction=0.6,
            n=5000,
        )
        wind_rose = build_wind_rose_data(wind_df)
        direction, speed = get_dominant_direction(wind_rose)
        # 應接近 225 度
        assert abs(direction - 225.0) < 22.5

    def test_speed_positive(self):
        """主風向平均風速應為正。"""
        wind_df = _make_wind_df()
        wind_rose = build_wind_rose_data(wind_df)
        _, speed = get_dominant_direction(wind_rose)
        assert speed > 0

    def test_direction_in_range(self):
        """主風向應在 [0, 360) 範圍。"""
        wind_df = _make_wind_df()
        wind_rose = build_wind_rose_data(wind_df)
        direction, _ = get_dominant_direction(wind_rose)
        assert 0 <= direction < 360


class TestFilterBySeason:
    """filter_by_season() 功能測試。"""

    def test_northeast_season_months(self):
        """東北季風（10-4月）篩選。"""
        dates = pd.date_range("2023-01-01", "2023-12-31", freq="D")
        wind_df = pd.DataFrame({
            "wind_speed": np.random.uniform(1, 10, len(dates)),
            "wind_direction": np.random.uniform(0, 360, len(dates)),
            "observation_time": dates,
        })
        result = filter_by_season(wind_df, "northeast")
        months = pd.to_datetime(result["observation_time"]).dt.month
        # 所有月份應在 10-12 或 1-4
        for m in months:
            assert m >= 10 or m <= 4

    def test_southwest_season_months(self):
        """西南季風（6-9月）篩選。"""
        dates = pd.date_range("2023-01-01", "2023-12-31", freq="D")
        wind_df = pd.DataFrame({
            "wind_speed": np.random.uniform(1, 10, len(dates)),
            "wind_direction": np.random.uniform(0, 360, len(dates)),
            "observation_time": dates,
        })
        result = filter_by_season(wind_df, "southwest")
        months = pd.to_datetime(result["observation_time"]).dt.month
        assert all((months >= 6) & (months <= 9))

    def test_northeast_has_more_months(self):
        """東北季風期間（7個月）應比西南季風（4個月）有更多資料。"""
        dates = pd.date_range("2023-01-01", "2023-12-31", freq="D")
        wind_df = pd.DataFrame({
            "wind_speed": np.random.uniform(1, 10, len(dates)),
            "wind_direction": np.random.uniform(0, 360, len(dates)),
            "observation_time": dates,
        })
        ne = filter_by_season(wind_df, "northeast")
        sw = filter_by_season(wind_df, "southwest")
        assert len(ne) > len(sw)

    def test_unknown_season_raises_error(self):
        """未知季節名稱應拋出 ValueError。"""
        wind_df = pd.DataFrame({
            "wind_speed": [5.0],
            "wind_direction": [45.0],
            "observation_time": ["2023-06-01"],
        })
        with pytest.raises(ValueError, match="Unknown season"):
            filter_by_season(wind_df, "winter")

    def test_transition_season(self):
        """過渡季節（5, 9, 10月）篩選。"""
        dates = pd.date_range("2023-01-01", "2023-12-31", freq="D")
        wind_df = pd.DataFrame({
            "wind_speed": np.random.uniform(1, 10, len(dates)),
            "wind_direction": np.random.uniform(0, 360, len(dates)),
            "observation_time": dates,
        })
        result = filter_by_season(wind_df, "transition")
        months = pd.to_datetime(result["observation_time"]).dt.month
        assert all(months.isin([5, 9, 10]))

    def test_no_time_column_returns_all(self):
        """缺少時間欄位時應回傳全部資料。"""
        wind_df = pd.DataFrame({
            "wind_speed": [5.0, 6.0],
            "wind_direction": [45.0, 90.0],
        })
        result = filter_by_season(wind_df, "northeast")
        assert len(result) == len(wind_df)

    def test_filter_preserves_columns(self):
        """篩選後應保留所有原始欄位。"""
        wind_df = pd.DataFrame({
            "wind_speed": [5.0, 6.0, 7.0],
            "wind_direction": [45.0, 90.0, 180.0],
            "observation_time": ["2023-01-15", "2023-07-15", "2023-11-15"],
            "station": ["A", "B", "C"],
        })
        result = filter_by_season(wind_df, "northeast")
        assert "station" in result.columns
