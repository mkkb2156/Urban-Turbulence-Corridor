# Urban Turbulence Corridor (UTC)

台灣城市風廊圖層系統 — 無人機低空作業風險評估平台

---

## 專案架構 Architecture

```
Frontend:  React 18 + TypeScript + Vite + Tailwind CSS + MapLibre GL
Backend:   FastAPI (Python 3.11+)
Database:  Supabase PostGIS (1,470 grid cells + 10 wind corridors)
Deploy:    Vercel (static build + Python serverless)
Data:      Open-Meteo (風速預報) + CWA 中央氣象署 (測站觀測)
```

### 目錄結構

```
web/                    # React 前端
  src/pages/            # 頁面元件 (Dashboard, Analysis, Corridor, Risk, FAI, Monitor, Guide)
  src/components/       # 共用元件 (map/, dashboard/, drone/, timeline/, report/)
  src/api/              # API client + TypeScript 型別
  src/__tests__/        # Vitest 測試 (8 files)

src/                    # Python 後端
  api/                  # FastAPI app + routes (22 endpoints)
  db/                   # SQLAlchemy models + PostGIS queries
  ingest/               # 資料匯入模組 (CWA, Open-Meteo, ERA5, OSM, NLSC, ESA, etc.)
  morphology/           # 地形分析 (BCR, FAI, roughness, SVF, street canyon)
  risk/                 # 風險評分 + 無人機規格
  wind/                 # 風場模型 (corridor, log profile, Weibull, wind rose, LCP)
```

---

## 快速開始 Quick Start

### 環境變數

複製 `.env.example` → `.env`，至少填入：
- `DATABASE_URL` — Supabase PostgreSQL 連線字串
- `CWA_API_KEY` — 中央氣象署 API key（免費註冊）

### 前端開發

```bash
cd web
npm install
npm run dev          # http://localhost:5173
```

### 後端開發

```bash
pip install -r requirements.txt
uvicorn src.api.main:app --reload   # http://localhost:8000
```

### Build & Preview

```bash
cd web && npm run build    # 產出 web/dist/
npm run preview            # 預覽 production build
```

---

## 測試指南 Testing Guide

### 1. 前端單元測試 (Vitest)

```bash
cd web
npm test                   # 跑所有測試（8 個測試檔案）
npm run test:watch         # Watch mode（開發時使用）
npm run test:ui            # Vitest UI 互動式介面
npm run test:coverage      # 產生覆蓋率報告（HTML + LCOV）
```

測試檔案：`web/src/__tests__/`
- `api/types.test.ts` — API 型別驗證
- `components/FlyabilityChecker.test.tsx` — DroneCheck 元件
- `components/RiskLegend.test.tsx` — 風險圖例元件
- `components/StatsCards.test.tsx` — 統計卡片元件
- `components/TestResultCard.test.tsx` — 測試結果卡片
- `utils/colors.test.ts` — 色彩工具函數
- `utils/format.test.ts` — 格式化工具函數
- `utils/geo.test.ts` — 地理計算工具函數

### 2. API 端點手動測試

啟動後端後，用 curl 或瀏覽器測試：

```bash
# 健康檢查
curl http://localhost:8000/health

# 儀表板資料
curl http://localhost:8000/api/v1/stats
curl http://localhost:8000/api/v1/grids
curl http://localhost:8000/api/v1/wind-rose
curl http://localhost:8000/api/v1/fai

# 風廊
curl http://localhost:8000/api/v1/corridors

# 風場
curl "http://localhost:8000/api/v1/wind?lon=121.5&lat=25.04&height=50"

# 風險評估
curl "http://localhost:8000/api/v1/risk?lon=121.5&lat=25.04&height=50"

# 即時天氣預報
curl "http://localhost:8000/api/v1/forecast?lon=121.5&lat=25.04"
curl http://localhost:8000/api/v1/forecast/stations

# 系統監控
curl http://localhost:8000/api/v1/monitor

# 區域分析 (POST)
curl -X POST http://localhost:8000/api/v1/area/predict \
  -H "Content-Type: application/json" \
  -d '{"polygon":[[121.5,25.03],[121.51,25.03],[121.51,25.04],[121.5,25.04]],"height":50}'

# 路線分析 (POST)
curl -X POST http://localhost:8000/api/v1/route/analyze \
  -H "Content-Type: application/json" \
  -d '{"waypoints":[[121.5,25.03],[121.51,25.04]],"height":50}'

# 批次風險查詢 (POST)
curl -X POST http://localhost:8000/api/v1/risk/batch \
  -H "Content-Type: application/json" \
  -d '{"points":[{"lon":121.5,"lat":25.04,"height":50}]}'
```

### 3. 頁面功能測試清單

啟動前後端後，逐頁驗證：

| 頁面 | 路徑 | 測試項目 |
|------|------|---------|
| 儀表板 | `/` | 統計卡片有數據、風花圖 16 方位、風險分布圓餅圖、地圖載入 grid cells |
| 飛行分析 | `/analysis` | 繪製區域 → 顯示分析結果；繪製路線 → 路線比較表 |
| 風廊 | `/corridors` | 10 條風廊列表、點擊展開詳情、地圖標記風廊路徑 |
| 風險評估 | `/risk` | 色碼風險地圖、DroneCheck 單點查詢、批次查詢（CSV 上傳）|
| FAI 分析 | `/fai` | 散佈圖載入、hover 顯示資訊 |
| 系統監控 | `/monitor` | DB / Open-Meteo / CWA 狀態燈號正常 |
| 使用指南 | `/guide` | 靜態頁面正常渲染 |
| 測試儀表板 | `/tests` | 測試結果卡片、覆蓋率進度條 |

### 4. 後端 Python 測試 (TODO)

目前尚未建立 pytest 測試套件，這是 Phase 3 的優先項目。

---

## 已完成功能 Completed Features

### 核心功能
- ✅ 互動式風險地圖（MapLibre GL + 色碼 grid cells）
- ✅ 風場粒子動畫（Windy.com 風格 Canvas overlay）
- ✅ 風花圖（Recharts 16 方位）
- ✅ 10 條台北風廊識別與地圖標註
- ✅ DroneCheck 單點 + 批次飛行適性查詢
- ✅ 區域分析（多邊形繪製 → 風場統計）
- ✅ 路線規劃與比較（路徑繪製 → 風險分析）
- ✅ FAI 正面面積指數分析
- ✅ 即時天氣預報（Open-Meteo + CWA）
- ✅ PDF 報告匯出

### 平台功能
- ✅ 全中文 UI
- ✅ 響應式設計（桌面 + 行動裝置）
- ✅ 系統監控頁面（DB / API 狀態）
- ✅ 集中式 logging + request middleware
- ✅ Vercel 部署設定（`vercel.json`）
- ✅ 前端 Vitest 測試（8 files）

### 資料來源
- ✅ Supabase PostGIS — 1,470 grid cells + 10 wind corridors
- ✅ Open-Meteo — 風速/風向/陣風即時預報
- ✅ CWA 中央氣象署 — 測站觀測資料

---

## 下一步路線圖 Roadmap → 商業 Demo

### Phase 3A：穩定性與測試 (Quality & Stability)

讓產品「能放心展示」—— 確保每個功能都不會出錯。

- [ ] **後端 pytest 測試套件** — 為所有 22 個 API endpoint 寫單元測試
- [ ] **前端 E2E 測試** — Playwright 自動化測試關鍵用戶流程
- [ ] **API 錯誤處理統一** — 標準 error response 格式 + 友善錯誤訊息
- [ ] **效能優化** — 大量 grid cells 地圖渲染最佳化、API response caching (Redis)
- [ ] **CI/CD** — GitHub Actions: lint → test → build → deploy to Vercel

### Phase 3B：接入更多資料 (Data Integration)

讓數據更豐富、更即時，增加產品說服力。

| 資料源 | 用途 | 現狀 |
|--------|------|------|
| ERA5 再分析 | 歷史風場月/季平均統計 | ✅ ingest 模組已完成 (`src/ingest/era5.py`)，需接入 API |
| 民航局空域 | 即時限航區/NOTAM | ✅ ingest 模組已完成 (`src/ingest/caa_airspace.py`)，需接入前端 |
| NLSC 建築物 | 3D 建築模型 | ✅ ingest 模組已完成 (`src/ingest/nlsc_buildings.py`) |
| ESA WorldCover | 土地覆蓋分類 | ✅ ingest 模組已完成 (`src/ingest/esa_worldcover.py`) |
| GHS-BUILT-H | 全球建築高度 | ✅ ingest 模組已完成 (`src/ingest/ghs_built_h.py`) |
| DEM 地形 | 數值高程模型 | ✅ ingest 模組已完成 (`src/ingest/dem_terrain.py`) |
| CWA 警特報 | 即時氣象警報 | 🔲 需新開發 |
| 更多城市 | 高雄/台中/新竹 | 🔲 需匯入新城市 grid data |

**優先順序**：ERA5 歷史資料 → 民航局空域 → 氣象警報 → 更多城市

### Phase 3C：商業功能 (Business Features)

讓產品「能賣出去」—— 針對不同客群提供核心價值。

**🎯 目標客群與對應功能：**

| 客群 | 需求 | 功能 |
|------|------|------|
| 無人機物流/運營商 | 飛行前風險評估、路線規劃 | 飛行計畫儲存 + PDF 報告匯出 + 即時風險警報 |
| 保險公司 | 區域風險數據、理賠依據 | 歷史風險統計報告 + API 數據訂閱 |
| 政府/都市規劃 | 城市風廊分析、法規合規 | 風廊影響評估報告 + 空域管理整合 |

**功能開發清單：**

- [ ] **用戶系統** — Supabase Auth（登入/註冊/角色管理）
- [ ] **飛行計畫儲存** — 用戶可保存分析結果和路線規劃
- [ ] **PDF 報告升級** — 包含圖表、地圖截圖、風險摘要
- [ ] **API Key 管理** — 供第三方系統串接（付費方案用）
- [ ] **多語系 i18n** — 中/英/日 切換（國際展示用）
- [ ] **使用量追蹤** — 為未來計費做基礎
- [ ] **即時風險推播** — WebSocket 通知高風險警報

### Phase 3D：部署與營運 (Deployment & Operations)

讓產品「穩定運行」—— 可靠的 production 環境。

- [ ] **Vercel 正式部署** — 連接 GitHub repo，push to main 自動部署
- [ ] **自訂域名** — 綁定品牌域名 + SSL
- [ ] **環境變數管理** — Vercel Dashboard 設定 production secrets
- [ ] **監控告警** — Sentry（錯誤追蹤）+ Vercel Analytics（流量）
- [ ] **CDN 優化** — 靜態資源快取策略
- [ ] **備份策略** — Supabase 自動備份 + 手動快照

---

## 部署指南 Deployment

### Vercel 部署（推薦）

1. **連接 GitHub repo**：Vercel Dashboard → New Project → Import repo
2. **設定環境變數**：Settings → Environment Variables，從 `.env.example` 填入
3. **Build 設定**：
   - Framework: Vite
   - Build Command: `cd web && npm run build`
   - Output Directory: `web/dist`
4. **自動部署**：push to `main` branch 觸發部署

已有 `vercel.json` 設定：
- `/api/v1/*` → Python serverless function
- `/*` → React SPA (static files)

### 本機全端執行

```bash
# Terminal 1: 後端
pip install -r requirements.txt
uvicorn src.api.main:app --reload --port 8000

# Terminal 2: 前端（proxy 到後端）
cd web
npm install
npm run dev
```

前端 Vite dev server 會自動 proxy `/api/*` 到後端。

---

## API 端點一覽 API Reference

| Method | Path | 說明 |
|--------|------|------|
| GET | `/health` | 健康檢查 |
| GET | `/api/v1/stats` | 儀表板統計數據 |
| GET | `/api/v1/grids` | Grid cells 地圖資料 |
| GET | `/api/v1/wind-rose` | 風花圖 16 方位資料 |
| GET | `/api/v1/fai` | FAI 散佈圖資料 |
| GET | `/api/v1/corridors` | 風廊列表 |
| GET/POST | `/api/v1/wind` | 指定座標風場查詢 |
| GET/POST | `/api/v1/risk` | 指定座標風險評估 |
| POST | `/api/v1/risk/batch` | 批次風險查詢 |
| POST | `/api/v1/area/predict` | 區域風場分析 |
| POST | `/api/v1/route/analyze` | 路線風場分析 |
| POST | `/api/v1/route/plan` | 最優路線規劃 |
| POST | `/api/v1/report/generate` | 生成 PDF 報告 |
| GET | `/api/v1/forecast` | 即時天氣預報 |
| GET | `/api/v1/forecast/at` | 指定座標天氣預報 |
| GET | `/api/v1/forecast/stations` | CWA 測站列表 |
| GET | `/api/v1/monitor` | 系統監控狀態 |
| GET | `/api/v1/test-results` | 測試結果 |
| POST | `/api/v1/test-results/run` | 觸發測試執行 |

---

## 開發注意事項 Development Notes

- **前端開發**：所有 UI 文字使用中文
- **API fallback**：當 DB 無法連線時，API 會返回 demo/mock 資料（見 `src/api/fallback.py`）
- **地圖 token**：MapLibre GL 不需要 API key（使用開源 tile server）
- **Git 分支**：feature branches 使用 `claude/` prefix
- **Lint**：`cd web && npm run lint`
- **Type check**：`cd web && npx tsc --noEmit`
