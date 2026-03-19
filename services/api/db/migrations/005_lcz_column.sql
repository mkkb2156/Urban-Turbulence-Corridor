-- 005: LCZ (Local Climate Zone) 分類欄位
-- 基於 Stewart & Oke (2012) 方案

ALTER TABLE grid_cells
  ADD COLUMN IF NOT EXISTS lcz_class INTEGER;

ALTER TABLE grid_cells
  ADD COLUMN IF NOT EXISTS lcz_label TEXT;

-- 建立索引加速 LCZ 篩選
CREATE INDEX IF NOT EXISTS idx_grid_lcz_class ON grid_cells (lcz_class);

COMMENT ON COLUMN grid_cells.lcz_class IS 'Local Climate Zone class (1-8 for built types, 0 for open land)';
COMMENT ON COLUMN grid_cells.lcz_label IS 'LCZ label (e.g. Compact high-rise, Open mid-rise)';
