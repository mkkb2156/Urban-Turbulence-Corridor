# Urban Turbulence Corridor (UTC) v4

台灣城市風廊圖層系統 — 無人機低空作業風險評估平台
UX-First 單頁地圖應用 + WebGL GPU 風場渲染

---

## 專案架構 Architecture

```
Frontend:  React 19 + TypeScript + Vite + Tailwind CSS 4
           @vis.gl/react-maplibre + MapLibre GL v4
           Deck.gl v9 (Interleaved mode)
           WebGL GPU Texture 粒子風場（100K+ 粒子）
           Zustand v5 + TanStack Query v5

Backend:   FastAPI (Python 3.11+)
           27 API endpoints (25 繼承 + 2 新增)

Tiles:     Martin (Rust) — PostGIS → MVT 向量圖磚

Database:  Supabase PostGIS (1,470 grid cells + 10 wind corridors)

Deploy:    Fly.io (Martin + API) + Cloudflare Pages (Frontend)

Data:      Open-Meteo (風速預報) + CWA 中央氣象署 (測站觀測)
```

### 目錄結構

```
apps/web/                         # React 19 前端
  src/
    main.tsx                      # App 入口
    App.tsx                       # Root layout (地圖 + 面板)
    map/
      UTCMap.tsx                  # 主地圖元件 (@vis.gl/react-maplibre)
      DeckGLOverlay.tsx           # Interleaved deck.gl overlay
      layers/
        WindLayer.ts              # WebGL GPU Texture 粒子風場 (MapLibre custom layer)
        useWindLayer.ts           # React hook for WindLayer lifecycle
      controls/
        Toolbar.tsx               # 頂部工具列（搜尋 + 機型 + 圖層）
        TimeSlider.tsx            # 底部 72h 時間軸
        LayerDrawer.tsx           # 收摺式圖層控制
    panels/
      FlightPanel.tsx             # 右側結論面板（風險+時段+電池+廊道）
    store/
      map.ts                      # Zustand：地圖狀態（視口/選點）
      flight.ts                   # Zustand：機型/時間/飛行計畫
      ui.ts                       # Zustand：面板開關/圖層可見
    api/
      client.ts                   # HTTP client (auth + retry)
      types.ts                    # TypeScript 型別
      hooks/                      # TanStack Query hooks
    utils/
      riskColor.ts                # 風險色彩映射
      windTexture.ts              # PNG encode/decode
      cn.ts                       # className utility

services/api/                     # FastAPI 後端
  main.py                        # App 入口 + middleware
  auth.py                        # API Key 認證
  rate_limit.py                  # 限流
  errors.py                      # UTCError hierarchy
  response.py                    # Response envelope
  schemas.py                     # Pydantic models
  fallback.py                    # Demo 資料
  logging_config.py              # Request logging
  routes/                        # 15 router files (27 endpoints)
    wind_texture.py              # v4 新增：/wind-texture (PNG)
    flight_summary.py            # v4 新增：/flight-summary (聚合)
    dashboard.py, wind.py, risk.py, corridor.py, ...
  core/                          # 計算引擎（繼承 v3）
    wind/                        # log_profile, rockle, lcp, weibull, texture_encoder
    risk/                        # score, classifier, derived, power_model, drone_specs
    morphology/                  # bcr, fai, svf, roughness, lcz, grid
    ingest/                      # cwa, open_meteo, era5, osm, nlsc, esa, ...
  db/                            # SQLAlchemy + PostGIS
    session.py, models.py, queries.py, migrations/

services/tiles/                   # Martin 設定
  config.yaml                    # 5 個圖磚層

infra/                           # Docker + 部署
  docker-compose.yml             # postgres + martin + api + web
  fly/                           # Fly.io 部署設定
  Dockerfile.*                   # 容器映像
```

---

## 快速開始 Quick Start

### 前端開發

```bash
cd apps/web
npm install
npm run dev          # http://localhost:5173
```

### 後端開發

```bash
cd services/api
pip install -r requirements.txt
uvicorn main:app --reload   # http://localhost:8000
```

### Docker 全端

```bash
cd infra
docker compose up    # postgres:5432 + martin:3000 + api:8000 + web:5173
```

---

## 設計哲學

UTC v4 是**決策工具**，不是資料瀏覽器。
核心問題：「今天能飛嗎？」

### UX 核心流程
1. WHERE → 點地圖或搜尋地址
2. WHEN → 時間 slider（現在 / 72h 預報）
3. DRONE → 選擇機型
4. 結論 → 右側面板自動顯示 GO / CAUTION / NO-GO

### 技術亮點
- WebGL GPU 粒子風場：100K+ 粒子 60fps，Agafonkin ping-pong texture
- Martin MVT 圖磚：PostGIS → 向量圖磚，支援 10 萬+ 網格
- Interleaved mode：deck.gl 嵌入 MapLibre WebGL2 context
- 單頁地圖：所有功能以地圖為中心，不跳頁

---

## API 端點

### v4 新增
| Method | Path | 說明 |
|--------|------|------|
| GET | `/api/v1/wind-texture` | 風場 PNG Texture (R=U, G=V) |
| GET | `/api/v1/flight-summary` | 飛行風險摘要（聚合端點）|

### 繼承 v3（25 個）
| Method | Path | 說明 |
|--------|------|------|
| GET | `/health` | 健康檢查 |
| GET | `/api/v1/stats` | 儀表板統計 |
| GET | `/api/v1/grids` | Grid cells 地圖資料 |
| GET | `/api/v1/wind-rose` | 風花圖 16 方位 |
| GET | `/api/v1/fai` | FAI 散佈圖 |
| GET | `/api/v1/corridors` | 風廊列表 |
| GET/POST | `/api/v1/wind` | 座標風場查詢 |
| GET/POST | `/api/v1/risk` | 座標風險評估 |
| POST | `/api/v1/risk/batch` | 批次風險 |
| GET | `/api/v1/derived/{grid_id}` | 衍生數據 |
| GET | `/api/v1/derived/{grid_id}/flyability` | 適飛性 |
| GET | `/api/v1/forecast/flight-windows` | 最佳飛行時段 |
| POST | `/api/v1/area/predict` | 區域分析 |
| POST | `/api/v1/route/analyze` | 路線分析 |
| POST | `/api/v1/route/plan` | 路線規劃 |
| POST | `/api/v1/report/generate` | PDF 報告 |
| GET | `/api/v1/forecast` | 天氣預報 |
| GET | `/api/v1/forecast/stations` | CWA 測站 |
| GET | `/api/v1/monitor` | 系統監控 |

---

## 開發注意事項

- **前端文字**：所有 UI 使用中文
- **地圖 token**：不需要（OpenFreeMap + Martin，都免費）
- **API fallback**：DB 不可用時返回 demo 資料
- **API 認證**：開發環境 `API_KEY_REQUIRED=false`
- **新增 Schema**：集中在 `services/api/schemas.py`
- **DB Session**：使用 `from db.session import get_engine, table_exists`
- **Git 分支**：feature branches 使用 `claude/` prefix
- **Lint**：`cd apps/web && npm run lint`
- **Type check**：`cd apps/web && npx tsc --noEmit`
