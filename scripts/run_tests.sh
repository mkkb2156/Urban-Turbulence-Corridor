#!/usr/bin/env bash
# UTC 測試執行腳本 — 生成 JSON 報告供 Web Dashboard 使用
# Usage: bash scripts/run_tests.sh [backend|frontend|all]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPORT_DIR="$PROJECT_ROOT/data/output/test-reports"

mkdir -p "$REPORT_DIR"

run_backend() {
    echo "=== Running Backend Tests (pytest) ==="
    cd "$PROJECT_ROOT"

    python -m pytest tests/ \
        -v --tb=short \
        --json-report="$REPORT_DIR/pytest-results.json" \
        -p tests.pytest_json_report \
        --cov=src --cov-report=json:"$REPORT_DIR/coverage.json" \
        --cov-report=html:"$REPORT_DIR/htmlcov" \
        || true

    echo "Backend test report: $REPORT_DIR/pytest-results.json"
    echo "Coverage report: $REPORT_DIR/htmlcov/index.html"
}

run_frontend() {
    echo "=== Running Frontend Tests (vitest) ==="
    cd "$PROJECT_ROOT/web"

    if [ ! -d "node_modules" ]; then
        echo "Installing frontend dependencies..."
        npm install
    fi

    npx vitest run \
        --reporter=json --outputFile="$REPORT_DIR/vitest-results.json" \
        --coverage \
        || true

    echo "Frontend test report: $REPORT_DIR/vitest-results.json"
}

run_watch_backend() {
    echo "=== Backend Test Watch Mode ==="
    cd "$PROJECT_ROOT"
    python -m pytest_watch tests/ -- -v --tb=short
}

run_watch_frontend() {
    echo "=== Frontend Test Watch Mode ==="
    cd "$PROJECT_ROOT/web"
    npx vitest --ui
}

MODE="${1:-all}"

case "$MODE" in
    backend)
        run_backend
        ;;
    frontend)
        run_frontend
        ;;
    all)
        run_backend
        run_frontend
        ;;
    watch-backend)
        run_watch_backend
        ;;
    watch-frontend)
        run_watch_frontend
        ;;
    *)
        echo "Usage: $0 [backend|frontend|all|watch-backend|watch-frontend]"
        exit 1
        ;;
esac

echo ""
echo "=== Done ==="
echo "View test dashboard: http://localhost:5173/tests (dev) or http://localhost:8000/tests (prod)"
