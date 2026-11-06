"""Emit only synthetic test identifiers, not logs or assertion details."""

from pathlib import Path
import re
import sys
import unittest
import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from scripts.ci.database_junit import MODULES, flatten
from scripts.ci.concurrency_junit import TESTS

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / 'test-results/database'
SAFE_IDENTIFIER = re.compile(r'^[A-Za-z0-9_.-]+$')
cases = flatten(unittest.TestLoader().loadTestsFromNames(MODULES))
allowed = {(case.__class__.__module__ + '.' + case.__class__.__name__, case._testMethodName)
           for case in cases if not case.__class__.__name__.startswith('_FailedTest')}
allowed.update(('ParentPlus.Concurrency', name) for name in TESTS)
found = False

for filename in ('unittest-junit.xml', 'concurrency-junit.xml'):
    path = ROOT / filename
    if not path.is_file():
        print(f'::error title=Database evidence::{filename} is unavailable')
        continue
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        print(f'::error title=Database evidence::{filename} could not be parsed')
        continue
    for case in root.iter('testcase'):
        if not any(case.find(tag) is not None for tag in ('failure', 'error', 'skipped')):
            continue
        name = case.get('name', '')
        classname = case.get('classname', '')
        if (len(name) > 180 or len(classname) > 180 or not SAFE_IDENTIFIER.fullmatch(name)
                or not SAFE_IDENTIFIER.fullmatch(classname) or (classname, name) not in allowed):
            print('::error title=Database evidence::A failing test has an invalid identifier')
        else:
            print(f'::error title=Database test failure::{classname}.{name}')
        found = True

if not found:
    print('::error title=Database gate::No failed test identifier was available; inspect the job evidence')
