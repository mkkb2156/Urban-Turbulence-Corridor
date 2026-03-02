# UTC — Urban Turbulence Corridor

台灣城市風廊（Urban Wind Corridor）資料層，供無人機低空作業風險評估使用。

## 概述

UTC 從開放資料自動計算城市風廊與風險等級：

1. 取得 3D 建物與地形資料
2. 計算都市形態學指標（FAI、SVF、粗糙度）
3. 辨識風廊路徑（LCP）
4. 估算風速風險
5. 透過 API 與 Web 地圖呈現

## 快速開始

```bash
# 建立虛擬環境
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# 設定環境變數
cp .env.example .env
# 編輯 .env 填入 CWA_API_KEY 等

# 執行 Phase 1 pipeline（台北）
python scripts/run_pipeline.py --city taipei --grid-size 100

# 執行測試
pytest tests/ -v
```

## 目前階段

**Phase 1 — 形態學風險圖層**：FAI + LCP + 靜態風速估算

## 座標系統

- 內部計算：EPSG:3826（TWD97/TM2，公尺）
- API 輸出：EPSG:4326（WGS84）

## 授權

MIT License
