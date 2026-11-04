#!/usr/bin/env python3
"""JUnit XML reporting for ParentPlus database unittest suites."""

import sys
import time
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

# Ensure repository test modules are importable when this
# script is executed directly from scripts/ci.
REPO_ROOT = Path(__file__).resolve().parents[2]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

MODULES = [
    "tests.database.test_authorization",
    "tests.database.test_scheduling_foundation",
    "tests.database.test_scheduling_authorization_races",
    "tests.database.test_child_authorization",
    "tests.database.test_connection_authorization",
    "tests.database.test_approval_safety",
    "tests.database.test_approval_authorization_races",
    "tests.database.test_concurrent_authorization",
]


class RecordingResult(unittest.TextTestResult):
    def startTest(self, test):
        self._started_at = getattr(self, "_started_at", {})
        self._started_at[test.id()] = time.monotonic()
        super().startTest(test)

    def stopTest(self, test):
        self._durations = getattr(self, "_durations", {})
        started = self._started_at.pop(test.id(), time.monotonic())
        self._durations[test.id()] = time.monotonic() - started
        super().stopTest(test)


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def main():
    output = Path("test-results/database/unittest-junit.xml")
    output.parent.mkdir(parents=True, exist_ok=True)

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromNames(MODULES)
    cases = list(flatten(suite))

    runner = unittest.TextTestRunner(
        verbosity=2,
        resultclass=RecordingResult,
    )

    result = runner.run(suite)

    failures = dict(result.failures)
    errors = dict(result.errors)
    skipped = dict(result.skipped)

    root = ET.Element("testsuites")
    group = ET.SubElement(
        root,
        "testsuite",
        name="ParentPlus Database Unit Tests",
        tests=str(result.testsRun),
        failures=str(len(result.failures)),
        errors=str(len(result.errors)),
        skipped=str(len(result.skipped)),
    )

    for test in cases:
        case = ET.SubElement(
            group,
            "testcase",
            classname=test.__class__.__module__ + "." +
                      test.__class__.__name__,
            name=test._testMethodName,
            time=f"{result._durations.get(test.id(), 0):.6f}",
        )

        if test in failures:
            ET.SubElement(case, "failure").text = failures[test]
        elif test in errors:
            ET.SubElement(case, "error").text = errors[test]
        elif test in skipped:
            ET.SubElement(case, "skipped").text = skipped[test]

    ET.ElementTree(root).write(
        output,
        encoding="utf-8",
        xml_declaration=True,
    )

    print(f"JUnit evidence written: {output}", flush=True)

    expected_tests = 173
    actual_tests = result.testsRun
    recorded_cases = len(group.findall("testcase"))

    complete = (
        actual_tests == expected_tests
        and recorded_cases == actual_tests
        and len(result.failures) == 0
        and len(result.errors) == 0
        and len(result.skipped) == 0
        and result.wasSuccessful()
    )

    if not complete:
        print(
            "FAIL: Database test evidence incomplete or unsuccessful. "
            f"Expected={expected_tests}, executed={actual_tests}, "
            f"recorded={recorded_cases}, "
            f"failures={len(result.failures)}, "
            f"errors={len(result.errors)}, "
            f"skipped={len(result.skipped)}",
            flush=True,
        )
        return 1

    print("PASS: All 173 database unit tests verified", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
