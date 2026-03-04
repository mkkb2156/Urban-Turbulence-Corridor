# Phase 2 計畫 — 真實資料整合與前端上傳處理

> 最後更新：2026-03-04
> 前置條件：Phase 1 模組全部完成，Vercel 部署修復完成

---

## 一、架構限制與設計決策

### 現有限制

| 限制 | 值 | 影響 |
|------|---|------|
| Vercel Lambda 大小 | 50 MB | Python 依賴已精簡至 33 packages |
| Vercel Lambda timeout | 10s（Hobby）/ 60s（Pro） | 不能在 Lambda 內跑 pipeline |
| Supabase Storage | 1 GB（免費）/ 100 GB（Pro） | 大檔案暫存可用 |
| Supabase DB | 500 MB（免費）/ 8 GB（Pro） | PostGIS 網格資料足夠 |
| GitHub 檔案上限 | 100 MB | GeoTIFF / SHP 無法直接上傳 |

### 大檔案處理策略

```
使用者瀏覽器 → Supabase Storage（暫存原始檔）
                    ↓
             本機 / GitHub Actions（跑 pipeline）
                    ↓
             Supabase PostGIS（寫入計算結果）
                    ↓
             Vercel API（讀取 PostGIS → 前端）
```

**核心原則**：Vercel 只負責讀取（API serving），不負責計算。重運算在本機或 CI 完成。

---

## 二、你需要提供的資料

### P0 必備（Demo 最低需求）

| # | 資料 | 預估大小 | 取得方式 | 我需要你做什麼 |
|---|------|---------|---------|---------------|
| 1 | **建築物 SHP/GeoJSON** | 10-200 MB | OSM（自動）或 NLSC（手動申請） | 方案 A：什麼都不用做，我用 OSM 模組自動下載。方案 B：如果有 NLSC 3D 建物，把 SHP 放到 `data/raw/buildings/` |
| 2 | **CWA API Key** | 字串 | https://opendata.cwa.gov.tw/ 免費註冊 | 註冊後把 key 貼到 `.env` 的 `CWA_API_KEY` |
| 3 | **Supabase 連線資訊** | 字串 | Supabase Dashboard → Settings → Database | 提供 DB_HOST, DB_PORT, DB_USER, DB_PASSWORD |

### P1 品質提升

| # | 資料 | 預估大小 | 取得方式 | 說明 |
|---|------|---------|---------|------|
| 4 | **GHS-BUILT-H GeoTIFF** | ~500 MB（全球 tile） | https://ghsl.jrc.ec.europa.eu/download.php?ds=bu_h | 補完 OSM 缺失的建築高度。下載 R9_C19 tile |
| 5 | **台灣 20m DTM** | ~200 MB | https://data.gov.tw/dataset/35430 | 地形影響粗糙度計算 |
| 6 | **sheethub/tpe3d** | ~50 MB | `git clone https://github.com/sheethub/tpe3d` | 台北 3D 建築備用方案 |

### P2 進階（Phase 2 後期）

| # | 資料 | 預估大小 | 取得方式 | 說明 |
|---|------|---------|---------|------|
| 7 | **NLSC 3D 建物 SHP** | 1-2 GB（全台北） | https://maps.nlsc.gov.tw/S09SOA/ 申請 | 最高品質建築資料 |
| 8 | **ERA5 NetCDF** | ~500 MB/年 | Copernicus CDS 申請 | 歷史風場統計基線 |
| 9 | **台北市 LOD1 3D 模型** | 未知 | https://3d.taipei/ 申請 | 官方 3D 城市模型 |

---

## 三、大檔案處理方案

### 方案比較

| 方案 | 優點 | 缺點 | 適用情境 |
|------|------|------|---------|
| **A. Supabase Storage + Edge Function** | 前端上傳、自動化 | 處理時間受限、需寫轉換邏輯 | 小檔案（< 50MB SHP/GeoJSON） |
| **B. 本機跑 pipeline → DB 匯入** | 無大小限制、完整 pipeline | 需本機環境 | 大檔案（GeoTIFF、全市 SHP） |
| **C. GitHub Actions CI** | 自動化、可重現 | 設定較複雜、runner 有空間限制 | 定期更新（風場資料排程） |

### 建議組合

```
小檔案（< 50 MB）→ 方案 A：前端上傳 → Supabase Storage → Edge Function 處理
大檔案（> 50 MB）→ 方案 B：本機 pipeline → 直接寫入 Supabase PostGIS
定期更新          → 方案 C：GitHub Actions 排程拉 CWA/Open-Meteo → 寫入 DB
```

---

## 四、前端上傳功能設計

### 4.1 架構

```
[React 前端]                    [Supabase]                    [處理層]
     │                              │                              │
     ├─ 選擇檔案 (SHP/GeoJSON)     │                              │
     ├─ 上傳至 ──────────────────→ Storage bucket                  │
     │                         (raw-uploads/)                      │
     ├─ 呼叫處理 API ─────────────→ Edge Function ────────────────→│
     │                              │  讀取檔案                     │
     │                              │  解析 geometry               │
     │                              │  裁切至 bbox                 │
     │                              │  寫入 PostGIS                │
     ├─ 輪詢狀態 ←──────────────── processing_jobs 表              │
     │                              │                              │
     └─ 完成 → 刷新地圖            │                              │
```

### 4.2 Supabase 設定

```sql
-- Storage bucket
INSERT INTO storage.buckets (id, name, public)
VALUES ('raw-uploads', 'raw-uploads', false);

-- 處理任務追蹤表
CREATE TABLE processing_jobs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    file_path TEXT NOT NULL,          -- Storage 內路徑
    file_type TEXT NOT NULL,          -- 'buildings_shp', 'buildings_geojson', 'dem_tiff'
    city TEXT NOT NULL DEFAULT 'taipei',
    status TEXT NOT NULL DEFAULT 'pending',  -- pending/processing/completed/failed
    result JSONB,                     -- 處理結果摘要
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

-- RLS policy
ALTER TABLE processing_jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users see own jobs" ON processing_jobs
    FOR SELECT USING (auth.uid() = user_id);
```

### 4.3 可透過前端上傳的檔案類型

| 類型 | 格式 | 大小限制 | 處理方式 |
|------|------|---------|---------|
| 建築物 | `.geojson`, `.json` | 50 MB | Edge Function 直接解析 → PostGIS |
| 建築物 | `.shp` + `.shx` + `.dbf` + `.prj`（ZIP） | 50 MB | Edge Function 解壓 → 解析 → PostGIS |
| 風場 CSV | `.csv` | 10 MB | Edge Function 解析 → 統計 → PostGIS |
| 網格結果 | `.gpkg` | 50 MB | Edge Function 解析 → PostGIS |

> GeoTIFF（DEM、GHS-BUILT-H）因為太大且需要 rasterio，**不適合前端上傳**，
> 建議在本機處理後匯入。

### 4.4 前端上傳元件（新增頁面）

```
/upload 頁面
├── 拖放區域（接受 .zip / .geojson / .csv / .gpkg）
├── 檔案類型選擇（建築物 / 風場 / 網格結果）
├── 城市選擇（taipei / taipei_pilot / 自訂 bbox）
├── 上傳進度條
├── 處理狀態追蹤（pending → processing → completed）
└── 完成後「查看地圖」按鈕
```

---

## 五、Phase 2 Task 清單

### Sprint 1：真實資料驗證（本週）

| Task | 說明 | 依賴 |
|------|------|------|
| **T1.1** 用 OSM 模組下載信義區建築 | `python -m src.ingest.osm_buildings --city taipei_pilot` | 網路連線 |
| **T1.2** 用 Open-Meteo 拉 1 年歷史風場 | `python -m src.ingest.open_meteo --city taipei --days 365` | 網路連線 |
| **T1.3** 跑完整 pipeline | `python scripts/run_pipeline.py --city taipei_pilot -v` | T1.1 + T1.2 |
| **T1.4** 視覺化驗證 FAI | 疊合 Google 衛星影像，檢查 101 區域 FAI 最高 | T1.3 |
| **T1.5** 匯入 Supabase PostGIS | `python -m src.db.queries --import-grid data/output/taipei_pilot_grid.gpkg` | T1.3 + Supabase 連線 |
| **T1.6** 設定 Vercel 環境變數 | DB_HOST/PORT/NAME/USER/PASSWORD | Supabase 連線資訊 |
| **T1.7** 部署驗證 | `/health` + `/api/v1/corridors?city=taipei_pilot` | T1.5 + T1.6 |

### Sprint 2：前端上傳功能（下週）

| Task | 說明 | 依賴 |
|------|------|------|
| **T2.1** Supabase Storage bucket 設定 | 建立 `raw-uploads` bucket + RLS | Supabase 專案 |
| **T2.2** 建立 `processing_jobs` 表 | SQL migration | Supabase 專案 |
| **T2.3** Supabase Edge Function：處理建築 GeoJSON | 解析 → 裁切 bbox → 寫入 PostGIS | T2.1 + T2.2 |
| **T2.4** Supabase Edge Function：處理建築 SHP（ZIP） | 解壓 → 解析 → 裁切 → 寫入 | T2.3 |
| **T2.5** Supabase Edge Function：處理風場 CSV | 解析 → 統計 → 寫入 | T2.3 |
| **T2.6** 前端 Upload 頁面 | React 拖放上傳 + 進度 + 狀態追蹤 | T2.1 |
| **T2.7** 上傳後自動觸發 pipeline（輕量版） | Edge Function 裁切 + 基本統計，重計算仍需本機 | T2.3-T2.5 |

### Sprint 3：風場進階整合（第 3-4 週）

| Task | 說明 | 依賴 |
|------|------|------|
| **T3.1** CWA 即時風場串接 | 每 10 分鐘更新，寫入 DB | CWA API Key |
| **T3.2** GitHub Actions：排程風場更新 | cron: 每小時拉 CWA + Open-Meteo | T3.1 |
| **T3.3** ERA5 歷史統計基線 | Weibull 分布參數，台北多站 | ERA5 帳號 + 本機處理 |
| **T3.4** 多高度風場剖面 API | `/api/v1/wind/profile?heights=10,50,80,120,180` | T3.1 |
| **T3.5** 風花圖即時更新 | Dashboard 風花圖接 DB 而非 mock | T3.1 + T3.2 |

### Sprint 4：建築資料品質提升（第 4-5 週）

| Task | 說明 | 依賴 |
|------|------|------|
| **T4.1** GHS-BUILT-H 高度補完腳本 | rasterio 裁切 + OSM 高度合併 | GHS-BUILT-H tile 下載 |
| **T4.2** NLSC 3D 建物匯入模組 | SHP → 高度清洗 → GeoPackage | NLSC 資料到手 |
| **T4.3** 建築資料品質比較報告 | OSM vs NLSC vs GHS-BUILT-H 的 MAE 分析 | T4.1 + T4.2 |
| **T4.4** 地形 DTM 整合 | 粗糙度計算加入地形因子 | DTM 下載 |

### Sprint 5：前端增強（第 5-6 週）

| Task | 說明 | 依賴 |
|------|------|------|
| **T5.1** 即時風險指示器 | 地圖上顯示當前風速 + 風險等級 | T3.1 |
| **T5.2** 時間軸播放器 | 查看歷史 24 小時風場變化 | T3.2 |
| **T5.3** 無人機航路規劃 | 在風廊地圖上繪製航路 → 評估風險 | Sprint 1 |
| **T5.4** 多城市支援 | 新竹、台中、高雄 config | Sprint 1-4 |

---

## 六、本機 Pipeline 操作指南（大檔案）

對於無法上傳至 GitHub 或前端的大檔案：

### 環境設定

```bash
# 建立本機開發環境
uv venv && source .venv/bin/activate
uv pip install -e ".[pipeline,dev]"

# 設定 Supabase 連線（.env）
DB_HOST=db.<project-ref>.supabase.co
DB_PORT=6543
DB_NAME=postgres
DB_USER=postgres.<project-ref>
DB_PASSWORD=<your-password>
```

### 大檔案處理流程

```bash
# 1. 把大檔案放到 data/raw/（已 gitignore）
cp ~/Downloads/GHS_BUILT_H_R9_C19.tif data/raw/terrain/
cp ~/Downloads/NLSC_buildings_taipei.shp data/raw/buildings/

# 2. 跑 pipeline（自動讀取 data/raw → 處理 → data/output）
python scripts/run_pipeline.py --city taipei_pilot --grid-size 100 -v

# 3. 匯入 Supabase PostGIS
python -m src.db.queries --import-grid data/output/taipei_pilot_grid.gpkg

# 4. 驗證
curl "https://<your-app>.vercel.app/api/v1/corridors?city=taipei_pilot"
```

### .gitignore 已包含

```
data/raw/          # 原始大檔案不進 git
data/processed/    # 處理後中間檔不進 git
data/output/       # 輸出結果不進 git
```

---

## 七、GitHub Actions 排程（風場自動更新）

```yaml
# .github/workflows/wind-update.yml
name: Update Wind Data
on:
  schedule:
    - cron: '0 */6 * * *'  # 每 6 小時
  workflow_dispatch:        # 手動觸發

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv pip install -e ".[pipeline]"
      - run: python -m src.ingest.open_meteo --city taipei --days 7
      - run: python -m src.ingest.cwa_weather --region taipei
        env:
          CWA_API_KEY: ${{ secrets.CWA_API_KEY }}
      # 計算統計 → 寫入 DB
      - run: python -m src.db.queries --update-wind-stats
        env:
          DB_HOST: ${{ secrets.DB_HOST }}
          DB_PORT: ${{ secrets.DB_PORT }}
          DB_NAME: ${{ secrets.DB_NAME }}
          DB_USER: ${{ secrets.DB_USER }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
```

---

## 八、Supabase PostGIS Schema（Phase 2 完整版）

```sql
-- 啟用 PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- 網格計算結果（Phase 1 已有）
CREATE TABLE grid_cells (
    grid_id TEXT PRIMARY KEY,
    city TEXT NOT NULL,
    bcr FLOAT, svf FLOAT,
    fai_ne FLOAT, fai_sw FLOAT,
    z0 FLOAT, zd FLOAT,
    wind_50m FLOAT, wind_80m FLOAT, wind_120m FLOAT,
    risk_level TEXT, risk_score FLOAT,
    is_corridor BOOLEAN DEFAULT FALSE,
    corridor_rank INTEGER DEFAULT -1,
    geometry GEOMETRY(Polygon, 3826),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_grid_geom ON grid_cells USING GIST(geometry);

-- 風廊路徑
CREATE TABLE wind_corridors (
    corridor_id TEXT PRIMARY KEY,
    city TEXT NOT NULL,
    corridor_class TEXT,
    total_cost FLOAT,
    length_cells INTEGER,
    geometry GEOMETRY(LineString, 3826),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_corridor_geom ON wind_corridors USING GIST(geometry);

-- 即時風場觀測（Phase 2 新增）
CREATE TABLE wind_observations (
    id BIGSERIAL PRIMARY KEY,
    station_id TEXT NOT NULL,
    station_name TEXT,
    observed_at TIMESTAMPTZ NOT NULL,
    wind_speed FLOAT,          -- m/s
    wind_direction FLOAT,      -- degrees
    gust_speed FLOAT,          -- m/s
    temperature FLOAT,         -- °C
    source TEXT,               -- 'cwa', 'open_meteo', 'moenv'
    location GEOMETRY(Point, 4326),
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_wind_obs_time ON wind_observations(observed_at DESC);
CREATE INDEX idx_wind_obs_station ON wind_observations(station_id, observed_at DESC);

-- 風場統計（預計算）
CREATE TABLE wind_statistics (
    city TEXT NOT NULL,
    period TEXT NOT NULL,       -- 'annual', 'northeast_monsoon', 'southwest_monsoon'
    mean_speed FLOAT,
    median_speed FLOAT,
    p95_speed FLOAT,
    dominant_direction FLOAT,
    weibull_k FLOAT,
    weibull_c FLOAT,
    wind_rose JSONB,           -- 16 扇區頻率
    sample_count INTEGER,
    updated_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (city, period)
);

-- 建築物原始資料（前端上傳用）
CREATE TABLE buildings (
    id BIGSERIAL PRIMARY KEY,
    city TEXT NOT NULL,
    height FLOAT,
    height_source TEXT,        -- 'osm_height', 'osm_levels', 'nlsc', 'ghs', 'estimated'
    source TEXT NOT NULL,      -- 'osm', 'nlsc', 'tpe3d', 'upload'
    geometry GEOMETRY(Polygon, 3826),
    uploaded_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_buildings_geom ON buildings USING GIST(geometry);
CREATE INDEX idx_buildings_city ON buildings(city);

-- 處理任務
CREATE TABLE processing_jobs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    file_path TEXT NOT NULL,
    file_type TEXT NOT NULL,
    city TEXT NOT NULL DEFAULT 'taipei',
    status TEXT NOT NULL DEFAULT 'pending',
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);
```

---

## 九、回答：大檔案怎麼處理？

| 檔案大小 | 建議方式 | 說明 |
|---------|---------|------|
| < 10 MB | 前端上傳 | GeoJSON 建築物、風場 CSV |
| 10-50 MB | 前端上傳（ZIP） | SHP 壓縮包、小區域 GeoPackage |
| 50-500 MB | 本機 pipeline → DB | GHS-BUILT-H tile、DTM |
| > 500 MB | 本機 pipeline → DB | NLSC 全市建物、ERA5 NetCDF |
| 定期更新 | GitHub Actions | CWA/Open-Meteo 風場資料 |

**不進 GitHub 的大檔案**放在 `data/raw/`（已 gitignore），
用 `scripts/run_pipeline.py` 本機處理後直接寫入 Supabase PostGIS。
