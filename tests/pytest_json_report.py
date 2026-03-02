"""pytest plugin: 輸出 JSON 格式測試結果供 Web Dashboard 使用。"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path


def pytest_addoption(parser):
    parser.addoption(
        "--json-report",
        action="store",
        default=None,
        help="Output JSON test report to specified path",
    )


def pytest_configure(config):
    json_path = config.getoption("--json-report")
    if json_path:
        config._json_report_path = Path(json_path)
        config._json_report_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "start_time": time.time(),
            "framework": "pytest",
            "suites": {},
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "error": 0,
                "duration_ms": 0,
            },
        }


def pytest_runtest_logreport(report):
    config = report.config if hasattr(report, "config") else None
    if config is None:
        return
    if not hasattr(config, "_json_report_data"):
        return

    data = config._json_report_data

    # Only process the "call" phase (not setup/teardown) for pass/fail
    if report.when != "call" and not (report.when == "setup" and report.skipped):
        return

    # Extract suite name from nodeid (e.g., tests/test_fai.py::TestFAI::test_basic → test_fai)
    parts = report.nodeid.split("::")
    file_part = parts[0].replace("tests/", "").replace(".py", "")
    suite_name = file_part

    if suite_name not in data["suites"]:
        data["suites"][suite_name] = {
            "name": suite_name,
            "file": parts[0],
            "tests": [],
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "duration_ms": 0,
        }

    suite = data["suites"][suite_name]

    test_name = "::".join(parts[1:]) if len(parts) > 1 else parts[0]

    status = "passed"
    message = None
    if report.passed:
        status = "passed"
    elif report.failed:
        status = "failed"
        message = str(report.longrepr) if report.longrepr else None
    elif report.skipped:
        status = "skipped"
        message = str(report.longrepr) if report.longrepr else None

    test_entry = {
        "name": test_name,
        "status": status,
        "duration_ms": round(report.duration * 1000, 2),
        "message": message,
    }

    suite["tests"].append(test_entry)
    suite[status] += 1
    suite["duration_ms"] += test_entry["duration_ms"]

    data["summary"]["total"] += 1
    data["summary"][status] += 1


def pytest_sessionfinish(session, exitstatus):
    config = session.config
    if not hasattr(config, "_json_report_data"):
        return

    data = config._json_report_data
    data["summary"]["duration_ms"] = round(
        (time.time() - data["start_time"]) * 1000, 2
    )
    data["exit_code"] = exitstatus

    # Convert suites dict to list
    data["suites"] = list(data["suites"].values())

    # Remove internal start_time
    del data["start_time"]

    output_path = config._json_report_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
