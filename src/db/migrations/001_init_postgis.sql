-- ============================================================
-- UTC Phase 2 — Supabase PostGIS Schema
-- 在 Supabase SQL Editor 中執行此檔案
-- ============================================================

-- 啟用 PostGIS（Supabase 預設已安裝，需手動啟用）
CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================================================
-- 1. 網格計算結果（Phase 1 核心）
-- ============================================================
CREATE TABLE IF NOT EXISTS grid_cells (
    id SERIAL PRIMARY KEY,
    grid_id TEXT UNIQUE NOT NULL,
    city TEXT NOT NULL,
    row INTEGER NOT NULL,
    col INTEGER NOT NULL,
    geometry GEOMETRY(Polygon, 3826) NOT NULL,

    -- 形態學指標
    bcr FLOAT,
    svf FLOAT,
    mean_height FLOAT,
    max_height FLOAT,
    n_buildings INTEGER,
    z0 FLOAT,
    zd FLOAT,

    -- FAI（主要方向）
    fai_ne FLOAT,
    fai_sw FLOAT,
    fai_max FLOAT,
    fai_max_direction FLOAT,

    -- 風速估算
    wind_50m FLOAT,
    wind_80m FLOAT,
    wind_120m FLOAT,

    -- 風廊
    is_corridor BOOLEAN DEFAULT FALSE,
    corridor_rank INTEGER DEFAULT -1,

    -- 風險
    risk_level TEXT,
    risk_score FLOAT,

    -- 中繼資料
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_grid_cells_geom ON grid_cells USING GIST(geometry);
CREATE INDEX IF NOT EXISTS idx_grid_cells_city ON grid_cells(city);

-- ============================================================
-- 2. 風廊路徑
-- ============================================================
CREATE TABLE IF NOT EXISTS wind_corridors (
    id SERIAL PRIMARY KEY,
    corridor_id TEXT UNIQUE NOT NULL,
    city TEXT NOT NULL,
    geometry GEOMETRY(LineString, 3826) NOT NULL,
    corridor_class TEXT,        -- primary / secondary / minor
    total_cost FLOAT,
    length_cells INTEGER,
    estimated_width FLOAT,
    wind_direction TEXT,        -- northeast / southwest
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wind_corridors_geom ON wind_corridors USING GIST(geometry);
CREATE INDEX IF NOT EXISTS idx_wind_corridors_city ON wind_corridors(city);

-- ============================================================
-- 3. 氣象站
-- ============================================================
CREATE TABLE IF NOT EXISTS weather_stations (
    id SERIAL PRIMARY KEY,
    station_id TEXT UNIQUE NOT NULL,
    station_name TEXT,
    city TEXT,
    geometry GEOMETRY(Point, 4326)
);

CREATE INDEX IF NOT EXISTS idx_weather_stations_geom ON weather_stations USING GIST(geometry);

-- ============================================================
-- 4. 即時風場觀測（Phase 2）
-- ============================================================
CREATE TABLE IF NOT EXISTS wind_observations (
    id BIGSERIAL PRIMARY KEY,
    station_id TEXT NOT NULL,
    station_name TEXT,
    observed_at TIMESTAMPTZ NOT NULL,
    wind_speed FLOAT,           -- m/s
    wind_direction FLOAT,       -- degrees
    gust_speed FLOAT,           -- m/s
    temperature FLOAT,          -- °C
    source TEXT,                 -- 'cwa', 'open_meteo', 'moenv'
    location GEOMETRY(Point, 4326),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wind_obs_time ON wind_observations(observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_wind_obs_station ON wind_observations(station_id, observed_at DESC);

-- ============================================================
-- 5. 風場統計（預計算）
-- ============================================================
CREATE TABLE IF NOT EXISTS wind_statistics (
    city TEXT NOT NULL,
    period TEXT NOT NULL,        -- 'annual', 'northeast_monsoon', 'southwest_monsoon'
    mean_speed FLOAT,
    median_speed FLOAT,
    p95_speed FLOAT,
    dominant_direction FLOAT,
    weibull_k FLOAT,
    weibull_c FLOAT,
    wind_rose JSONB,            -- 16 扇區頻率
    sample_count INTEGER,
    updated_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (city, period)
);

-- ============================================================
-- 6. 建築物原始資料（前端上傳用，Sprint 2）
-- ============================================================
CREATE TABLE IF NOT EXISTS buildings (
    id BIGSERIAL PRIMARY KEY,
    city TEXT NOT NULL,
    height FLOAT,
    height_source TEXT,         -- 'osm_height', 'osm_levels', 'nlsc', 'ghs', 'estimated'
    source TEXT NOT NULL,       -- 'osm', 'nlsc', 'tpe3d', 'upload'
    geometry GEOMETRY(Polygon, 3826),
    uploaded_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_buildings_geom ON buildings USING GIST(geometry);
CREATE INDEX IF NOT EXISTS idx_buildings_city ON buildings(city);

-- ============================================================
-- 7. 處理任務追蹤（前端上傳用，Sprint 2）
-- ============================================================
CREATE TABLE IF NOT EXISTS processing_jobs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    file_path TEXT NOT NULL,
    file_type TEXT NOT NULL,    -- 'buildings_shp', 'buildings_geojson', 'dem_tiff'
    city TEXT NOT NULL DEFAULT 'taipei',
    status TEXT NOT NULL DEFAULT 'pending',  -- pending / processing / completed / failed
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

-- ============================================================
-- updated_at 自動更新 trigger
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trigger_grid_cells_updated_at
    BEFORE UPDATE ON grid_cells
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER trigger_wind_corridors_updated_at
    BEFORE UPDATE ON wind_corridors
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER trigger_wind_statistics_updated_at
    BEFORE UPDATE ON wind_statistics
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
