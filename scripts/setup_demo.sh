#!/usr/bin/env bash
# ============================================================
# UTC Demo Environment Setup
# 快速建立本機 Demo 環境，跑 pipeline → 匯入 DB
#
# 前置條件：
#   1. Python 3.11+ 已安裝
#   2. .env 已填好 DB_HOST/PORT/NAME/USER/PASSWORD
#   3. Supabase PostGIS 已建立（跑過 001_init_postgis.sql）
#
# Usage:
#   bash scripts/setup_demo.sh              # 全部步驟
#   bash scripts/setup_demo.sh --skip-db    # 跳過 DB 匯入
#   bash scripts/setup_demo.sh --city taipei_pilot  # 指定城市
# ============================================================

set -euo pipefail

CITY="${1:-taipei_pilot}"
SKIP_DB=false
VERBOSE=""

# 解析參數
for arg in "$@"; do
  case $arg in
    --skip-db)   SKIP_DB=true ;;
    --city)      shift; CITY="${1:-taipei_pilot}" ;;
    -v|--verbose) VERBOSE="-v" ;;
  esac
done

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "============================================================"
echo " UTC Demo Setup — City: $CITY"
echo "============================================================"

# Step 0: 確保虛擬環境
if [ ! -d ".venv" ]; then
  echo "[0/5] Creating virtual environment..."
  if command -v uv &> /dev/null; then
    uv venv
  else
    python3 -m venv .venv
  fi
fi

echo "[0/5] Installing dependencies..."
if command -v uv &> /dev/null; then
  uv pip install -e ".[pipeline,dev]"
else
  source .venv/bin/activate
  pip install -e ".[pipeline,dev]"
fi

# Step 1: 產生建築物資料
BUILDINGS_PATH="data/processed/buildings/${CITY}_buildings.gpkg"
if [ -f "$BUILDINGS_PATH" ]; then
  echo "[1/5] Buildings already exist at $BUILDINGS_PATH, skipping."
else
  echo "[1/5] Generating synthetic building data..."
  if [ "$CITY" = "taipei" ] || [ "$CITY" = "taipei_pilot" ]; then
    python scripts/generate_buildings.py
    # taipei_pilot 共用 taipei 的建築資料
    if [ "$CITY" = "taipei_pilot" ] && [ ! -f "$BUILDINGS_PATH" ]; then
      cp "data/processed/buildings/taipei_buildings.gpkg" "$BUILDINGS_PATH" 2>/dev/null || true
    fi
  else
    echo "  WARNING: No building generator for $CITY. Run OSM download manually:"
    echo "  python -m src.ingest.osm_buildings --city $CITY"
  fi
fi

# Step 2: 取得風場資料（Open-Meteo，免 API key）
WIND_STATS="data/processed/weather/${CITY}_wind_stats.json"
if [ -f "$WIND_STATS" ]; then
  echo "[2/5] Wind stats already exist at $WIND_STATS, skipping."
else
  echo "[2/5] Fetching Open-Meteo historical wind data (30 days for demo)..."
  python -m src.ingest.open_meteo --city "$CITY" --days 30 || {
    echo "  WARNING: Open-Meteo fetch failed (network?). Using default wind speed."
  }
fi

# Step 3: 跑 pipeline
OUTPUT_GRID="data/output/${CITY}_grid.gpkg"
echo "[3/5] Running Phase 1 pipeline..."
python scripts/run_pipeline.py --city "$CITY" --grid-size 100 $VERBOSE

if [ ! -f "$OUTPUT_GRID" ]; then
  echo "ERROR: Pipeline output not found at $OUTPUT_GRID"
  exit 1
fi
echo "  Pipeline output: $OUTPUT_GRID"

# Step 4: 匯入 DB
if [ "$SKIP_DB" = true ]; then
  echo "[4/5] Skipping DB import (--skip-db)."
else
  echo "[4/5] Importing grid to Supabase PostGIS..."
  if [ -f ".env" ] && grep -q "DB_HOST" .env; then
    python -m src.db.queries --import-grid "$OUTPUT_GRID"
    echo "  Grid imported successfully."

    # 匯入風廊
    CORRIDORS="data/output/${CITY}_corridors.gpkg"
    if [ -f "$CORRIDORS" ]; then
      python -m src.db.queries --import-corridors "$CORRIDORS"
      echo "  Corridors imported successfully."
    fi
  else
    echo "  WARNING: .env not found or DB_HOST not set. Skipping DB import."
    echo "  To import later: python -m src.db.queries --import-grid $OUTPUT_GRID"
  fi
fi

# Step 5: 視覺化輸出
echo "[5/5] Exporting visualization..."
python scripts/export_tiles.py --city "$CITY" --format both 2>/dev/null || {
  echo "  NOTE: export_tiles.py skipped (optional dependency missing?)."
}

echo ""
echo "============================================================"
echo " Demo setup complete!"
echo "============================================================"
echo ""
echo "Output files:"
echo "  Grid:      data/output/${CITY}_grid.gpkg"
echo "  Corridors: data/output/${CITY}_corridors.gpkg"
echo "  Map:       data/output/${CITY}_map.html (if export succeeded)"
echo ""
echo "Next steps:"
echo "  1. 確認 .env 已填 Supabase 連線資訊"
echo "  2. 在 Supabase SQL Editor 執行 src/db/migrations/001_init_postgis.sql"
echo "  3. python -m src.db.queries --import-grid data/output/${CITY}_grid.gpkg"
echo "  4. 啟動前端: cd web && npm run dev"
echo "  5. 啟動後端: uvicorn src.api.main:app --reload"
