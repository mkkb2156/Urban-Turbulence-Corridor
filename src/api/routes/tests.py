"""測試結果 API — 供 Web Dashboard 讀取 pytest + vitest 結果。"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
REPORT_DIR = PROJECT_ROOT / "data" / "output" / "test-reports"
PYTEST_REPORT = REPORT_DIR / "pytest-results.json"
VITEST_REPORT = REPORT_DIR / "vitest-results.json"


class TestSuite(BaseModel):
    name: str
    file: str
    tests: list[dict]
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration_ms: float = 0


class TestReport(BaseModel):
    timestamp: str
    framework: str
    suites: list[TestSuite]
    summary: dict
    exit_code: int = 0


class CombinedTestResults(BaseModel):
    backend: TestReport | None = None
    frontend: TestReport | None = None
    combined_summary: dict = {}


class RunStatus(BaseModel):
    status: str
    message: str


def _load_report(path: Path) -> dict | None:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def _run_pytest():
    """執行 pytest 並輸出 JSON 報告。"""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "python", "-m", "pytest", "tests/",
            "-v", "--tb=short",
            f"--json-report={PYTEST_REPORT}",
            "-p", "tests.pytest_json_report",
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
    )


def _run_vitest():
    """執行 vitest 並輸出 JSON 報告。"""
    web_dir = PROJECT_ROOT / "web"
    if not (web_dir / "node_modules").exists():
        return
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["npx", "vitest", "run", "--reporter=json", f"--outputFile={VITEST_REPORT}"],
        cwd=str(web_dir),
        capture_output=True,
    )


@router.get("/test-results", response_model=CombinedTestResults)
async def get_test_results():
    """取得最新測試結果（backend + frontend）。"""
    backend_data = _load_report(PYTEST_REPORT)
    frontend_data = _load_report(VITEST_REPORT)

    backend = TestReport(**backend_data) if backend_data else None
    frontend = None
    if frontend_data:
        # vitest JSON format differs, normalize it
        frontend = _normalize_vitest_report(frontend_data)

    # Combined summary
    b_sum = backend.summary if backend else {"total": 0, "passed": 0, "failed": 0, "skipped": 0}
    f_sum = frontend.summary if frontend else {"total": 0, "passed": 0, "failed": 0, "skipped": 0}

    combined = {
        "total": b_sum.get("total", 0) + f_sum.get("total", 0),
        "passed": b_sum.get("passed", 0) + f_sum.get("passed", 0),
        "failed": b_sum.get("failed", 0) + f_sum.get("failed", 0),
        "skipped": b_sum.get("skipped", 0) + f_sum.get("skipped", 0),
    }

    return CombinedTestResults(
        backend=backend,
        frontend=frontend,
        combined_summary=combined,
    )


@router.post("/test-results/run", response_model=RunStatus)
async def run_tests(background_tasks: BackgroundTasks):
    """觸發測試執行（背景執行）。"""
    background_tasks.add_task(_run_pytest)
    background_tasks.add_task(_run_vitest)
    return RunStatus(
        status="running",
        message="Tests started in background. Poll GET /test-results for updates.",
    )


@router.post("/test-results/run/backend", response_model=RunStatus)
async def run_backend_tests(background_tasks: BackgroundTasks):
    """只執行後端測試。"""
    background_tasks.add_task(_run_pytest)
    return RunStatus(status="running", message="Backend tests started.")


@router.post("/test-results/run/frontend", response_model=RunStatus)
async def run_frontend_tests(background_tasks: BackgroundTasks):
    """只執行前端測試。"""
    background_tasks.add_task(_run_vitest)
    return RunStatus(status="running", message="Frontend tests started.")


def _normalize_vitest_report(data: dict) -> TestReport:
    """將 vitest JSON 輸出正規化為統一格式。"""
    suites = []
    summary = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "duration_ms": 0}

    test_results = data.get("testResults", [])
    for result in test_results:
        name = Path(result.get("name", "unknown")).stem
        tests = []
        suite_passed = 0
        suite_failed = 0
        suite_skipped = 0

        for assertion in result.get("assertionResults", result.get("testResults", [])):
            status = assertion.get("status", "passed")
            if status == "passed":
                suite_passed += 1
            elif status == "failed":
                suite_failed += 1
            else:
                suite_skipped += 1

            tests.append({
                "name": assertion.get("fullName", assertion.get("title", "unknown")),
                "status": status,
                "duration_ms": assertion.get("duration", 0),
                "message": "\n".join(assertion.get("failureMessages", [])) or None,
            })

        suite = TestSuite(
            name=name,
            file=result.get("name", ""),
            tests=tests,
            passed=suite_passed,
            failed=suite_failed,
            skipped=suite_skipped,
            duration_ms=result.get("endTime", 0) - result.get("startTime", 0),
        )
        suites.append(suite)
        summary["total"] += len(tests)
        summary["passed"] += suite_passed
        summary["failed"] += suite_failed
        summary["skipped"] += suite_skipped

    summary["duration_ms"] = data.get("startTime", 0)

    return TestReport(
        timestamp=data.get("startTime", ""),
        framework="vitest",
        suites=suites,
        summary=summary,
    )
