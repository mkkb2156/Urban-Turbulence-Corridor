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
# 建立虛擬環境（請在專案根目錄執行）
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
# 若上面失敗，可改為：uv pip install geopandas 等依賴後再跑測試
# 注意：uv 指令後勿在同一行加註解，會出現 Failed to parse: # 錯誤

# 設定環境變數
cp .env.example .env
# 編輯 .env 填入 CWA_API_KEY 等

# 執行 Phase 1 pipeline（台北）
python scripts/run_pipeline.py --city taipei --grid-size 100

# 執行測試
pytest tests/ -v
```

## 開發指令

```bash
# 啟動前端開發伺服器
cd web && npm run dev        # http://localhost:3000

# 啟動 Vitest UI（瀏覽器測試介面）
cd web && npm run test:ui    # http://localhost:51204/__vitest__/

# 執行所有測試（前後端）
bash scripts/run_tests.sh all

# Watch mode
bash scripts/run_tests.sh watch-backend    # pytest watch
bash scripts/run_tests.sh watch-frontend   # vitest --ui
```

## 目前階段

**Phase 1 — 形態學風險圖層**：FAI + LCP + 靜態風速估算

## 座標系統

- 內部計算：EPSG:3826（TWD97/TM2，公尺）
- API 輸出：EPSG:4326（WGS84）

## 授權

MIT License
