-- UTC v4: Wind Texture Cache Table
-- 快取每個 bbox+datetime 的 PNG bytes，避免重複計算。TTL 1 小時。

CREATE TABLE IF NOT EXISTS wind_textures (
    cache_key   TEXT PRIMARY KEY,       -- SHA256(bbox + datetime + altitude + resolution)
    png_bytes   BYTEA NOT NULL,         -- PNG 圖片資料
    bounds      FLOAT[4] NOT NULL,      -- [lng_min, lat_min, lng_max, lat_max]
    wind_min    FLOAT NOT NULL,         -- 解碼參數
    wind_max    FLOAT NOT NULL,
    resolution  INT NOT NULL,           -- m/pixel
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    expires_at  TIMESTAMPTZ NOT NULL    -- created_at + 1 hour
);

CREATE INDEX IF NOT EXISTS idx_wind_textures_expires
    ON wind_textures(expires_at);

-- 定期清理過期快取
-- DELETE FROM wind_textures WHERE expires_at < NOW();

-- v4: 新增 morphology_grids 欄位（如果不存在）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'grid_cells' AND column_name = 'wind_texture_u'
    ) THEN
        ALTER TABLE grid_cells ADD COLUMN wind_texture_u FLOAT[];
        ALTER TABLE grid_cells ADD COLUMN wind_texture_v FLOAT[];
    END IF;
END $$;
