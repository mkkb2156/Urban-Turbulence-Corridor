# Urban Turbulence Corridor (UTC)

台灣城市風廊圖層系統 — 無人機低空作業風險評估平台

---

## 專案架構 Architecture

```
Frontend:  React 18 + TypeScript + Vite + Tailwind CSS + MapLibre GL
Backend:   FastAPI (Python 3.11+)
Database:  Supabase PostGIS (1,470 grid cells + 10 wind corridors + 3 預留表)
Deploy:    Vercel (static build + Python serverless)
Data:      Open-Meteo (風速預報) + CWA 中央氣象署 (測站觀測)
```

### 目錄結構

```
web/                    # React 前端
  src/pages/            # 頁面元件 (Dashboard, Analysis, Corridor, Risk, FAI, Monitor, Guide)
  src/components/       # 共用元件 (map/, dashboard/, drone/, timeline/, report/, route/, test-dashboard/)
  src/api/              # API client (auth + retry) + TypeScript 型別
  src/__tests__/        # Vitest 測試 (8 files, 124 tests)

src/                    # Python 後端
  api/                  # FastAPI app + API Gateway
    main.py             # App 入口 + middleware 註冊
    auth.py             # API Key 認證 middleware
    rate_limit.py        # 限流 middleware (sliding window)
    errors.py            # 統一錯誤處理 (UTCError hierarchy)
    response.py          # Response envelope helpers
    schemas.py           # 所有 Pydantic request/response models (集中管理)
    logging_config.py    # Request logging + 使用量追蹤
    fallback.py          # DB 不可用時的 demo 資料
    routes/              # 11 個 router 檔案 (25 endpoints)
  db/                   # SQLAlchemy models + PostGIS queries + migrations
    session.py           # 全域 engine + connection pool + get_db() dependency
    models.py            # ORM models (含 APIKey, APIUsage)
    queries.py           # PostGIS 查詢函數
    migrations/          # SQL migration 檔案 (001~003)
  ingest/               # 資料匯入模組 (CWA, Open-Meteo, ERA5, OSM, NLSC, ESA, etc.)
  morphology/           # 地形分析 (BCR, FAI, roughness, SVF, street canyon)
  risk/                 # 風險評分 + 無人機規格 + 衍生數據演算
  wind/                 # 風場模型 (corridor, log profile, Weibull, wind rose, LCP)
```

---

## 快速開始 Quick Start

### 環境變數

複製 `.env.example` → `.env`，至少填入：
- `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` — Supabase PostgreSQL 連線資訊
- `CWA_API_KEY` — 中央氣象署 API key（免費註冊）

API 管理相關（可選）：
- `API_KEY_REQUIRED` — `true` 啟用 API Key 認證（預設 `false`，開發模式免認證）
- `DEFAULT_RATE_LIMIT_PER_MIN` — 預設每分鐘請求限制（預設 60）
- `ADMIN_API_KEY` — 管理用 master key（不限流、可查看使用量）

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

# 衍生數據
curl http://localhost:8000/api/v1/derived/taipei_001_005
curl "http://localhost:8000/api/v1/derived/taipei_001_005/flyability?drone_id=dji-mini4-pro"
curl "http://localhost:8000/api/v1/forecast/flight-windows?lon=121.55&lat=25.03&drone_id=dji-mini4-pro"

# 即時天氣預報
curl "http://localhost:8000/api/v1/forecast?city=taipei"
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
| 飛行分析 | `/analysis` | 繪製區域 → 顯示分析結果；繪製路線 → 路線比較表（含逆風/側風）|
| 風廊 | `/corridors` | 10 條風廊列表、點擊展開詳情、地圖標記風廊路徑 |
| 風險評估 | `/risk` | 色碼風險地圖（多色碼模式）、DroneCheck 單點查詢、批次查詢（CSV 上傳）|
| FAI 分析 | `/fai` | 散佈圖載入、hover 顯示資訊 |
| 系統監控 | `/monitor` | DB / Open-Meteo / CWA 狀態燈號正常 |
| 使用指南 | `/guide` | 靜態頁面正常渲染 |
| 測試儀表板 | `/tests` | 測試結果卡片、覆蓋率進度條 |

### 4. 後端 Python 測試 (TODO)

目前尚未建立 pytest 測試套件，這是 Phase 3 的優先項目。

---

## 已完成功能 Completed Features

### 核心功能
- ✅ 互動式風險地圖（MapLibre GL + 色碼 grid cells + 多色碼模式切換）
- ✅ 風場粒子動畫（Windy.com 風格 Canvas overlay）
- ✅ 風花圖（Recharts 16 方位）
- ✅ 10 條台北風廊識別與地圖標註
- ✅ DroneCheck 單點 + 批次飛行適性查詢
- ✅ 區域分析（多邊形繪製 → 風場統計）
- ✅ 路線規劃與比較（路徑繪製 → 風險分析 + 逆風/側風分量）
- ✅ FAI 正面面積指數分析
- ✅ 即時天氣預報（Open-Meteo + CWA）
- ✅ PDF 報告匯出

### 衍生數據演算（Phase 3 新增）
- ✅ 湍流強度指數 (TI) — `1 / ln((z-zd)/z0)` 三高度層
- ✅ 風切變指數 — `ln(U₂/U₁) / ln(z₂/z₁)` 50↔80↔120m
- ✅ 陣風因子 (GF) — `1 + 3×TI×(1+0.5×FAI_max)`
- ✅ 建築遮蔽指數 — `(1-SVF)×(1+FAI)×BCR`
- ✅ 可用飛行高度範圍 — min_safe_alt / max_legal_alt
- ✅ 路線逆風/側風效率 — headwind / crosswind / wind_effect_pct
- ✅ Weibull 超越機率 — `P(V>threshold) = exp(-(V/c)^k)`
- ✅ 最佳飛行時段預測 — 從 72h 預報找連續適飛窗口
- ✅ 衍生數據計算模組 (`src/risk/derived.py`)

### 資料庫 Schema
- ✅ `grid_cells` — 1,470 格 + 11 個衍生欄位（TI/shear/GF/shelter/alt）
- ✅ `wind_corridors` — 10 條風廊
- ✅ `airspace_zones` — 空域限制區（結構已建，待資料填入）
- ✅ `flight_conditions` — 時序飛行條件（結構已建，待定期匯入）
- ✅ `terrain_elevation` — 地形高程（結構已建，待 DEM 資料）
- ✅ DB migration: `001_init_postgis.sql` + `002_derived_columns.sql` + `003_api_management.sql`

### API Gateway（新增）
- ✅ API Key 認證 — `X-API-Key` header 或 `?api_key=` query param
- ✅ Rate Limiting — sliding window 限流（預設 60 次/分鐘，per API Key）
- ✅ 使用量追蹤 — in-memory 記錄 per-key/per-endpoint 請求統計
- ✅ 統一錯誤處理 — `UTCError` hierarchy + 全域 exception handler
- ✅ Response envelope — `{"data": ..., "meta": {"version", "generated_at"}}`
- ✅ 集中式 Schema — 所有 Pydantic model 統一在 `src/api/schemas.py`
- ✅ DB Session 管理 — 全域 engine + connection pool + `get_db()` FastAPI dependency
- ✅ 前端 API client — auth header 注入 + 5xx exponential backoff retry

#### Middleware 執行順序（內 → 外）
```
Request → APIKeyMiddleware → RateLimitMiddleware → CORSMiddleware → RequestLoggingMiddleware → Route Handler
```

#### 公開路徑（免認證）
`/health`, `/docs`, `/openapi.json`, `/redoc`, `/assets/*`, 非 `/api/` 路徑

#### API Key 方案
| Plan | Rate Limit | 說明 |
|------|-----------|------|
| free | 60/min | 預設免費方案 |
| pro | 300/min | 付費方案（預留） |
| enterprise | 1000/min | 企業方案（預留） |
| admin | 無限制 | `ADMIN_API_KEY` 管理員 |

### 平台功能
- ✅ 全中文 UI
- ✅ 響應式設計（桌面 + 行動裝置）
- ✅ 系統監控頁面（DB / API 狀態）
- ✅ 集中式 logging + request middleware + 使用量追蹤
- ✅ Vercel 部署設定（`vercel.json`）
- ✅ 前端 Vitest 測試（8 files, 124 tests）

### 資料來源
- ✅ Supabase PostGIS — 1,470 grid cells + 10 wind corridors
- ✅ Open-Meteo — 風速/風向/陣風即時預報（10m/80m/120m）
- ✅ CWA 中央氣象署 — 測站觀測資料

---

## 下一步路線圖 Roadmap → 商業 Demo

### Phase 3A：穩定性與測試 (Quality & Stability)

讓產品「能放心展示」—— 確保每個功能都不會出錯。

- [ ] **後端 pytest 測試套件** — 為所有 25 個 API endpoint 寫單元測試
- [ ] **前端 E2E 測試** — Playwright 自動化測試關鍵用戶流程
- [x] **API 錯誤處理統一** — 標準 error response 格式 + 友善錯誤訊息（`src/api/errors.py`）
- [ ] **效能優化** — 大量 grid cells 地圖渲染最佳化、API response caching (Redis)
- [ ] **CI/CD** — GitHub Actions: lint → test → build → deploy to Vercel

### Phase 3B：接入更多資料 (Data Integration)

讓數據更豐富、更即時，增加產品說服力。

| 資料源 | 用途 | 現狀 |
|--------|------|------|
| ERA5 再分析 | 歷史風場月/季平均統計 | ✅ ingest 模組已完成，需接入 API |
| 民航局空域 | 即時限航區/NOTAM | ✅ ingest 模組已完成 + DB 表已建，需接入前端 |
| NLSC 建築物 | 3D 建築模型 | ✅ ingest 模組已完成 |
| ESA WorldCover | 土地覆蓋分類 | ✅ ingest 模組已完成 |
| GHS-BUILT-H | 全球建築高度 | ✅ ingest 模組已完成 |
| DEM 地形 | 數值高程模型 | ✅ ingest 模組已完成 + DB 表已建 |
| CWA 警特報 | 即時氣象警報 | 🔲 需新開發 |
| 更多城市 | 高雄/台中/新竹 | 🔲 需匯入新城市 grid data |

**優先順序**：ERA5 歷史資料 → 民航局空域 → 氣象警報 → 更多城市

### Phase 3C：商業功能 (Business Features)

讓產品「能賣出去」—— 針對不同客群提供核心價值。

| 客群 | 需求 | 功能 |
|------|------|------|
| 無人機物流/運營商 | 飛行前風險評估、路線規劃 | 飛行計畫儲存 + PDF 報告匯出 + 即時風險警報 |
| 保險公司 | 區域風險數據、理賠依據 | 歷史風險統計報告 + API 數據訂閱 |
| 政府/都市規劃 | 城市風廊分析、法規合規 | 風廊影響評估報告 + 空域管理整合 |

- [ ] **用戶系統** — Supabase Auth（登入/註冊/角色管理）
- [ ] **飛行計畫儲存** — 用戶可保存分析結果和路線規劃
- [ ] **PDF 報告升級** — 包含圖表、地圖截圖、風險摘要
- [x] **API Key 管理** — 供第三方系統串接（`src/api/auth.py` + `src/api/rate_limit.py`）
- [ ] **多語系 i18n** — 中/英/日 切換（國際展示用）
- [x] **使用量追蹤** — in-memory 追蹤（`src/api/logging_config.py`），DB 表已預建（`003_api_management.sql`）
- [ ] **即時風險推播** — WebSocket 通知高風險警報

### Phase 3D：部署與營運 (Deployment & Operations)

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
| GET | `/api/v1/grids` | Grid cells 地圖資料（含衍生欄位） |
| GET | `/api/v1/wind-rose` | 風花圖 16 方位資料 |
| GET | `/api/v1/fai` | FAI 散佈圖資料 |
| GET | `/api/v1/corridors` | 風廊列表 |
| GET/POST | `/api/v1/wind` | 指定座標風場查詢 |
| GET/POST | `/api/v1/risk` | 指定座標風險評估 |
| POST | `/api/v1/risk/batch` | 批次風險查詢 |
| GET | `/api/v1/derived/{grid_id}` | 網格衍生數據（TI/shear/gust/shelter/alt） |
| GET | `/api/v1/derived/{grid_id}/flyability` | 結合衍生數據的適飛性檢查 |
| GET | `/api/v1/forecast/flight-windows` | 最佳飛行時段 |
| POST | `/api/v1/area/predict` | 區域風場分析 |
| POST | `/api/v1/route/analyze` | 路線風場分析（含逆風/側風） |
| POST | `/api/v1/route/plan` | 最優路線規劃 |
| POST | `/api/v1/report/generate` | 生成 PDF 報告 |
| GET | `/api/v1/forecast` | 即時天氣預報 |
| GET | `/api/v1/forecast/at` | 指定座標天氣預報 |
| GET | `/api/v1/forecast/stations` | CWA 測站列表 |
| GET | `/api/v1/monitor` | 系統監控狀態 |
| GET | `/api/v1/test-results` | 測試結果 |
| POST | `/api/v1/test-results/run` | 觸發測試執行 |

---

## 衍生數據公式 Derived Data Formulas

| 指標 | 公式 | 來源欄位 | 合理範圍 |
|------|------|---------|---------|
| 湍流強度 TI | `1 / ln((z-zd)/z0)` | z0, zd | 城市 0.2-0.5 |
| 風切變指數 α | `ln(U₂/U₁) / ln(z₂/z₁)` | wind_50m/80m/120m | 0.1-0.5 |
| 陣風因子 GF | `1 + 3×TI×(1+0.5×fai_max)` | TI, fai_max | 城市 1.5-3.0 |
| 遮蔽指數 | `(1-SVF)×(1+FAI)×BCR` | svf, fai, bcr | 0-1 |
| 最低安全高度 | `max(mean_h+20, max_h+10)` | mean/max_height | m AGL |
| 逆風分量 | `wind × cos(wind_dir - bearing)` | 風速+路線方位 | m/s |
| Weibull 超越 | `exp(-(V/c)^k)` | weibull_k/c | 0-1 機率 |

---

## 開發注意事項 Development Notes

- **前端開發**：所有 UI 文字使用中文
- **API fallback**：當 DB 無法連線時，API 會返回 demo/mock 資料（見 `src/api/fallback.py`）
- **API 認證**：開發環境 `API_KEY_REQUIRED=false` 免認證；生產環境建議開啟，使用 `X-API-Key` header
- **前端 API client**：`web/src/api/client.ts` 已內建 auth header 注入 + 5xx retry，設定 key 用 `setApiKey()`
- **統一錯誤格式**：所有 API 錯誤回傳 `{"error": {"code": "...", "message": "...", "details": ...}}`
- **新增 Schema**：所有 request/response model 集中在 `src/api/schemas.py`，新增端點請在此檔案定義
- **DB Session**：route 中使用 `from src.db.session import get_engine, table_exists`，勿在 route 內自建 engine
- **地圖 token**：MapLibre GL 不需要 API key（使用開源 tile server + glyphs）
- **Git 分支**：feature branches 使用 `claude/` prefix
- **Lint**：`cd web && npm run lint`
- **Type check**：`cd web && npx tsc --noEmit`
- **DB migrations**：`src/db/migrations/` 目錄下的 SQL 檔案需在 Supabase SQL Editor 中手動執行
