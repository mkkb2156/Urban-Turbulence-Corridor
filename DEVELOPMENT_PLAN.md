# UTC 開發計畫 — 免費開放資料 Demo 建構

> 最後更新：2026-03-04
> 狀態：Phase 1 核心模組完成，Vercel 部署修復中，待真實資料驗證

---

## 零、Phase 1 實際完成度盤點

### 已完成模組（含完整邏輯，非 stub）

| 模組 | 檔案 | 狀態 | 說明 |
|------|------|------|------|
| 網格系統 | `src/morphology/grid.py` | **完成** | 100m 正方形網格，支援多城市 bbox |
| BCR | `src/morphology/bcr.py` | **完成** | 建蔽率計算，spatial join + overlay |
| FAI | `src/morphology/fai.py` | **完成** | 16 方向正面面積指數，投影寬度法 |
| SVF | `src/morphology/svf.py` | **完成** | 基於 BCR/Hav 近似估算（非魚眼法） |
| 粗糙度 | `src/morphology/roughness.py` | **完成** | Grimmond & Oke 1999 形態學法，z₀ + zd |
| 對數風剖面 | `src/wind/log_profile.py` | **完成** | 50/80/120m 三高度風速降尺度 |
| LCP 風廊 | `src/wind/lcp.py` | **完成** | scipy shortest_path，FAI→cost surface→LCP |
| 風廊分類 | `src/wind/corridor.py` | **完成** | 主廊道/次廊道分級 |
| 風險分類 | `src/risk/classifier.py` | **完成** | 綠/黃/紅/黑四級 |
| 綜合評分 | `src/risk/score.py` | **完成** | 多因子加權 0-100 分 |
| Pipeline | `scripts/run_pipeline.py` | **完成** | 9 步驟完整串接，CLI 介面 |

### 資料擷取模組

| 模組 | 檔案 | 狀態 | 說明 |
|------|------|------|------|
| Open-Meteo | `src/ingest/open_meteo.py` | **完成** | 歷史 + 即時 API，含付費 key 支援 |
| CWA 氣象 | `src/ingest/cwa_weather.py` | **完成** | 自動氣象站觀測 API |
| OSM 建築 | `src/ingest/osm_buildings.py` | **完成** | Overpass API 擷取 + 高度填補 |
| 合成建築 | `scripts/generate_buildings.py` | **完成** | 3,800 棟仿真建物（demo 用） |

### Web 前端（React + TypeScript + Vite）

| 頁面 | 檔案 | 狀態 |
|------|------|------|
| Dashboard | `web/src/pages/DashboardPage.tsx` | **完成** — 統計卡片、風花圖、風險分布 |
| 風廊地圖 | `web/src/pages/CorridorPage.tsx` | **完成** — Leaflet 互動地圖 + GridPopup |
| 風險地圖 | `web/src/pages/RiskPage.tsx` | **完成** — 風險等級色彩圖 |
| 適飛評估 | `web/src/pages/FAIPage.tsx` | **完成** — 無人機適飛性檢查 |
| 測試面板 | `web/src/pages/TestDashboardPage.tsx` | **完成** — 測試結果視覺化 |

### API 後端（FastAPI）

| 路由 | 檔案 | 端點 |
|------|------|------|
| Dashboard | `src/api/routes/dashboard.py` | `/api/v1/dashboard/stats`, `/wind-rose`, `/risk-distribution` |
| Corridor | `src/api/routes/corridor.py` | `/api/v1/corridors` |
| Risk | `src/api/routes/risk.py` | `/api/v1/risk` |
| Wind | `src/api/routes/wind.py` | `/api/v1/wind/profile`, `/current` |
| Tests | `src/api/routes/tests.py` | `/api/v1/tests/run`, `/results` |

### 部署

| 項目 | 狀態 |
|------|------|
| Vercel 設定 (`vercel.json`) | **完成** — Python API + Static SPA |
| build-backend 修正 | **完成** — `setuptools.build_meta` |
| 依賴精簡 | **完成** — 33 packages（API），重型套件移至 `[pipeline]` |
| uv.lock | **完成** — Vercel `uv sync --locked` 可用 |
| Supabase 環境變數 | **待設定** — DB_HOST/PORT/NAME/USER/PASSWORD |

### 測試

| 類型 | 數量 | 涵蓋 |
|------|------|------|
| Python 測試 | 17 個檔案 | grid, bcr, fai, svf, roughness, corridor, classifier, score, api, buildings, drone_specs, wind_rose, street_canyon |
| Web 測試 | 8 個檔案 | types, colors, format, geo, components |

### 目前缺口

| 缺口 | 影響 | 解法 |
|------|------|------|
| **建築資料仍為合成資料** | 所有形態指標的真實性 | Step 1 取得真實資料 |
| **Pipeline 未跑過真實資料** | 無法驗證計算結果 | Step 4 跑一輪完整 pipeline |
| **Supabase 未設定** | API 無法連線 | 在 Vercel 設定環境變數 |
| **地形 DEM 未整合** | 粗糙度精度受限 | Phase 2 再處理 |

---

## 一、資料下載連結總表

### 建築物資料（最關鍵 — Demo 必備）

| 資料 | URL | 格式 | 說明 |
|------|-----|------|------|
| **NLSC 3D 建物模型** | https://whgis-nlsc.moi.gov.tw/Opendata/Files.aspx | SHP/GML | 國土測繪中心開放資料，需註冊帳號，含建物輪廓+高度 |
| **NLSC 圖資商店** | https://maps.nlsc.gov.tw/S09SOA/homePage.action?Language=ZH | WFS | 圖資商店介面，可下載 3D 建物圖資 |
| **NLSC WFS 服務** | https://wfs.nlsc.gov.tw/ | WFS | 直接用 QGIS 或程式串接 WFS 取建物 |
| **台北市 3D 模型（LOD1）** | https://3d.taipei/ | 需申請 | 台北市政府 3D 城市模型，含真實建物高度 |
| **sheethub/tpe3d（GitHub 快速取得）** | https://github.com/sheethub/tpe3d | GeoJSON | 社群擷取的台北 3D 建築資料，可直接用 |
| **OSM 建築輪廓（透過 Overpass）** | `python -m src.ingest.osm_buildings --city taipei` | Python | 已有模組，但高度資料不完整 |
| **GHS-BUILT-H 建築高度** | https://ghsl.jrc.ec.europa.eu/download.php?ds=bu_h | GeoTIFF | 全球 100m 網格建築高度估算（MAE 2.27m） |
| **GHS-OBAT 個體建築高度** | https://ghsl.jrc.ec.europa.eu/datasets.php | CSV/Parquet | 個體建築高度屬性，含台灣（透過 Overture Maps） |
| **WSF 3D（DLR）** | https://geoservice.dlr.de/web/datasets/wsf_3d | GeoTIFF | 90m 平均建築高度/建蔽率，全球覆蓋 |

### 地形 DEM/DSM

| 資料 | URL | 解析度 | 說明 |
|------|-----|--------|------|
| **台灣 20m DTM** | https://data.gov.tw/dataset/35430 | 20m | 政府公開地形數值模型 |
| **台灣 20m DSM** | https://data.gov.tw/dataset/175240 | 20m | 數值地表模型（含建物和植被） |
| **Copernicus GLO-30 DEM** | https://copernicus-dem-30m.s3.amazonaws.com/readme.html | 30m | AWS S3 免認證直接下載 |
| **FABDEM（裸地 DTM）** | https://data.bris.ac.uk/data/dataset/s5hqmjcdj8yo2ibzi9b4ew3sn | 30m | 去除建築和樹木的 DTM（非商業免費） |
| **NLSC 數值地形模型** | https://www.nlsc.gov.tw/cp.aspx?n=1853 | 20m | 國土測繪中心 DEM 下載頁面 |

### 風場與氣象資料

| 資料 | URL | 說明 |
|------|-----|------|
| **CWA 開放資料平台** | https://opendata.cwa.gov.tw/ | 中央氣象署 API，需免費註冊取得 API Key |
| **CWA 自動氣象站（O-A0001-001）** | https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0001-001 | 含風速 WDSD、風向 WDSE、陣風 GUST，每 10 分鐘更新 |
| **CWA 10 分鐘綜觀站（O-A0003-001）** | https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0003-001 | 最高頻率免費風場觀測 |
| **CWA WRF 3km 模式輸出** | https://data.gov.tw/dataset/58977 | 區域預報模式（M-A0064 系列） |
| **CWA GFS 預報資料** | https://data.gov.tw/en/datasets/40311 | 全球預報系統台灣區域 |
| **Open-Meteo API** | https://api.open-meteo.com/v1/forecast | 已整合，提供 10/80/120/180m 風速 |
| **Open-Meteo 歷史 API** | https://archive-api.open-meteo.com/v1/archive | 歷史逐時風場資料 |
| **ERA5 再分析（Copernicus CDS）** | https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels | 1940 至今逐時全球再分析，需免費註冊 |
| **ERA5 氣壓層資料** | https://cds.climate.copernicus.eu/datasets/reanalysis-era5-pressure-levels | 37 氣壓層風場資料 |
| **GFS（NOAA 原始）** | https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl | 0.25° 每 6 小時更新，無需註冊 |
| **Global Wind Atlas** | https://globalwindatlas.info/area/Taiwan | 250m 解析度台灣風場氣候學（10-200m 高度） |
| **IGRA 探空資料（板橋站）** | https://www.ncei.noaa.gov/products/weather-balloon/integrated-global-radiosonde-archive | 垂直風場剖面，站號 46692 |
| **懷俄明大學探空** | https://weather.uwyo.edu/upperair/sounding.html | 選 46692 Banqiao 站 |
| **Visual Crossing** | https://www.visualcrossing.com/weather-api | 10/50/80/100m 多高度風速（免費 1000 筆/日） |

### 土地覆蓋與植被

| 資料 | URL | 解析度 | 說明 |
|------|-----|--------|------|
| **ESA WorldCover v200** | https://worldcover2021.esa.int/ | 10m | 全球土地覆蓋分類（含建成區/樹木/草地） |
| **Meta/WRI 全球樹冠高度** | https://sustainability.atmeta.com/blog/2024/04/22/using-artificial-intelligence-to-map-the-earths-forests/ | 1m | 超高解析度樹冠高度，透過 GEE 取得 |
| **GEE 樹冠高度 catalog** | https://gee-community-catalog.org/projects/canopy/ | 1m | Google Earth Engine 存取方式 |

### 無人機空域

| 資料 | URL | 說明 |
|------|-----|------|
| **CAA 遙控無人機管理系統** | https://drone.caa.gov.tw/ | 台灣無人機空域查詢 |
| **CAA 空域 GIS 圖層** | https://drone.caa.gov.tw/（地圖頁面） | 禁限航區 shapefile |
| **台北市無人機活動區域** | https://dot.gov.taipei/ | 台北市核准飛行區域 |

### 道路與基礎設施

| 資料 | URL | 格式 | 說明 |
|------|-----|------|------|
| **OSM 台灣 PBF** | https://download.geofabrik.de/asia/taiwan.html | PBF | 完整 OpenStreetMap 台灣資料 |
| **台灣國土利用調查** | https://data.gov.tw/dataset/32563 | SHP | 土地利用分類 |

### 補充感測器資料

| 資料 | URL | 說明 |
|------|-----|------|
| **環境部空品站** | https://data.moenv.gov.tw/ | 台北多站逐時風速風向（士林/中山/萬華/松山/大同/古亭） |
| **民生公共物聯網** | https://ci.taiwan.gov.tw/ | SensorThings API，數千感測器 |
| **OpenSky Network** | https://opensky-network.org/ | ADS-B 航機追蹤（學術免費） |

---

## 二、Demo 最快路徑：信義區 + 大安區 Pilot

### 目標

在 pilot 區（bbox `[121.535, 25.020, 121.575, 25.050]`，約 3km x 3km）
產出可互動的風廊風險地圖：

- 100m 網格的 FAI 值（NE + SW 兩主風向）
- LCP 風廊路徑
- 50m/80m/120m 對數風速剖面估算
- 綠/黃/紅/黑風險等級

### Step 1：取得建築資料（最關鍵）

**方案 A（最快 — 已有模組）：OSM + GHS-BUILT-H 高度補完**

```bash
# OSM 建築擷取（已有 src/ingest/osm_buildings.py）
python -m src.ingest.osm_buildings --city taipei_pilot

# 下載 GHS-BUILT-H 信義區切片
# https://ghsl.jrc.ec.europa.eu/download.php?ds=bu_h
# 選 R2023A / 100m / Epoch 2018 / Tile: R9_C19（含台灣）
# 下載後用 rasterio 裁切至 pilot 區範圍，補完 OSM 缺失高度
```

**方案 B（較佳品質）：sheethub/tpe3d GeoJSON**

```bash
git clone https://github.com/sheethub/tpe3d.git
# 內含台北市 3D 建築 GeoJSON，篩選 pilot 區範圍
```

**方案 C（最佳但需等審核）：NLSC 3D 建物**

```
1. 前往 https://maps.nlsc.gov.tw/S09SOA/
2. 註冊帳號 → 搜尋「3D 建物模型」
3. 下載台北市範圍 SHP
```

> 建議策略：先用方案 A 或 B 立即出 demo，同時申請方案 C 後續替換。

### Step 2：取得地形資料（Phase 2，可暫跳過）

```bash
# 從 data.gov.tw 下載台北 20m DTM
# https://data.gov.tw/dataset/35430
# 或 Copernicus DEM: s3://copernicus-dem-30m/Copernicus_DSM_COG_10_N25_00_E121_00_DEM/
```

### Step 3：取得風場資料（已有模組）

```bash
# Open-Meteo 歷史（已整合）
python -m src.ingest.open_meteo --city taipei --days 365

# CWA 即時（需設定 CWA_API_KEY）
python -m src.ingest.cwa_weather --region taipei
```

### Step 4：跑 Pipeline

```bash
# 一鍵執行 Phase 1 全流程
python scripts/run_pipeline.py --city taipei_pilot --grid-size 100 -v

# Pipeline 內部 9 步驟：
# 1. create_grid         → 100m 網格
# 2. load buildings      → 從 data/processed/buildings/
# 3. compute_bcr         → 建蔽率
# 4. compute_fai         → 16 方向 FAI
# 5. estimate_svf        → 天空可視因子
# 6. compute_roughness   → z₀ + zd
# 7. downscale_wind      → 50/80/120m 風速
# 8. identify_corridors  → LCP 風廊 + 分類
# 9. classify_risk       → 綠/黃/紅/黑 + 0-100 分數
#
# 輸出: data/output/taipei_pilot_grid.gpkg
#       data/output/taipei_pilot_corridors.gpkg
```

### Step 5：驗證與展示

```bash
# 方法一：灌入 Supabase PostGIS → 前端 SPA
python -m src.db.queries --import-grid data/output/taipei_pilot_grid.gpkg

# 方法二：本地啟動
uvicorn src.api.main:app --reload --port 8000
cd web && npm run dev    # http://localhost:3000
```

---

## 三、Demo 預期產出與驗證指標

完成後會有涵蓋信義區+大安區的互動地圖：

| 圖層 | 內容 | 合理性檢查 |
|------|------|-----------|
| FAI 熱力圖 | 16 方向建築正面面積指數 | 台北 101（508m）應為該區 FAI 最高 |
| 風廊路徑 | LCP 低阻力風通道 | 應沿基隆河方向（NE 季風主廊道） |
| 風速估算 | 50/80/120m 三高度 | 仁愛路/敦化南路交叉口 FAI 較低（寬大道） |
| 風險等級 | 綠/黃/紅/黑 | M30T 12 m/s 抗風上限為紅線 |
| 街谷加速 | 高樓群狹窄通道 | 信義計畫區應出現風速加速效應 |

---

## 四、Phase 2 方向（CLAUDE2.md 銜接）

| 優先序 | 項目 | 資料來源 | 說明 |
|--------|------|---------|------|
| P0 | ERA5 歷史風場統計基線 | ERA5 CDS（免費） | Weibull 分布參數 |
| P0 | CWA 10 分鐘即時風場串接 | CWA API（免費） | 即時風險更新 |
| P1 | 多高度風場剖面 | Open-Meteo + GFS（免費） | 10/80/120/180m |
| P1 | URock 快速都市風場診斷 | QGIS UMEP 外掛（免費） | CFD-lite |
| P2 | 板橋探空資料驗證 | IGRA/懷俄明大學（免費） | 垂直風剖面 ground truth |
| P2 | 環境部空品站補充風場 | MOENV API（免費） | 多點觀測校正 |
| P3 | OpenFOAM RANS 預計算 | OpenFOAM GPL（免費） | 高精度 CFD 參考場 |
| P3 | ML surrogate model | 基於 CFD 輸出 | 即時推論用 |

---

## 五、立即行動清單

### 部署收尾（今天）

- [ ] 在 Vercel Dashboard 設定 Supabase 環境變數（DB_HOST/PORT/NAME/USER/PASSWORD）
- [ ] 觸發重新部署，確認 Python 依賴安裝通過
- [ ] 測試 `/health` 與 `/api/v1/corridors` 端點

### 真實資料（本週）

- [ ] 用 `src/ingest/osm_buildings.py` 或 sheethub/tpe3d 取得信義區建築
- [ ] 下載 GHS-BUILT-H R9_C19 tile 補全建築高度
- [ ] 用 Open-Meteo 歷史 API 拉 1 年台北風場（已有模組）
- [ ] 跑 `run_pipeline.py --city taipei_pilot`，產出第一張 FAI 熱力圖
- [ ] 視覺化驗證 — 與 Google 衛星影像疊合確認 FAI 合理性

### 資料申請（本週啟動，等審核）

- [ ] 註冊 CWA API Key（如果還沒有）
- [ ] 申請 NLSC 3D 建物資料
- [ ] 申請台北市 LOD1 3D 模型（3d.taipei）
- [ ] 註冊 Copernicus CDS 帳號（ERA5 用）

### Demo 完善（下週）

- [ ] 跑 LCP + log_profile + risk classifier 全流程
- [ ] 產出 demo 互動地圖（前端 SPA 或 Folium）
- [ ] NLSC 資料到手後替換建築資料，重跑 pipeline 比對差異
- [ ] 撰寫 Phase 2 計畫（CLAUDE2.md）
