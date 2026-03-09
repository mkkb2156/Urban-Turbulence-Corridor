# UTC — Urban Turbulence Corridor

## 台灣城市風廊圖層系統 — 無人機低空作業風險評估平台

---

## 1. 產品概述

### 1.1 產品定位

UTC（Urban Turbulence Corridor）是一個**城市低空風場風險評估平台**，專為無人機運營場景設計。平台結合城市形態學分析、物理風場模型、與無人機工程參數，提供精確的飛行風險評估與路線規劃建議。

### 1.2 解決的問題

城市環境中的風場極為複雜：建築物造成的繞流、加速、湍流與遮蔽效應，使得無人機低空飛行面臨不可預測的風險。傳統氣象預報僅提供開闊地形的巨觀風速，無法反映都市街區尺度的風場特徵。

UTC 平台解決以下痛點：

| 問題 | UTC 解決方案 |
|------|------------|
| 氣象站風速無法代表街區實際風速 | 對數風速剖面降尺度 + Röckle 建築繞流模型 |
| 不知道哪些區域容易形成危險風廊 | LCP（最低成本路徑）多方向風廊辨識 |
| 無法量化風對無人機續航的影響 | drone_awe 功率模型計算電池消耗 |
| 缺乏飛行前風險評估工具 | 複合風險評分 + 適飛性檢查 + 最佳時段預測 |
| 路線規劃不考慮風場因素 | 逆風/側風分析 + 最優路線規劃 |

### 1.3 核心價值主張

```
城市形態學  ×  風場物理模型  ×  無人機工程參數  =  精準風險評估
（建築數據）   （大氣科學）      （飛行力學）       （可執行決策）
```

### 1.4 目標用戶

| 用戶群 | 需求 | 核心功能 |
|--------|------|---------|
| **無人機物流/運營商** | 飛行前風險評估、路線規劃 | 飛行計畫 + 風險報告 + 即時風險警報 + 電池續航估算 |
| **保險公司** | 區域風險數據、理賠依據 | 歷史風險統計 + API 數據訂閱 |
| **政府/都市規劃** | 城市風廊分析、法規合規 | 風廊影響評估 + 空域管理整合 + LCZ 分類 |

---

## 2. 技術架構

### 2.1 系統架構

```
┌──────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  React 18 + TypeScript + Vite + Tailwind CSS + MapLibre GL  │
│  TanStack Query (server state) + Recharts (charts)          │
└──────────────────┬───────────────────────────────────────────┘
                   │  HTTP/REST API
┌──────────────────▼───────────────────────────────────────────┐
│                    API Gateway                                │
│  ┌──────────┐ ┌────────────┐ ┌──────┐ ┌──────────────────┐  │
│  │ API Key  │ │ Rate Limit │ │ CORS │ │ Request Logging  │  │
│  │   Auth   │ │  (sliding  │ │      │ │ + Usage Tracking │  │
│  │          │ │   window)  │ │      │ │                  │  │
│  └──────────┘ └────────────┘ └──────┘ └──────────────────┘  │
├──────────────────────────────────────────────────────────────┤
│                    FastAPI Backend                            │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Routes: 26 endpoints across 13 modules               │  │
│  │  dashboard, wind, risk, corridor, forecast, derived,   │  │
│  │  area, route, report, monitor, drone_power, tests      │  │
│  └──────────────────────┬─────────────────────────────────┘  │
│  ┌────────┐ ┌───────────▼──┐ ┌──────────┐ ┌────────────┐   │
│  │Morpho- │ │    Wind      │ │   Risk   │ │  Ingest    │   │
│  │logy    │ │  Modeling    │ │Assessment│ │  (11 data  │   │
│  │(BCR,   │ │(Log Profile, │ │(Score,   │ │  sources)  │   │
│  │FAI,SVF,│ │ LCP, Röckle,│ │Derived,  │ │            │   │
│  │z0/zd,  │ │ Weibull,    │ │Power     │ │            │   │
│  │LCZ)    │ │ Wind Rose)  │ │Model)    │ │            │   │
│  └────────┘ └─────────────┘ └──────────┘ └────────────┘   │
└──────────────────┬───────────────────────────────────────────┘
                   │  SQLAlchemy + GeoAlchemy2
┌──────────────────▼───────────────────────────────────────────┐
│                  Supabase PostGIS                             │
│  9 tables: grid_cells, wind_corridors, weather_stations,     │
│  wind_observations, airspace_zones, flight_conditions,       │
│  terrain_elevation, api_keys, api_usage                      │
│  1,470 grid cells (100m × 100m) + 10 wind corridors         │
└──────────────────────────────────────────────────────────────┘
         │                              │
┌────────▼──────────┐     ┌─────────────▼─────────────┐
│    Open-Meteo     │     │   CWA 中央氣象署           │
│  風速預報 (72h)    │     │  測站觀測 (即時)           │
│  10m/80m/120m     │     │  風速/風向/陣風            │
└───────────────────┘     └───────────────────────────┘
```

### 2.2 技術棧摘要

| 層級 | 技術 | 版本 |
|------|------|------|
| **前端框架** | React + TypeScript | 18 + 5.x |
| **建置工具** | Vite | 5.x |
| **地圖引擎** | MapLibre GL JS | 4.x |
| **UI 樣式** | Tailwind CSS | 3.x |
| **圖表** | Recharts | 2.x |
| **API 狀態** | TanStack Query | 5.x |
| **後端框架** | FastAPI | 0.100+ |
| **ORM** | SQLAlchemy + GeoAlchemy2 | 2.x |
| **空間資料** | GeoPandas + Shapely | 0.14+ |
| **座標系統** | EPSG:3826 (TWD97/TM2, 內部) → EPSG:4326 (WGS84, 輸出) |
| **資料庫** | PostgreSQL + PostGIS (Supabase) | 15+ |
| **部署** | Vercel (靜態 + Python serverless) | — |

---

## 3. 目錄結構

```
Urban-Turbulence-Corridor/
├── config/
│   └── settings.py              # 全域設定（CRS、城市、常數、環境變數）
│
├── src/                         # Python 後端
│   ├── api/                     # FastAPI 應用層
│   │   ├── main.py              # App 入口 + middleware 註冊
│   │   ├── schemas.py           # 所有 Pydantic request/response models
│   │   ├── auth.py              # API Key 認證 middleware
│   │   ├── rate_limit.py        # 滑動窗口限流
│   │   ├── errors.py            # 統一錯誤處理（UTCError 階層）
│   │   ├── response.py          # Response envelope helpers
│   │   ├── logging_config.py    # Request logging + 使用量追蹤
│   │   ├── fallback.py          # DB 不可用時的 demo 資料
│   │   └── routes/              # 13 個 router 模組（26 endpoints）
│   │       ├── dashboard.py     # 統計、網格、風花圖、FAI
│   │       ├── wind.py          # 風速查詢（log_profile / rockle）
│   │       ├── risk.py          # 風險評估（單點 / 批次）
│   │       ├── corridor.py      # 風廊查詢 + 即時計算
│   │       ├── forecast.py      # 天氣預報（Open-Meteo / CWA）
│   │       ├── derived.py       # 衍生數據 + 適飛性 + 飛行時段
│   │       ├── area.py          # 區域分析（多邊形）
│   │       ├── route.py         # 路線分析 + 最優規劃
│   │       ├── report.py        # PDF 報告生成
│   │       ├── drone_power.py   # 無人機功率 / 任務可行性
│   │       ├── monitor.py       # 系統健康監控
│   │       ├── tests.py         # 測試結果追蹤
│   │       └── wind_regional.py # 區域風場
│   │
│   ├── db/                      # 資料庫層
│   │   ├── models.py            # SQLAlchemy ORM（9 張資料表）
│   │   ├── queries.py           # PostGIS 空間查詢函數
│   │   ├── session.py           # DB engine + connection pool
│   │   └── migrations/          # SQL migration 檔案
│   │       ├── 001_init_postgis.sql
│   │       ├── 002_derived_columns.sql
│   │       ├── 003_api_management.sql
│   │       ├── 004_corridor_direction.sql
│   │       └── 005_lcz_column.sql
│   │
│   ├── morphology/              # 城市形態學分析
│   │   ├── grid.py              # 網格生成與管理
│   │   ├── bcr.py               # 建築覆蓋率 (BCR)
│   │   ├── fai.py               # 正面面積指數 (FAI, 16 方向)
│   │   ├── roughness.py         # 粗糙度 z₀ / 零平面位移 zd
│   │   ├── svf.py               # 天空可視因子 (SVF)
│   │   ├── street_canyon.py     # 街道峽谷比 (H/W)
│   │   └── lcz.py               # 局地氣候區 (LCZ) 分類
│   │
│   ├── wind/                    # 風場建模
│   │   ├── log_profile.py       # 對數風速剖面降尺度
│   │   ├── lcp.py               # LCP 風廊辨識（多方向）
│   │   ├── rockle.py            # Röckle 2.5D 建築繞流模型
│   │   ├── corridor.py          # 風廊屬性分析
│   │   ├── weibull.py           # Weibull 極端風分佈
│   │   └── wind_rose.py         # 風花圖（16 方位）
│   │
│   ├── risk/                    # 風險評估
│   │   ├── score.py             # 複合風險評分 (0-100)
│   │   ├── classifier.py        # 四級風險分類
│   │   ├── derived.py           # 衍生指標（TI, shear, GF, shelter...）
│   │   ├── drone_specs.py       # 無人機規格資料庫（5 款 DJI）
│   │   └── power_model.py       # 功率/續航/航程建模
│   │
│   └── ingest/                  # 資料匯入（11 模組）
│       ├── open_meteo.py        # Open-Meteo 風速預報
│       ├── cwa_weather.py       # CWA 中央氣象署觀測
│       ├── era5.py              # ERA5 再分析歷史風場
│       ├── nlsc_buildings.py    # 台灣 NLSC 3D 建築
│       ├── osm_buildings.py     # OpenStreetMap 建築
│       ├── osm_roads.py         # OSM 道路網絡
│       ├── dem_terrain.py       # DEM 地形高程
│       ├── caa_airspace.py      # 民航局空域限制
│       ├── esa_worldcover.py    # ESA 土地覆蓋
│       ├── ghs_built_h.py       # GHS 全球建築高度
│       └── landuse.py           # 土地利用分類
│
├── web/                         # React 前端
│   └── src/
│       ├── pages/               # 8 個頁面元件
│       │   ├── DashboardPage.tsx    # 儀表板（/）
│       │   ├── AnalysisPage.tsx     # 飛行分析（/analysis）
│       │   ├── CorridorPage.tsx     # 風廊（/corridors）
│       │   ├── RiskPage.tsx         # 風險評估（/risk）
│       │   ├── FAIPage.tsx          # FAI 分析（/fai）
│       │   ├── MonitorPage.tsx      # 系統監控（/monitor）
│       │   ├── GuidePage.tsx        # 使用指南（/guide）
│       │   └── TestDashboardPage.tsx # 測試儀表板（/tests）
│       │
│       ├── components/          # 共用元件
│       │   ├── map/             # 地圖元件（WindMap, 粒子動畫, 等值線, 繪圖工具）
│       │   ├── dashboard/       # 儀表板元件（統計卡片, 風花圖, 風險分佈）
│       │   ├── drone/           # 無人機元件（選擇器, 適飛檢查, 電池影響）
│       │   ├── timeline/        # 時間軸播放器
│       │   ├── report/          # 報告匯出
│       │   ├── route/           # 路線相關
│       │   └── test-dashboard/  # 測試結果卡片
│       │
│       ├── api/                 # API 客戶端
│       │   ├── client.ts        # HTTP client（auth + retry）
│       │   ├── hooks.ts         # React Query hooks（22 個）
│       │   └── types.ts         # TypeScript 型別定義
│       │
│       ├── utils/               # 工具函數
│       │   ├── colors.ts        # 色彩系統（5 種色碼模式 + 無障礙）
│       │   ├── format.ts        # 格式化（風速、座標、時間）
│       │   └── geo.ts           # 地理計算（距離、方位、台灣邊界）
│       │
│       ├── contexts/            # React Context
│       │   └── FlightContext.tsx # 跨頁面飛行狀態共享
│       │
│       └── __tests__/           # Vitest 測試（8 檔 124 個測試）
│
└── vercel.json                  # Vercel 部署設定
```

---

## 4. 核心功能模組

### 4.1 城市形態學分析

城市形態學指標是風場建模的基礎輸入。所有指標在 100m × 100m 網格上計算。

| 指標 | 模組 | 公式/方法 | 典型範圍 | 用途 |
|------|------|----------|---------|------|
| **BCR** | `bcr.py` | 建築投影面積 / 網格面積 | 0-0.7 | 建築密度量化 |
| **FAI** | `fai.py` | Σ(建築正面投影面積 ⊥ θ) / 網格面積 | 0-2.0 | 風對建築物的阻力（16 方向） |
| **z₀** | `roughness.py` | Grimmond & Oke (1999), MacDonald (1998) | 0.1-2.0 m | 地表粗糙度，影響風速剖面 |
| **zd** | `roughness.py` | MacDonald (1998): zd = (1+α^(-λp)×(λp-1))×H_avg | 5-20 m | 零平面位移，風速從此高度開始 |
| **SVF** | `svf.py` | 1 - BCR × (2/π) × arctan(h/r) | 0.2-0.9 | 天空可見度，影響輻射與通風 |
| **LCZ** | `lcz.py` | Stewart & Oke (2012) 分類 | 1-8 | 局地氣候區，整合性城市分類 |

#### LCZ 分類對照

| LCZ | 名稱 | SVF | H/W | BCR | 高度 | 通風潛力 |
|-----|------|-----|-----|-----|------|---------|
| 1 | 密集高層 | <0.4 | >2 | >0.5 | >25m | 0.15 |
| 2 | 密集中層 | 0.3-0.6 | 0.75-2 | 0.4-0.7 | 10-25m | 0.25 |
| 3 | 密集低層 | 0.2-0.6 | 0.75-1.5 | 0.4-0.7 | 3-10m | 0.30 |
| 4 | 開放高層 | >0.5 | 0.75-1.25 | 0.2-0.4 | >25m | 0.55 |
| 5 | 開放中層 | >0.5 | 0.3-0.75 | 0.2-0.4 | 10-25m | 0.65 |
| 6 | 開放低層 | >0.6 | 0.3-0.75 | 0.2-0.4 | 3-10m | 0.75 |
| 7 | 輕量低層 | 0.2-0.5 | 1-2 | >0.6 | 2-4m | 0.20 |
| 8 | 大型低層 | >0.7 | 0.1-0.3 | 0.3-0.5 | 3-10m | 0.60 |

---

### 4.2 風場建模

#### 4.2.1 對數風速剖面（Log Profile）

將氣象站 10m 高度觀測風速降尺度至無人機飛行高度（50m / 80m / 120m）。

```
U(z) = (u* / κ) × ln((z - zd) / z₀)

u*   = 摩擦速度 (m/s)
κ    = von Kármán 常數 (0.4)
z    = 目標高度 (m)
zd   = 零平面位移 (m)
z₀   = 粗糙度長度 (m)
```

每個網格依據自身的 z₀/zd 獨立計算，反映建築形態差異。

#### 4.2.2 LCP 風廊辨識

使用最低成本路徑（Least Cost Path）演算法辨識城市通風廊道：

1. **FAI → 阻力面**：低 FAI = 低阻力（風容易通過）
2. **定義邊界**：根據風向自動選擇上風側（source）與下風側（target）
3. **Dijkstra 最短路徑**：8 連通鄰域，含對角線（√2 距離）
4. **路徑回溯**：從目標邊界回溯最低成本路徑

**多方向支援**：可計算 NE、SW、N、E、S、W、NW、SE 共 8 方向，自動合併去重（>70% 重疊門檻）。

**即時 API**：`POST /api/v1/corridors/compute` 可即時計算指定方向的風廊（~1-2 秒 / 1,470 cells）。

**支援城市**：台北、高雄、台中、新竹（可擴充）。

#### 4.2.3 Röckle 建築繞流模型

基於 Röckle (1990) 的 2.5D 診斷風場模型，考慮建築物對風場的影響：

```
建築繞流三區域：

┌─────────────┐
│             │
│  Displace-  │  Building   │  Cavity  │      Wake         │
│   ment      │  (speed=0)  │ (回流    │  (逐漸恢復)        │
│  (減速)     │             │  -0.3×U) │                    │
│             │             │          │                    │
└─────────────┘─────────────┘──────────┘────────────────────┘
     ← Ld →      ← D →       ← Lc →      ← Lw →
   1.5×W                    min(1.8W,D)   W×H/max(W,H)×3

       + 角落加速（最大 ~1.3× 參考風速）
```

高度衰減：飛行高度超過建築高度 2.5 倍時，建築效應可忽略。

#### 4.2.4 Weibull 極端風分佈

```
超越機率: P(V > v) = exp(-(v/c)^k)

k = 形狀參數（台灣城市典型 1.5-2.5）
c = 尺度參數（與平均風速相關）
```

用於評估特定風速被超越的機率，供保險與風險管理使用。

#### 4.2.5 風花圖

16 方位（N, NNE, NE, ..., NNW）的風頻率與平均風速統計，基於 Open-Meteo 365 天逐時資料。

---

### 4.3 風險評估

#### 4.3.1 複合風險評分

0-100 分綜合評估，基於多個因子加權：

| 風險等級 | 分數範圍 | 風速門檻 | 代表色 | 建議 |
|---------|---------|---------|--------|------|
| 安全 (Green) | 0-30 | ≤5 m/s | 🟢 | 可安全飛行 |
| 注意 (Yellow) | 30-60 | 5-8 m/s | 🟡 | 謹慎飛行 |
| 危險 (Red) | 60-80 | 8-12 m/s | 🔴 | 不建議飛行 |
| 禁飛 (Black) | 80-100 | >12 m/s | ⚫ | 禁止飛行 |

#### 4.3.2 衍生指標

| 指標 | 公式 | 物理意義 | 典型範圍 |
|------|------|---------|---------|
| 湍流強度 TI | `1 / ln((z-zd)/z₀)` | 風速波動劇烈程度 | 城市 0.2-0.5 |
| 風切變指數 α | `ln(U₂/U₁) / ln(z₂/z₁)` | 高度間風速變化率 | 0.1-0.5 |
| 陣風因子 GF | `1 + 3×TI×(1+0.5×FAI_max)` | 平均風到陣風倍率 | 城市 1.5-3.0 |
| 遮蔽指數 | `(1-SVF)×(1+FAI)×BCR` | 建築物遮風程度 | 0-1 |
| 最低安全高度 | `max(mean_h+20, max_h+10)` | 避障最低高度 | m AGL |
| 逆風分量 | `wind × cos(wind_dir - bearing)` | 路線逆風影響 | m/s |
| Weibull 超越率 | `exp(-(V/c)^k)` | 超過指定風速的機率 | 0-1 |

#### 4.3.3 無人機適飛性檢查

支援 5 款 DJI 無人機，含 70% 安全裕度：

| 機型 | 最大抗風 | 安全限制 (70%) | 類別 |
|------|---------|-------------|------|
| DJI Mini 4 Pro | 10.7 m/s | 7.5 m/s | 消費級 |
| DJI Air 3 | 12.0 m/s | 8.4 m/s | 消費級 |
| DJI Mavic 3 | 12.0 m/s | 8.4 m/s | 專業級 |
| DJI Matrice 30 | 15.0 m/s | 10.5 m/s | 工業級 |
| DJI Matrice 350 RTK | 15.0 m/s | 10.5 m/s | 工業級 |

#### 4.3.4 電池功率/續航建模

基於 drone_awe 方法的物理功率模型：

```
懸停功率:  P_hover = (mg)^1.5 / √(2ρA) / η
前飛功率:  P_forward = P_induced + P_parasite + P_profile
          P_parasite = 0.5 × ρ × V³ × Cd × S
含風效應:  地面速度 = √(空速² - 側風²) - 逆風
續航時間:  endurance = battery_Wh / P_total
航程:      range = endurance × groundspeed
```

提供：
- 單點功率估算（指定風速/風向 → 續航/航程/電池影響）
- 路線任務可行性（多段能量預算 → 電池是否足夠 + 推薦速度）

#### 4.3.5 最佳飛行時段預測

從 Open-Meteo 72 小時預報中，尋找連續適飛窗口（風速低於無人機安全閾值的連續時段）。

---

### 4.4 資料匯入

| 模組 | 資料源 | 用途 | 格式 |
|------|--------|------|------|
| `open_meteo.py` | Open-Meteo API | 風速預報 72h（10m/80m/120m） | JSON API |
| `cwa_weather.py` | 中央氣象署 API | 即時測站觀測 | JSON API |
| `era5.py` | Copernicus CDS | 歷史風場月/季平均 | NetCDF |
| `nlsc_buildings.py` | 台灣 NLSC | 3D 建築物足跡 + 高度 | Shapefile |
| `osm_buildings.py` | OpenStreetMap | 建築物資料 | GeoJSON |
| `osm_roads.py` | OpenStreetMap | 道路網絡 | GeoJSON |
| `dem_terrain.py` | Copernicus GLO-30 | 數值高程模型 | GeoTIFF |
| `caa_airspace.py` | 民航局 | 空域限制區 / NOTAM | GeoJSON |
| `esa_worldcover.py` | ESA WorldCover | 土地覆蓋分類 | GeoTIFF |
| `ghs_built_h.py` | GHS-BUILT-H | 全球建築高度 30m | GeoTIFF |
| `landuse.py` | 綜合 | 土地利用分類 | — |

---

### 4.5 前端頁面

| 頁面 | 路徑 | 功能 |
|------|------|------|
| **儀表板** | `/` | 1,470 網格互動地圖、風險分佈統計、風花圖、72h 預報時間軸 |
| **飛行分析** | `/analysis` | 三合一：(1) 區域分析（畫多邊形→風場統計）(2) 路線分析（畫路徑→逆風/側風）(3) 路線規劃（起終點→最優路線） |
| **風廊** | `/corridors` | 風廊列表 + 地圖標記、多方向即時計算（6 方向切換 + 多方向分析） |
| **風險評估** | `/risk` | 多色碼風險地圖（5 模式切換）、單點 / 批次 DroneCheck |
| **FAI 分析** | `/fai` | 散佈圖（地形粗糙度 vs FAI）、FAI 圖層覆蓋 |
| **系統監控** | `/monitor` | DB / Open-Meteo / CWA 服務狀態燈號、延遲統計 |
| **使用指南** | `/guide` | 產品介紹、快速入門、API 文件、資料源說明 |
| **測試儀表板** | `/tests` | 測試結果卡片、覆蓋率進度條 |

#### 地圖視覺化系統

- **Grid Cells**: 1,470 個 100m 正方形，5 種色碼模式（risk / turbulence / gust_factor / shelter / wind_speed）
- **風廊路徑**: 主要風廊（藍色）/ 次要風廊（灰色）折線
- **風箭頭**: 每個 grid 的風向指示箭頭
- **粒子動畫**: Windy 風格 Canvas overlay，800 粒子流線
- **等值線**: MapLibre native heatmap + Turf.js isolines
- **無障礙色彩**: 支援 viridis / cividis 色盲友善模式

---

## 5. API 端點一覽

### 5.1 端點列表

| Method | Path | 說明 |
|--------|------|------|
| GET | `/health` | 健康檢查（免認證） |
| **Dashboard** | | |
| GET | `/api/v1/stats` | 儀表板統計（網格數、風險分佈、風速） |
| GET | `/api/v1/grids` | 網格資料（含衍生欄位、LCZ） |
| GET | `/api/v1/wind-rose` | 風花圖 16 方位資料 |
| GET | `/api/v1/fai` | FAI 散佈圖資料 |
| **Wind** | | |
| GET/POST | `/api/v1/wind` | 風速查詢（支援 `model=rockle`） |
| **Risk** | | |
| GET/POST | `/api/v1/risk` | 風險評估（單點） |
| POST | `/api/v1/risk/batch` | 批次風險查詢（最多 100 點） |
| **Corridors** | | |
| GET | `/api/v1/corridors` | 風廊列表（含方向篩選） |
| POST | `/api/v1/corridors/compute` | 即時風廊計算（LCP 多方向） |
| **Forecast** | | |
| GET | `/api/v1/forecast` | 天氣預報（72h） |
| GET | `/api/v1/forecast/at` | 指定座標預報 |
| GET | `/api/v1/forecast/stations` | CWA 測站列表 |
| GET | `/api/v1/forecast/flight-windows` | 最佳飛行時段 |
| **Derived Data** | | |
| GET | `/api/v1/derived/{grid_id}` | 衍生指標（TI/shear/GF/shelter/alt） |
| GET | `/api/v1/derived/{grid_id}/flyability` | 適飛性檢查 |
| **Analysis** | | |
| POST | `/api/v1/area/predict` | 區域風場分析 |
| POST | `/api/v1/route/analyze` | 路線風場分析（逆風/側風） |
| POST | `/api/v1/route/plan` | 最優路線規劃 |
| **Drone Power** | | |
| POST | `/api/v1/drone/power` | 功率計算（風→續航/航程） |
| POST | `/api/v1/drone/mission` | 任務可行性（能量預算） |
| **System** | | |
| POST | `/api/v1/report/generate` | 報告生成 |
| GET | `/api/v1/monitor` | 系統監控 |
| GET | `/api/v1/test-results` | 測試結果 |
| POST | `/api/v1/test-results/run` | 觸發測試執行 |

### 5.2 API Gateway

#### 認證

- **開發模式**：`API_KEY_REQUIRED=false` 免認證
- **生產模式**：使用 `X-API-Key` header 或 `?api_key=` query param
- **公開路徑**：`/health`, `/docs`, `/openapi.json`, `/redoc`

#### 限流方案

| Plan | 限流 | 說明 |
|------|------|------|
| free | 60 次/分鐘 | 預設免費 |
| pro | 300 次/分鐘 | 付費方案 |
| enterprise | 1000 次/分鐘 | 企業方案 |
| admin | 無限制 | 管理員 |

#### 統一錯誤格式

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Grid cell not found",
    "details": {}
  }
}
```

---

## 6. 資料庫 Schema

### 6.1 核心資料表

| 資料表 | 用途 | 記錄數 | 關鍵欄位 |
|--------|------|--------|---------|
| **grid_cells** | 100m 分析網格 | 1,470 | geometry(POLYGON), BCR, SVF, FAI(NE/SW/max), wind(50m/80m/120m), risk_level, risk_score, TI, shear, GF, shelter, LCZ |
| **wind_corridors** | 風廊路徑 | 10+ | geometry(LINESTRING), corridor_class, total_cost, wind_direction, wind_direction_deg |
| **weather_stations** | 氣象測站 | — | station_id, geometry(POINT), city |
| **wind_observations** | 風場觀測時序 | — | station_id, observation_time, wind_speed, wind_direction, gust_speed |
| **airspace_zones** | 空域限制區 | — | zone_type(prohibited/restricted/airport), geometry, max_height_m |
| **flight_conditions** | 逐時飛行條件 | — | grid_id, forecast_time, wind(3 heights), risk_level, TI |
| **terrain_elevation** | 地形高程 | — | dem_elevation, slope_deg, aspect_deg |
| **api_keys** | API 認證 | — | key_hash, plan(free/pro/enterprise), rate_limit_per_min |
| **api_usage** | 使用量追蹤 | — | endpoint, method, status_code, response_time_ms |

### 6.2 Migration 歷史

| 編號 | 檔案 | 內容 |
|------|------|------|
| 001 | `init_postgis.sql` | PostGIS 啟用 + 核心表 + 索引 + trigger |
| 002 | `derived_columns.sql` | grid_cells 新增 11 個衍生欄位 |
| 003 | `api_management.sql` | api_keys + api_usage 表 |
| 004 | `corridor_direction.sql` | wind_corridors 新增風向角度欄位 |
| 005 | `lcz_column.sql` | grid_cells 新增 LCZ 分類欄位 |

---

## 7. 測試覆蓋

### 7.1 前端測試（Vitest）

- **8 個測試檔案，124 個測試案例**
- 覆蓋：API 型別驗證、元件渲染、工具函數（色彩、格式化、地理計算）

| 測試檔案 | 測試數 | 測試對象 |
|---------|--------|---------|
| `api/types.test.ts` | 20 | TypeScript 型別驗證 |
| `components/FlyabilityChecker.test.tsx` | 7 | 適飛檢查元件 |
| `components/RiskLegend.test.tsx` | 3 | 風險圖例元件 |
| `components/StatsCards.test.tsx` | 7 | 統計卡片元件 |
| `components/TestResultCard.test.tsx` | 9 | 測試結果卡片 |
| `utils/colors.test.ts` | 18 | 色彩工具函數 |
| `utils/format.test.ts` | 25 | 格式化工具函數 |
| `utils/geo.test.ts` | 35 | 地理計算工具函數 |

### 7.2 後端測試

- pytest 測試套件尚未建立，為下一階段優先項目。
