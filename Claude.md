# Urban Turbulence Corridor (UTC) — Claude.md

## 專案簡介

Urban Turbulence Corridor 是一套都市風場湍流建模與無人機飛行風險評估系統，
針對台灣都市環境，整合開放地理資料、氣象數據與建築形態分析，
提供互動式的風廊視覺化與飛行安全決策支援。

---

## 開發目標：互動式 Demo

最終 Demo 目標是讓用戶可以**直接操作地圖介面**，完成從區域選取、風況分析到路線規劃的完整工作流程。

### 核心功能（八大模組）

#### 1. 多邊形區域預測 `[area-prediction]`
- 用戶在地圖上**繪製多邊形**圈定感興趣區域
- 選擇**日期範圍**（如未來 24/48/72 小時）
- 系統回傳該區域內的環境預測：
  - 風速分佈（平均/最大/陣風）
  - 風向統計（風玫瑰圖）
  - 對無人機飛行的影響評估（風險等級分佈）
- 支援多區域同時比較

#### 2. 路線風況查詢 `[route-query]`
- 用戶設定路線（A → B，或多個 waypoint）
- 系統沿路線計算逐段風況：
  - 各路段的風速/風向
  - 沿途風險等級變化（綠/黃/紅/黑）
  - 預估飛行時間（考慮逆風/順風）
- 以路線色帶呈現風險梯度

#### 3. 最優路線規劃 `[optimal-route]`
- 給定起終點，自動規劃**風險最低**的飛行路線
- 基於現有 LCP（Least Cost Path）演算法擴展
- 考慮因素：
  - 風速與風向（逆風懲罰）
  - 建築物遮蔽與湍流風險
  - 飛行高度的風場差異
- 可提供多條備選路線（最安全 / 最短 / 平衡）

#### 4. 動態風廊視覺化 `[wind-corridor-viz]`
- 地圖上以**動態箭頭**呈現風廊：
  - 箭頭方向 = 風向
  - 箭頭大小 = 風速強度
  - 顏色 = 風險等級（綠→黃→紅→黑）
- 可切換不同風廊（主要/次要/微型）
- 支援圖層疊加（建築物 + 風廊 + 風險格網）

#### 5. 時間軸播放器 `[timeline-player]`
- 底部時間軸，可拖動或自動播放
- 觀察風場隨時間的動態變化（如未來 24/48/72 小時）
- 播放速度可調整
- 關鍵時刻標記（如風速驟變、風向轉換）
- 類似天氣動畫效果，讓用戶直觀感受風場演變

#### 6. 無人機型號適配 `[drone-matching]`
- 用戶選擇特定無人機型號（DJI Mini 4 Pro、Mavic 3、Matrice 350 等）
- 系統根據該機型的抗風能力自動：
  - 標示安全/危險區域
  - 調整路線規劃的風險閾值
  - 計算預估續航時間（考慮逆風耗電）
- 支援自訂無人機規格（最大抗風、重量、電池容量）
- 基於現有 `drone_specs.py` 擴展

#### 7. 飛行高度切換 `[altitude-switch]`
- 即時切換 50m / 80m / 120m（或自訂高度）的風場視圖
- 觀察不同高度的風險差異
- 路線規劃時可指定飛行高度
- 高度切換時地圖圖層平滑過渡
- 基於現有對數風速剖面（log wind profile）計算

#### 8. 任務報告匯出 `[mission-report]`
- 將分析結果匯出為飛行前 briefing 報告：
  - 區域風險摘要
  - 建議路線與替代方案
  - 沿途風況預報
  - 無人機適配性評估
- 匯出格式：PDF / 截圖 / JSON（供整合至飛控系統）
- 包含地圖截圖 + 數據圖表

---

## 技術架構

### 後端（Python）
- **框架**: FastAPI
- **資料庫**: PostgreSQL + PostGIS (GeoAlchemy2)
- **地理空間**: GeoPandas, Shapely, Rasterio
- **風場模型**: 對數風速剖面、LCP 風廊分析、Weibull 分佈
- **部署**: Vercel Serverless + Uvicorn

### 前端（React + TypeScript）
- **框架**: React 18 + React Router 6
- **地圖**: MapLibre GL（開源 Mapbox 替代方案）
- **圖表**: Recharts（風玫瑰圖、分佈圖）
- **樣式**: Tailwind CSS
- **資料**: TanStack React Query
- **建構**: Vite + TypeScript

### 資料來源
- **建築**: OpenStreetMap + NLSC（國土測繪中心）
- **氣象**: Open-Meteo API + CWA（中央氣象署）
- **地形**: DSM/DTM（20m 格網數值高程模型）
- **座標系**: 內部 EPSG:3826（TWD97）→ 輸出 EPSG:4326（WGS84）

---

## Demo 工作流程

```
用戶操作流程：
┌─────────────────────────────────────────────────────┐
│  1. 選擇無人機型號                                      │
│  2. 設定日期/時間範圍                                    │
│  3. 選擇飛行高度                                        │
│     ┌──────────┬──────────┬──────────┐               │
│     │ 繪製區域  │ 設定路線  │ 最優規劃  │               │
│     │ (多邊形)  │ (A→B)   │ (自動)   │               │
│     └────┬─────┴────┬─────┴────┬─────┘               │
│          ▼          ▼          ▼                      │
│     區域風險報告  路線風況分析  最佳路線建議              │
│          │          │          │                      │
│          └──────────┴──────────┘                      │
│                     ▼                                 │
│  4. 時間軸播放 → 觀察風場動態變化                        │
│  5. 匯出任務報告（PDF / JSON）                          │
└─────────────────────────────────────────────────────┘
```

---

## 風險等級定義

| 等級 | 顏色 | 風速 (m/s) | 說明 |
|------|------|-----------|------|
| 安全 | 🟢 綠 | ≤ 5 | 適合所有機型飛行 |
| 注意 | 🟡 黃 | 5 – 8 | 輕型無人機需注意 |
| 危險 | 🔴 紅 | 8 – 12 | 僅專業機型可飛行 |
| 極度危險 | ⚫ 黑 | > 12 | 禁止飛行 |

---

## 開發階段

### Phase 1 ✅ 已完成
- 都市形態計算（FAI、BCR、SVF、z₀、zd）
- 風廊識別（LCP 演算法）
- 對數風速剖面降尺度
- 風險分類系統
- FastAPI 後端 + React 前端
- Vercel 部署配置

### Phase 2 🔄 進行中 — 互動式 Demo

#### Sprint 0：基礎設施 — 預報數據 + 地圖繪圖工具
> 所有互動功能的前提

**Backend**
- [ ] 擴展 `src/ingest/open_meteo.py`：新增 `fetch_forecast_wind(city, days=3)`
  - Open-Meteo Forecast API，未來 72h 逐時 wind_speed/wind_direction/wind_gusts
- [ ] 新增 `src/api/routes/forecast.py`：
  - `GET /api/v1/forecast?city=taipei&hours=72` → 逐時風場預報
  - `GET /api/v1/forecast/at?lon=&lat=&hours=72` → 特定座標預報（含 log profile 降尺度）
- [ ] 在 `src/api/main.py` 註冊新 router

**Frontend**
- [ ] 安裝 `@mapbox/mapbox-gl-draw`（相容 MapLibre GL）
- [ ] 新建 `web/src/components/map/DrawingToolbar.tsx`：
  - 模式切換：多邊形 / 折線 / 標記點
  - 回調：`onPolygonComplete(geojson)`, `onRouteComplete(geojson)`
- [ ] 整合進 `WindMap.tsx`：新增 `enableDrawing` prop

#### Sprint 1：飛行高度切換 + 無人機型號適配（可與 Sprint 0 並行）

**1A. 飛行高度切換 `[altitude-switch]`**
- [ ] 擴展 `MapControls.tsx`：滑桿或按鈕組（50/80/120m + 自訂）
- [ ] 高度變更觸發 React Query 重新取得 grid cells
- [ ] MapLibre `setPaintProperty` 漸變過渡

**1B. 無人機型號適配 `[drone-matching]`**
- [ ] 新建 `web/src/components/drone/DroneSelector.tsx`（全局選擇器）
- [ ] 新建 `web/src/contexts/FlightContext.tsx`（selectedDrone, selectedHeight, selectedTimeRange）
- [ ] 擴展 `WindMap.tsx`：根據無人機 `max_wind_speed` 動態調整格網顏色
- [ ] 擴展 `src/risk/drone_specs.py`：`get_zone_flyability()` 批量評估

#### Sprint 2：動態風廊視覺化 + 時間軸播放器（依賴 Sprint 0）

**2A. 動態風廊箭頭 `[wind-corridor-viz]`**
- [ ] 新建 `web/src/components/map/WindArrowLayer.tsx`：
  - MapLibre `symbol` 圖層 + SVG 箭頭 `icon-image`
  - 大小 = `icon-size` 映射 wind_speed（0.3–1.5）
  - 顏色 = risk_level（復用 `RISK_COLORS`）
  - 旋轉 = `icon-rotate` 映射 wind_direction
- [ ] 動畫效果：定期微調透明度模擬風流動

**2B. 時間軸播放器 `[timeline-player]`**
- [ ] 新建 `web/src/components/timeline/TimelinePlayer.tsx`：
  - 底部固定欄：時間滑桿 + 播放/暫停/快轉
  - 範圍：現在 → +72h，速度 1x/2x/4x
  - 關鍵時刻標記（風速 > 閾值 → 紅點）
- [ ] 新增 `useForecast(city, hours)` hook
- [ ] 時間軸變更 → 通過 FlightContext 更新地圖數據

#### Sprint 3：多邊形區域預測 + 路線風況查詢（依賴 Sprint 0 繪圖工具）

**3A. 多邊形區域預測 `[area-prediction]`**
- [ ] 新增 `src/api/routes/area.py`：
  - `POST /api/v1/area/predict`
  - 邏輯：polygon WGS84→3826 → `ST_Intersects` grid cells → 聚合風速/風險/風玫瑰
- [ ] 新增 `src/db/queries.py`：`query_grids_by_polygon()`
- [ ] 新建 `web/src/pages/AnalysisPage.tsx`（主互動頁面）

**3B. 路線風況查詢 `[route-query]`**
- [ ] 新增 `src/api/routes/route.py`：
  - `POST /api/v1/route/analyze`
  - 邏輯：waypoints 間每 100m 插值 → 查詢 grid cell → 逐段風速/逆風分量/飛行時間
- [ ] 新建 `web/src/components/route/RouteAnalysisPanel.tsx`
  - MapLibre `line-gradient` 按風險上色路線

#### Sprint 4：最優路線規劃（依賴 Sprint 3）
- [ ] 擴展 `src/wind/lcp.py`：`plan_optimal_route(start, end, cost_surface, mode)`
  - 三種模式：`safest`（最低風險）/ `shortest`（最短）/ `balanced`（加權）
  - 復用 `compute_cost_distance()` + `trace_least_cost_path()`
- [ ] 擴展 `src/api/routes/route.py`：`POST /api/v1/route/plan`
- [ ] 新建 `web/src/components/route/RoutePlannerPanel.tsx`
  - 三條備選路線同時顯示 + 比較表格

#### Sprint 5：任務報告匯出（依賴 Sprint 3/4）
- [ ] 新增 `src/api/routes/report.py`：`POST /api/v1/report/generate`
  - PDF（reportlab）/ JSON 格式
- [ ] 新建 `web/src/components/report/ExportButton.tsx`
  - 地圖截圖：`map.getCanvas().toDataURL()`

### Phase 3 📋 計畫中 — 生產化
- [ ] 使用者帳戶與歷史紀錄
- [ ] 即時氣象推播（風速驟變警報）
- [ ] 禁飛區圖層疊加
- [ ] 飛控系統 API 整合
- [ ] 行動裝置適配

---

## Sprint 依賴關係

```
Sprint 0（基礎設施）
  ├── Sprint 1（高度 + 無人機） ← 可並行
  ├── Sprint 2（風廊 + 時間軸） ← 依賴預報 API
  ├── Sprint 3（區域 + 路線） ← 依賴繪圖工具
  │     └── Sprint 4（最優路線） ← 依賴路線基礎
  └── Sprint 5（報告匯出） ← 依賴分析結果
```

---

## 新增/修改檔案清單

| 類型 | 檔案路徑 | 操作 |
|------|----------|------|
| Backend | `src/ingest/open_meteo.py` | 擴展（forecast） |
| Backend | `src/api/routes/forecast.py` | 新建 |
| Backend | `src/api/routes/area.py` | 新建 |
| Backend | `src/api/routes/route.py` | 新建 |
| Backend | `src/api/routes/report.py` | 新建 |
| Backend | `src/api/main.py` | 擴展（註冊 routers） |
| Backend | `src/api/schemas.py` | 擴展（新 models） |
| Backend | `src/db/queries.py` | 擴展（polygon + nearest） |
| Backend | `src/wind/lcp.py` | 擴展（A→B 規劃） |
| Backend | `src/risk/drone_specs.py` | 擴展（批量評估） |
| Frontend | `web/src/components/map/DrawingToolbar.tsx` | 新建 |
| Frontend | `web/src/components/map/WindArrowLayer.tsx` | 新建 |
| Frontend | `web/src/components/map/WindMap.tsx` | 擴展 |
| Frontend | `web/src/components/map/MapControls.tsx` | 擴展 |
| Frontend | `web/src/components/drone/DroneSelector.tsx` | 新建 |
| Frontend | `web/src/components/timeline/TimelinePlayer.tsx` | 新建 |
| Frontend | `web/src/components/route/RouteAnalysisPanel.tsx` | 新建 |
| Frontend | `web/src/components/route/RoutePlannerPanel.tsx` | 新建 |
| Frontend | `web/src/components/report/ExportButton.tsx` | 新建 |
| Frontend | `web/src/contexts/FlightContext.tsx` | 新建 |
| Frontend | `web/src/pages/AnalysisPage.tsx` | 新建 |
| Frontend | `web/src/api/hooks.ts` | 擴展 |
| Frontend | `web/src/api/types.ts` | 擴展 |

---

## 編碼規範

- Python: PEP 8, type hints, docstrings（繁體中文可）
- TypeScript: strict mode, 明確型別定義
- 元件: 功能元件 + React hooks
- 測試: pytest (後端) + vitest (前端)
- Git: 功能分支 → PR → main
- 座標: 內部一律 EPSG:3826，API 輸出一律 EPSG:4326

---

## 關鍵檔案索引

| 模組 | 檔案 | 說明 |
|------|------|------|
| 風廊分析 | `src/wind/lcp.py` | LCP 最低成本路徑 |
| 風速剖面 | `src/wind/log_profile.py` | 對數風速降尺度 |
| 風險分類 | `src/risk/classifier.py` | 四級風險分類 |
| 無人機規格 | `src/risk/drone_specs.py` | 機型抗風能力 |
| API 入口 | `src/api/main.py` | FastAPI 主入口 |
| 資料模型 | `src/db/models.py` | PostGIS 資料表 |
| 地圖頁面 | `web/src/pages/CorridorPage.tsx` | 風廊地圖 |
| API hooks | `web/src/api/hooks.ts` | React Query |
| 風險閾值 | `config/risk_thresholds.yaml` | 閾值設定 |
