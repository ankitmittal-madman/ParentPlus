#!/usr/bin/env python3
"""JUnit evidence for ParentPlus standalone concurrency tests."""

import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "test-results/database/concurrency-junit.xml"

TESTS = [
    "test_concurrent_workspace.py",
    "test_concurrent_child.py",
    "test_concurrent_connection.py",
    "test_concurrent_approval.py",
]


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    root = ET.Element("testsuites")
    suite = ET.SubElement(
        root,
        "testsuite",
        name="ParentPlus Standalone Concurrency",
        tests=str(len(TESTS)),
    )

    failures = 0

    for filename in TESTS:
        print(f"Running {filename}", flush=True)

        started = time.monotonic()

        try:
            result = subprocess.run(
                [sys.executable, str(ROOT / "tests/database" / filename)],
                cwd=ROOT,
                env={
                    **os.environ,
                    "PYTHONPATH": str(ROOT),
                },
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            code = result.returncode
            stdout = result.stdout
            stderr = result.stderr
        except subprocess.TimeoutExpired as exc:
            code = 124
            stdout = (
                exc.stdout.decode(errors="replace")
                if isinstance(exc.stdout, bytes)
                else (exc.stdout or "")
            )
            stderr = (
                exc.stderr.decode(errors="replace")
                if isinstance(exc.stderr, bytes)
                else (exc.stderr or "")
            ) + "\nTest timed out"

        duration = time.monotonic() - started

        case = ET.SubElement(
            suite,
            "testcase",
            classname="ParentPlus.Concurrency",
            name=filename,
            time=f"{duration:.6f}",
        )

        if code != 0:
            failures += 1
            ET.SubElement(
                case,
                "failure",
                message=f"Process exit code: {code}",
            ).text = stderr or stdout

        ET.SubElement(case, "system-out").text = stdout
        ET.SubElement(case, "system-err").text = stderr

        print(stdout, end="", flush=True)
        if stderr:
            print(stderr, file=sys.stderr, flush=True)

        print(
            f"{'PASS' if code == 0 else 'FAIL'}: {filename}",
            flush=True,
        )

    suite.set("failures", str(failures))
    suite.set("errors", "0")
    suite.set("skipped", "0")

    ET.ElementTree(root).write(
        OUTPUT,
        encoding="utf-8",
        xml_declaration=True,
    )

    print(f"JUnit evidence written: {OUTPUT}", flush=True)

    if len(suite.findall("testcase")) != 4 or failures:
        print("FAIL: Concurrency evidence incomplete", flush=True)
        return 1

    print("PASS: All four concurrency scenarios verified", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
