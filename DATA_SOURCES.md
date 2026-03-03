# 資料來源清單 — UTC 城市風廊系統

## 目前使用的資料

### 1. 氣象風場資料 — Open-Meteo (真實資料)

| 項目 | 說明 |
|------|------|
| **來源** | Open-Meteo Historical Weather API |
| **網址** | https://open-meteo.com/ |
| **API 文件** | https://open-meteo.com/en/docs/historical-weather-api |
| **資料內容** | 逐時 10m 風速、風向、陣風 |
| **涵蓋範圍** | 全球，0.25° 網格解析度 (ERA5 重分析) |
| **時間範圍** | 1940 年至今（延遲約 5 天） |
| **授權** | CC BY 4.0 (免費 tier) / 付費 tier 無限制 |
| **本專案使用** | 台北中心點 (25.085°N, 121.562°E) 過去 365 天逐時資料 |
| **取得方式** | `python -m src.ingest.open_meteo --city taipei --days 365` |
| **輸出** | `data/processed/weather/taipei_wind_hourly.csv`, `taipei_wind_stats.json`, `taipei_wind_rose.json` |

> **付費 API Key 使用方式**: 在 `src/ingest/open_meteo.py` 中設定 `OPEN_METEO_API_KEY`，
> 或呼叫時傳入 `api_key` 參數。付費 tier 可取得更高解析度資料。

### 2. 建築物資料 — 合成資料 (待替換)

| 項目 | 說明 |
|------|------|
| **目前狀態** | 合成資料 — `scripts/generate_buildings.py` 產生 3,800 棟仿真建物 |
| **輸出位置** | `data/processed/buildings/taipei_buildings.gpkg` |

---

## 可替換的真實資料來源

### 2a. 建築物 — OpenStreetMap (推薦，免費)

| 項目 | 說明 |
|------|------|
| **來源** | OpenStreetMap via Overpass API |
| **網址** | https://www.openstreetmap.org/ |
| **Overpass API** | https://overpass-api.de/api/interpreter |
| **Geofabrik 下載** | https://download.geofabrik.de/asia/taiwan.html |
| **資料內容** | 建築物 footprint (polygon) + `building:levels` + `height` 標籤 |
| **授權** | ODbL (Open Data Commons Open Database License) |
| **取得方式** | `python -m src.ingest.osm_buildings --city taipei` |
| **注意** | 高度覆蓋率約 30%，缺失值用 `building:levels × 3m` 或中位數填補 |

### 2b. 建築物 — NLSC 3D 建物 (官方，需申請)

| 項目 | 說明 |
|------|------|
| **來源** | 內政部國土測繪中心 3D 建物模型 |
| **網址** | https://maps.nlsc.gov.tw/S09SOA/ |
| **資料內容** | 建物 footprint + BHEIGHT (建物高度) + 樓層 |
| **格式** | SHP / GML |
| **授權** | 需登入申請，政府開放資料授權 |
| **取得方式** | 手動下載後 → `python -m src.ingest.nlsc_buildings --city taipei` |

### 2c. 建築物 — TGOS 國土資訊 (官方)

| 項目 | 說明 |
|------|------|
| **來源** | 地理資訊圖資雲整合服務平台 |
| **網址** | https://tgos.nat.gov.tw/ |
| **資料內容** | 建物資料含部分高度 |
| **授權** | 政府開放資料 |

---

### 3. 氣象風場 — CWA 中央氣象署 (官方，已整合)

| 項目 | 說明 |
|------|------|
| **來源** | 中央氣象署開放資料平台 |
| **網址** | https://opendata.cwa.gov.tw/ |
| **API 文件** | https://opendata.cwa.gov.tw/dist/opendata-swagger.html |
| **資料集 ID** | `O-A0001-001` (自動氣象站觀測) |
| **資料內容** | 即時風速、風向、陣風、溫度等 |
| **API Key** | 免費申請 → 設定於 `.env` 的 `CWA_API_KEY` |
| **取得方式** | `python -m src.ingest.cwa_weather --region taipei` |
| **台北測站** | 臺北(466920)、鞍部(466910)、大直(C0A980)、內湖(C0A9C0)、士林(C0A9E0)、社子(C0A9F0)、信義(C0A9A0)、文山(C0ACA0)、大安森林(C0AC40) |

### 3b. 歷史氣象 — CODiS (官方)

| 項目 | 說明 |
|------|------|
| **來源** | 氣候觀測資料查詢服務 |
| **網址** | https://codis.cwa.gov.tw/ |
| **資料內容** | 歷史逐時/逐日氣象觀測（含風速風向） |
| **取得方式** | 網頁查詢匯出 CSV |
| **用途** | 建立長期風花圖統計（建議至少 1 年資料） |

---

### 4. 地形 DTM/DSM (尚未使用)

| 項目 | 說明 |
|------|------|
| **DTM 來源** | 內政部 20m 數值地形模型 |
| **DTM 網址** | https://data.gov.tw/dataset/35430 |
| **DSM 來源** | 內政部 20m 數值表面模型 |
| **DSM 網址** | https://data.gov.tw/dataset/175240 |
| **格式** | GeoTIFF |
| **解析度** | 20m |
| **授權** | 政府開放資料 |
| **取得方式** | 直接下載 → 放入 `data/raw/terrain/` → `python -m src.ingest.dem_terrain --city taipei` |

### 5. 道路網路 (尚未使用)

| 項目 | 說明 |
|------|------|
| **來源** | OpenStreetMap |
| **網址** | https://www.openstreetmap.org/ |
| **Geofabrik 下載** | https://download.geofabrik.de/asia/taiwan.html |
| **授權** | ODbL |
| **取得方式** | `python -m src.ingest.osm_roads` (需安裝 osmnx) |
| **用途** | 街谷方向分析、道路寬度估算 |

### 6. 國土利用分類 (尚未使用)

| 項目 | 說明 |
|------|------|
| **來源** | 內政部國土測繪中心 |
| **網址** | https://maps.nlsc.gov.tw/ (搜尋「國土利用」) |
| **data.gov.tw** | https://data.gov.tw/ (搜尋「國土利用調查」) |
| **格式** | SHP |
| **授權** | 政府開放資料（部分需申請） |
| **用途** | 地表粗糙度分類對照 |

---

## 資料替換優先順序

| 優先 | 資料 | 原因 | 難度 |
|------|------|------|------|
| 1 | **建築物 → OSM** | 影響所有形態指標 (BCR/FAI/SVF)，是分析基礎 | 低 — 只需網路連線 |
| 2 | **建築物 → NLSC** | 官方資料，高度最準確 | 中 — 需申請帳號 |
| 3 | **地形 DTM** | 可改善粗糙度計算精度 | 低 — 直接下載 |
| 4 | **道路 → OSM** | 街谷分析用 | 低 — 直接下載 |
| 5 | **國土利用** | 輔助粗糙度分類 | 中 — 需申請 |

## Open-Meteo 付費版 vs 免費版

| 功能 | 免費 | 付費 |
|------|------|------|
| 歷史資料 | ERA5 (0.25°, ~25km) | ERA5-Land (0.1°, ~9km) |
| 更新延遲 | ~5 天 | ~2 天 |
| API 限制 | 10,000 calls/day | 依方案 |
| 高度修正 | 有 | 有 (更精確) |

**建議**: 免費版 ERA5 已足夠作為參考風速。付費版的 ERA5-Land 可提供更高解析度。
台北盆地內風速空間變異主要由建物形態（FAI/BCR）和對數風速剖面模型處理，
Open-Meteo 只提供單點參考風速，不需要極高解析度。
