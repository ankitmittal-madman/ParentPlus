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
upgrade_stages = {'container_precheck', 'container_start', 'container_ready', 'migration_inventory', 'auth_fixture',
                  'old_migrations', 'legacy_creation', 'legacy_rename', 'upgrade_migration',
                  'legacy_state', 'legacy_retry', 'new_retry', 'control_upgrade',
                  'control_disabled_retry', 'control_enabled_retry', 'cleanup'}
upgrade_errors = {'AssertionError', 'CalledProcessError', 'TimeoutExpired', 'JSONDecodeError', 'OSError',
                  'FileNotFoundError', 'RuntimeError'}
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
            if (classname == 'tests.database.test_workspace_receipt_upgrade.WorkspaceReceiptUpgradeTests'
                    and name == 'test_existing_renamed_workspace_is_preserved_and_legacy_retry_fails_closed'):
                details = ' '.join((case.findtext(tag) or '') for tag in ('failure', 'error'))
                markers = set(re.findall(r'UPGRADE_DIAG:([a-z_]+):([A-Za-z]+)', details))
                for stage, error in sorted(markers):
                    if stage in upgrade_stages and error in upgrade_errors:
                        print(f'::error title=Upgrade test stage::{stage} ({error})')
        found = True

if not found:
    print('::error title=Database gate::No failed test identifier was available; inspect the job evidence')
