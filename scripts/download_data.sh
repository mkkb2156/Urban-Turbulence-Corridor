#!/usr/bin/env bash
# 一鍵下載所有城市原始資料
# Usage: bash scripts/download_data.sh taipei

set -euo pipefail

CITY="${1:-taipei}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$PROJECT_ROOT/data/raw"

echo "=== UTC Data Download ==="
echo "City: $CITY"
echo "Output: $DATA_DIR"
echo ""

# 建立目錄
mkdir -p "$DATA_DIR/buildings"
mkdir -p "$DATA_DIR/terrain"
mkdir -p "$DATA_DIR/weather"
mkdir -p "$DATA_DIR/osm"

# 1. 建物資料
echo "[1/4] Downloading building data..."
echo "  NOTE: NLSC 3D building data requires manual download from:"
echo "  https://maps.nlsc.gov.tw/S09SOA/homePage.action?Language=ZH"
echo "  Place downloaded files in: $DATA_DIR/buildings/"
echo ""

# 2. 地形資料
echo "[2/4] Downloading terrain data..."
echo "  NOTE: Download DTM/DSM from:"
echo "  DTM: https://data.gov.tw/dataset/35430"
echo "  DSM: https://data.gov.tw/dataset/175240"
echo "  Place downloaded files in: $DATA_DIR/terrain/"
echo ""

# 3. 氣象資料
echo "[3/4] Fetching weather data..."
if [ -n "${CWA_API_KEY:-}" ]; then
    python -m src.ingest.cwa_weather --region "$CITY" || echo "  Warning: CWA fetch failed"
else
    echo "  CWA_API_KEY not set. Skipping weather data download."
    echo "  Set CWA_API_KEY in .env to enable."
fi
echo ""

# 4. OSM 道路
echo "[4/4] OSM road data..."
echo "  NOTE: Download Taiwan PBF from:"
echo "  https://download.geofabrik.de/asia/taiwan.html"
echo "  Place in: $DATA_DIR/osm/"
echo ""

echo "=== Download complete ==="
echo "Next steps:"
echo "  1. Place manually downloaded files in the directories above"
echo "  2. Run preprocessing: python -m src.ingest.nlsc_buildings --city $CITY"
echo "  3. Run pipeline: python scripts/run_pipeline.py --city $CITY"
