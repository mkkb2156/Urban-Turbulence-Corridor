-- ============================================================
-- UTC Phase 3 — 衍生數據欄位 + 新資料表
-- 在 Supabase SQL Editor 中執行此檔案
-- ============================================================

-- ============================================================
-- 1. 擴充 grid_cells：湍流、風切變、陣風、遮蔽、高度限制
-- ============================================================

-- 湍流強度 (Turbulence Intensity)
ALTER TABLE grid_cells ADD COLUMN IF NOT EXISTS turbulence_50m FLOAT;
ALTER TABLE grid_cells ADD COLUMN IF NOT EXISTS turbulence_80m FLOAT;
ALTER TABLE grid_cells ADD COLUMN IF NOT EXISTS turbulence_120m FLOAT;

-- 風切變指數 (Wind Shear Exponent)
ALTER TABLE grid_cells ADD COLUMN IF NOT EXISTS shear_50_80 FLOAT;
ALTER TABLE grid_cells ADD COLUMN IF NOT EXISTS shear_80_120 FLOAT;

-- 陣風因子 (Gust Factor)
ALTER TABLE grid_cells ADD COLUMN IF NOT EXISTS gust_factor FLOAT;

-- 建築遮蔽指數 (Shelter Index)
ALTER TABLE grid_cells ADD COLUMN IF NOT EXISTS shelter_index FLOAT;

-- 無人機可用高度範圍
ALTER TABLE grid_cells ADD COLUMN IF NOT EXISTS min_safe_alt FLOAT;
ALTER TABLE grid_cells ADD COLUMN IF NOT EXISTS max_legal_alt FLOAT DEFAULT 120.0;

-- 風向角度（取代硬編碼 NE）
ALTER TABLE grid_cells ADD COLUMN IF NOT EXISTS wind_direction_deg FLOAT;

-- ============================================================
-- 2. 空域限制區 (Airspace Zones)
-- ============================================================
CREATE TABLE IF NOT EXISTS airspace_zones (
    id SERIAL PRIMARY KEY,
    zone_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    zone_type TEXT NOT NULL,           -- 'prohibited', 'restricted', 'airport', 'military', 'special'
    restriction TEXT,                   -- 'no_fly', 'height_limit', 'permit_required'
    max_height_m FLOAT,                -- 限制高度 (m AGL), NULL = 完全禁飛
    geometry GEOMETRY(Polygon, 3826) NOT NULL,
    source TEXT DEFAULT 'caa',         -- 'caa', 'manual', 'notam'
    valid_from TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_airspace_geom ON airspace_zones USING GIST(geometry);

-- ============================================================
-- 3. 時序飛行條件 (Flight Conditions)
-- ============================================================
CREATE TABLE IF NOT EXISTS flight_conditions (
    id BIGSERIAL PRIMARY KEY,
    grid_id TEXT NOT NULL REFERENCES grid_cells(grid_id),
    forecast_time TIMESTAMPTZ NOT NULL,

    -- 風場
    wind_speed_50m FLOAT,
    wind_speed_80m FLOAT,
    wind_speed_120m FLOAT,
    wind_direction FLOAT,              -- degrees
    gust_speed FLOAT,

    -- 衍生風險
    risk_level TEXT,
    turbulence_intensity FLOAT,

    -- 來源
    source TEXT DEFAULT 'open_meteo',
    created_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(grid_id, forecast_time)
);

CREATE INDEX IF NOT EXISTS idx_flight_cond_time
    ON flight_conditions(forecast_time DESC);
CREATE INDEX IF NOT EXISTS idx_flight_cond_grid
    ON flight_conditions(grid_id, forecast_time DESC);

-- ============================================================
-- 4. 地形高程 (Terrain Elevation)
-- ============================================================
CREATE TABLE IF NOT EXISTS terrain_elevation (
    id SERIAL PRIMARY KEY,
    grid_id TEXT UNIQUE NOT NULL REFERENCES grid_cells(grid_id),
    dem_elevation FLOAT,               -- 地面高程 (m, MSL)
    dsm_elevation FLOAT,               -- 含建物高程 (m, MSL)
    slope_deg FLOAT,                   -- 坡度 (degrees)
    aspect_deg FLOAT,                  -- 坡向 (degrees, 0=N)
    source TEXT DEFAULT 'copernicus_glo30'
);

-- ============================================================
-- 5. 一次性回填衍生數據（純 SQL 計算）
-- ============================================================

-- 5a. 湍流強度: TI ≈ 1 / ln((z - zd) / z0)
UPDATE grid_cells SET
    turbulence_50m  = CASE WHEN z0 > 0 AND (50  - COALESCE(zd, 0)) > z0 THEN 1.0 / LN((50  - COALESCE(zd, 0)) / z0) ELSE NULL END,
    turbulence_80m  = CASE WHEN z0 > 0 AND (80  - COALESCE(zd, 0)) > z0 THEN 1.0 / LN((80  - COALESCE(zd, 0)) / z0) ELSE NULL END,
    turbulence_120m = CASE WHEN z0 > 0 AND (120 - COALESCE(zd, 0)) > z0 THEN 1.0 / LN((120 - COALESCE(zd, 0)) / z0) ELSE NULL END
WHERE z0 IS NOT NULL AND z0 > 0;

-- 5b. 風切變指數: α = ln(U₂/U₁) / ln(z₂/z₁)
UPDATE grid_cells SET
    shear_50_80  = CASE WHEN wind_50m > 0 AND wind_80m > 0  THEN LN(wind_80m  / wind_50m) / LN(80.0  / 50.0) ELSE NULL END,
    shear_80_120 = CASE WHEN wind_80m > 0 AND wind_120m > 0 THEN LN(wind_120m / wind_80m) / LN(120.0 / 80.0) ELSE NULL END
WHERE wind_50m IS NOT NULL AND wind_50m > 0;

-- 5c. 陣風因子: GF = 1 + g × TI × (1 + 0.5 × fai_max), g=3.0
UPDATE grid_cells SET
    gust_factor = CASE
        WHEN turbulence_50m IS NOT NULL AND fai_max IS NOT NULL
        THEN 1.0 + 3.0 * turbulence_50m * (1.0 + 0.5 * LEAST(fai_max, 1.0))
        ELSE NULL
    END
WHERE turbulence_50m IS NOT NULL;

-- 5d. 遮蔽指數: shelter = (1 - svf) × (1 + fai_dominant) × bcr
UPDATE grid_cells SET
    shelter_index = CASE
        WHEN svf IS NOT NULL AND bcr IS NOT NULL
        THEN (1.0 - COALESCE(svf, 1.0)) * (1.0 + COALESCE(GREATEST(fai_ne, fai_sw), 0)) * COALESCE(bcr, 0)
        ELSE NULL
    END
WHERE svf IS NOT NULL;

-- 5e. 可用高度範圍
UPDATE grid_cells SET
    min_safe_alt  = GREATEST(COALESCE(mean_height, 0) + 20.0, COALESCE(max_height, 0) + 10.0),
    max_legal_alt = 120.0
WHERE mean_height IS NOT NULL OR max_height IS NOT NULL;
