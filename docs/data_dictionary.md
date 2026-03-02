# UTC 資料欄位定義

## grid_cells 表

| 欄位 | 型態 | 說明 |
|------|------|------|
| grid_id | str | 網格 ID，格式 `{city}_{row}_{col}` |
| bcr | float | Building Coverage Ratio (0-1) |
| svf | float | Sky View Factor (0-1) |
| fai_ne | float | 東北季風 FAI 平均值 |
| fai_sw | float | 西南季風 FAI 平均值 |
| fai_max | float | 所有方向最大 FAI |
| z0 | float | 粗糙度長度 (m) |
| zd | float | 零平面位移 (m) |
| wind_50m | float | 50m 高度估算風速 (m/s) |
| wind_80m | float | 80m 高度估算風速 (m/s) |
| wind_120m | float | 120m 高度估算風速 (m/s) |
| risk_level | str | 風險等級 (green/yellow/red/black) |
| risk_score | float | 綜合風險分數 (0-100) |
| is_corridor | bool | 是否位於風廊上 |

## wind_corridors 表

| 欄位 | 型態 | 說明 |
|------|------|------|
| corridor_id | str | 風廊 ID |
| corridor_class | str | primary / secondary / minor |
| total_cost | float | LCP 累積成本 |
| estimated_width | float | 估算有效寬度 (m) |
