-- 004: 風廊方向欄位 + 多城市支援
-- 為 wind_corridors 表新增精確風向角度欄位

-- 新增風向角度欄位（0-360 氣象慣例）
ALTER TABLE wind_corridors
  ADD COLUMN IF NOT EXISTS wind_direction_deg FLOAT;

-- 為現有 NE 風廊設定預設值
UPDATE wind_corridors
  SET wind_direction_deg = 45.0
  WHERE wind_direction_deg IS NULL
    AND (wind_direction = 'NE' OR wind_direction IS NULL);

-- 新增唯一約束：同城市、同類別、同風向不重複
-- (先刪除舊約束如果有)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'uq_corridor_city_class_direction'
  ) THEN
    ALTER TABLE wind_corridors
      ADD CONSTRAINT uq_corridor_city_class_direction
      UNIQUE (city, corridor_class, wind_direction, wind_direction_deg);
  END IF;
END $$;

-- 建立索引加速按方向查詢
CREATE INDEX IF NOT EXISTS idx_corridors_direction_deg
  ON wind_corridors (wind_direction_deg);
