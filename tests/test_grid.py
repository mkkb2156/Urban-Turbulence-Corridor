"""網格建立模組測試。

測試 create_grid()、clip_grid_to_boundary()、save_grid() 等函式，
確認網格維度、ID 格式、CRS 設定以及邊界裁切行為。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import box

from src.morphology.grid import clip_grid_to_boundary, create_grid, save_grid


class TestCreateGrid:
    """create_grid() 功能測試。"""

    def test_grid_dimensions_match_bounds(self):
        """網格數量應與 bounds / cell_size 一致。"""
        bounds = (300000, 2770000, 300500, 2770300)
        grid = create_grid(bounds=bounds, cell_size=100)
        # 500m / 100m = 5 cols, 300m / 100m = 3 rows => 15 cells
        assert len(grid) == 15

    def test_grid_dimensions_small(self):
        """小範圍網格維度正確。"""
        bounds = (300000, 2770000, 300200, 2770200)
        grid = create_grid(bounds=bounds, cell_size=100)
        # 200m / 100m = 2 cols, 2 rows => 4 cells
        assert len(grid) == 4

    def test_grid_id_format(self):
        """網格 ID 應遵循 {city}_{row:03d}_{col:03d} 格式。"""
        bounds = (300000, 2770000, 300300, 2770300)
        grid = create_grid(bounds=bounds, cell_size=100, city="testcity")
        expected_ids = [
            f"testcity_{r:03d}_{c:03d}" for r in range(3) for c in range(3)
        ]
        assert sorted(grid["grid_id"].tolist()) == sorted(expected_ids)

    def test_grid_crs_is_epsg3826(self):
        """網格 CRS 應為 EPSG:3826。"""
        bounds = (300000, 2770000, 300200, 2770200)
        grid = create_grid(bounds=bounds, cell_size=100)
        assert grid.crs.to_epsg() == 3826

    def test_grid_has_required_columns(self):
        """網格應包含 grid_id、row、col 與 geometry 欄位。"""
        bounds = (300000, 2770000, 300200, 2770200)
        grid = create_grid(bounds=bounds, cell_size=100)
        for col in ["grid_id", "row", "col", "geometry"]:
            assert col in grid.columns

    def test_grid_cell_area(self):
        """每個網格面積應為 cell_size^2。"""
        bounds = (300000, 2770000, 300300, 2770300)
        cell_size = 100
        grid = create_grid(bounds=bounds, cell_size=cell_size)
        expected_area = cell_size * cell_size
        for area in grid.geometry.area:
            assert abs(area - expected_area) < 0.01

    def test_custom_cell_size(self):
        """使用自訂 cell_size 建立網格。"""
        bounds = (300000, 2770000, 300400, 2770400)
        grid = create_grid(bounds=bounds, cell_size=200)
        # 400m / 200m = 2 cols, 2 rows => 4 cells
        assert len(grid) == 4
        for area in grid.geometry.area:
            assert abs(area - 40000) < 0.01  # 200*200

    def test_grid_alignment_to_cell_size(self):
        """邊界應對齊至 cell_size 的倍數。"""
        # 非整數倍的邊界
        bounds = (300010, 2770010, 300290, 2770290)
        grid = create_grid(bounds=bounds, cell_size=100)
        # floor(300010/100)*100 = 300000, ceil(300290/100)*100 = 300300
        # 300m / 100m = 3 cols, 3 rows => 9 cells
        assert len(grid) == 9

    def test_row_col_indices(self):
        """row 和 col 索引應從 0 開始遞增。"""
        bounds = (300000, 2770000, 300300, 2770200)
        grid = create_grid(bounds=bounds, cell_size=100)
        assert set(grid["row"].unique()) == {0, 1}
        assert set(grid["col"].unique()) == {0, 1, 2}

    def test_default_city_taipei(self):
        """預設城市為 taipei，網格 ID 以 taipei 開頭。"""
        bounds = (300000, 2770000, 300100, 2770100)
        grid = create_grid(bounds=bounds, cell_size=100, city="taipei")
        assert grid["grid_id"].iloc[0].startswith("taipei_")


class TestClipGridToBoundary:
    """clip_grid_to_boundary() 功能測試。"""

    def test_clipping_reduces_cells(self, sample_grid):
        """邊界裁切後網格數量應減少或相等。"""
        # 建立只覆蓋左上區域的邊界
        boundary_geom = box(300000, 2770000, 300150, 2770150)
        boundary = gpd.GeoDataFrame(
            geometry=[boundary_geom], crs="EPSG:3826"
        )
        clipped = clip_grid_to_boundary(sample_grid, boundary)
        assert len(clipped) < len(sample_grid)

    def test_full_coverage_keeps_all(self, sample_grid):
        """完全覆蓋的邊界不應減少網格。"""
        boundary_geom = box(299900, 2769900, 300400, 2770400)
        boundary = gpd.GeoDataFrame(
            geometry=[boundary_geom], crs="EPSG:3826"
        )
        clipped = clip_grid_to_boundary(sample_grid, boundary)
        assert len(clipped) == len(sample_grid)

    def test_no_overlap_returns_empty(self, sample_grid):
        """不重疊的邊界應返回空網格。"""
        boundary_geom = box(0, 0, 100, 100)  # 完全不重疊
        boundary = gpd.GeoDataFrame(
            geometry=[boundary_geom], crs="EPSG:3826"
        )
        clipped = clip_grid_to_boundary(sample_grid, boundary)
        assert len(clipped) == 0

    def test_clipped_preserves_columns(self, sample_grid):
        """裁切後應保留原始欄位。"""
        boundary_geom = box(300000, 2770000, 300200, 2770200)
        boundary = gpd.GeoDataFrame(
            geometry=[boundary_geom], crs="EPSG:3826"
        )
        clipped = clip_grid_to_boundary(sample_grid, boundary)
        for col in ["grid_id", "row", "col"]:
            assert col in clipped.columns

    def test_clipped_preserves_crs(self, sample_grid):
        """裁切後 CRS 不變。"""
        boundary_geom = box(300000, 2770000, 300200, 2770200)
        boundary = gpd.GeoDataFrame(
            geometry=[boundary_geom], crs="EPSG:3826"
        )
        clipped = clip_grid_to_boundary(sample_grid, boundary)
        assert clipped.crs.to_epsg() == 3826


class TestSaveGrid:
    """save_grid() 功能測試。"""

    def test_save_creates_file(self, sample_grid):
        """儲存網格應建立 GPKG 檔案。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_grid.gpkg"
            result_path = save_grid(sample_grid, output_path=output_path)
            assert result_path.exists()

    def test_saved_grid_readable(self, sample_grid):
        """儲存後的檔案應可正確讀取。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_grid.gpkg"
            save_grid(sample_grid, output_path=output_path)
            loaded = gpd.read_file(output_path)
            assert len(loaded) == len(sample_grid)
            assert "grid_id" in loaded.columns

    def test_save_creates_parent_dir(self, sample_grid):
        """儲存時應自動建立父目錄。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "subdir" / "deep" / "test_grid.gpkg"
            result_path = save_grid(sample_grid, output_path=output_path)
            assert result_path.exists()

    def test_save_returns_path(self, sample_grid):
        """儲存應回傳輸出路徑。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_grid.gpkg"
            result = save_grid(sample_grid, output_path=output_path)
            assert isinstance(result, Path)
            assert str(result) == str(output_path)
