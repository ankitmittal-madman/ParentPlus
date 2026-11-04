#!/usr/bin/env python3
"""Validate ParentPlus database CI evidence."""
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
REPORTS = {
    "unittest-junit.xml": 240,
    "concurrency-junit.xml": 4,
}

total = 0

for filename, expected in REPORTS.items():
    path = ROOT / "test-results/database" / filename

    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f"FAIL: Missing evidence: {filename}")

    root = ET.parse(path).getroot()

    if root.tag != "testsuites":
        raise SystemExit(f"FAIL: Invalid root: {filename}")

    suites = root.findall("testsuite")
    cases = [
        case
        for suite in suites
        for case in suite.findall("testcase")
    ]

    reported = sum(int(s.get("tests", -1)) for s in suites)
    failures = sum(int(s.get("failures", -1)) for s in suites)
    errors = sum(int(s.get("errors", -1)) for s in suites)
    skipped = sum(int(s.get("skipped", -1)) for s in suites)

    names = [
        (c.get("classname"), c.get("name"))
        for c in cases
    ]

    if (
        not suites
        or reported != expected
        or len(cases) != expected
        or len(set(names)) != expected
        or failures != 0
        or errors != 0
        or skipped != 0
    ):
        raise SystemExit(f"FAIL: Invalid evidence: {filename}")

    for case in cases:
        if (
            not case.get("classname")
            or not case.get("name")
            or float(case.get("time", "-1")) < 0
            or any(
                case.find(tag) is not None
                for tag in ("failure", "error", "skipped")
            )
        ):
            raise SystemExit(f"FAIL: Invalid case: {filename}")

    print(f"PASS: {filename}: {expected} cases")
    total += expected

if total != 244:
    raise SystemExit("FAIL: Unexpected total coverage")

print("PASS: All 244 database evidence cases verified")
