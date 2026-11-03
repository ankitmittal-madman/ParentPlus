#!/usr/bin/env python3
"""Deterministic change selection and exact-test evidence for ParentPlus."""
import argparse
import ast
from datetime import datetime, timezone
import fnmatch
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SUITES = {'quality', 'frontend', 'database'}


class GateError(ValueError):
    """An input or result cannot safely satisfy the quality gate."""


def require(condition, message):
    if not condition:
        raise GateError(message)


def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise GateError(f'Cannot read JSON {path}: {exc}') from exc


def command(args, cwd):
    try:
        return subprocess.run(args, cwd=cwd, text=True, capture_output=True,
                              check=True, timeout=120).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        # Do not include arbitrary process output, which can contain credentials.
        raise GateError(f'Command failed: {args[0]} ({type(exc).__name__})') from exc


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def discover(root=ROOT):
    """Collect real unittest/Vitest identities without running their test bodies."""
    root = Path(root).resolve()
    unit_refs = collect_unittests(root)
    runner = ast.parse((root / 'scripts/ci/concurrency_junit.py').read_text())
    scenario_names = []
    for node in runner.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'TESTS' for t in node.targets):
            scenario_names = ast.literal_eval(node.value)
    scenarios = collect_scenarios(root, scenario_names, unit_refs)
    raw = command(['node', 'node_modules/vitest/vitest.mjs', 'list', '--json'], root / 'apps/web')
    try:
        collected = json.loads(raw)
    except ValueError as exc:
        raise GateError('Vitest collection did not return JSON') from exc
    frontend = set()
    require(isinstance(collected, list), 'Invalid Vitest collection')
    for case in collected:
        require(isinstance(case, dict) and isinstance(case.get('name'), str) and case['name'], 'Invalid Vitest case')
        path = Path(case['file']).resolve()
        require(path.is_relative_to(root / 'apps/web'), 'Vitest file is outside the application')
        ref = path.relative_to(root).as_posix() + '::' + case['name']
        require(ref not in frontend, f'Duplicate collected frontend identity: {ref}')
        frontend.add(ref)
    require(unit_refs and frontend and scenarios, 'Empty test inventory')
    return {'database': unit_refs, 'concurrency': scenarios, 'frontend': frontend}


def collect_unittests(root):
    """Collect nested and top-level database TestCases without executing them."""
    sys.path.insert(0, str(root))
    unit_refs = set()
    for path in sorted((root / 'tests/database').rglob('test_*.py')):
        module = '.'.join(path.relative_to(root).with_suffix('').parts)
        loader = unittest.TestLoader()
        tests = list(flatten(loader.loadTestsFromName(module)))
        require(not loader.errors, f'Python collection failed: {module}')
        for test in tests:
            method = getattr(test, test._testMethodName)
            disabled = any(getattr(item, flag, False) for item in (test, method)
                           for flag in ('__unittest_skip__', '__unittest_expecting_failure__'))
            require(not disabled, f'Disabled or expected-failure database case: {test.id()}')
            require(test.id() not in unit_refs, f'Duplicate collected test: {test.id()}')
            unit_refs.add(test.id())
    return unit_refs


def is_main_guard(node):
    if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
        return False
    test = node.test
    return (len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)
            and isinstance(test.left, ast.Name) and test.left.id == '__name__'
            and len(test.comparators) == 1 and isinstance(test.comparators[0], ast.Constant)
            and test.comparators[0].value == '__main__')


def source_fingerprint(root):
    """Bind plans and execution receipts to nonignored checkout bytes and modes."""
    root = Path(root).resolve()
    names = command(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], root)
    digest = hashlib.sha256()
    for name in sorted(set(filter(None, names.split('\0')))):
        if name.startswith('test-results/'):
            continue
        path = root / name
        digest.update(name.encode() + b'\0')
        if path.is_symlink():
            raise GateError(f'Source fingerprint does not support symlink: {name}')
        if path.is_file():
            digest.update(str(bool(path.stat().st_mode & 0o111)).encode() + b'\0')
            digest.update(hashlib.sha256(path.read_bytes()).digest())
        else:
            digest.update(b'deleted')
    return digest.hexdigest()


def path_matches(path, pattern):
    """Glob segments: * never crosses /; ** spans zero or more segments."""
    def match(parts, patterns):
        if not patterns:
            return not parts
        if patterns[0] == '**':
            return match(parts, patterns[1:]) or bool(parts and match(parts[1:], patterns))
        return bool(parts and fnmatch.fnmatchcase(parts[0], patterns[0]) and match(parts[1:], patterns[1:]))
    return match(path.split('/'), pattern.split('/'))


def collect_scenarios(root, names, unit_refs=()):
    """Reject orphan executable tests and collect runner-registered scenarios."""
    require(isinstance(names, list) and names, 'No standalone scenarios collected')
    require(all(isinstance(name, str) and Path(name).name == name for name in names), 'Invalid standalone scenario path')
    candidates = set()
    unit_modules = {ref.rsplit('.', 2)[0] for ref in unit_refs}
    for path in (root / 'tests/database').rglob('test_*.py'):
        tree = ast.parse(path.read_text())
        module = '.'.join(path.relative_to(root).with_suffix('').parts)
        has_main = any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == 'main' for node in tree.body)
        # Every test module must contribute collected TestCases or a registered
        # standalone scenario, regardless of how its entrypoint is spelled.
        if has_main or module not in unit_modules:
            candidates.add(path.relative_to(root / 'tests/database').as_posix())
    require(not candidates - set(names), 'Unregistered standalone tests: ' + ', '.join(sorted(candidates - set(names))))
    scenarios = set()
    for name in names:
        require(isinstance(name, str) and Path(name).name == name, 'Invalid standalone scenario path')
        path = root / 'tests/database' / name
        require(path.is_file(), f'Missing scenario: {name}')
        tree = ast.parse(path.read_text())
        require(any(isinstance(n, ast.FunctionDef) and n.name == 'main' for n in tree.body), f'Scenario has no synchronous main: {name}')
        guards = [node for node in tree.body if is_main_guard(node)]
        expected_call = ast.dump(ast.parse('main()').body[0])
        require(len(guards) == 1 and len(guards[0].body) == 1 and ast.dump(guards[0].body[0]) == expected_call, f'Scenario must invoke main() directly under its __main__ guard: {name}')
        ref = path.relative_to(root).as_posix()
        require(ref not in scenarios, f'Duplicate standalone scenario: {name}')
        scenarios.add(ref)
    return scenarios


def string_list(value):
    return isinstance(value, list) and all(isinstance(v, str) and v.strip() for v in value)


def validate_registry(registry, inventory, root=ROOT):
    require(isinstance(registry, dict) and type(registry.get('version')) is int and registry['version'] == 1
            and isinstance(registry.get('requirements'), list) and registry['requirements'], 'Invalid registry schema/version')
    seen = set()
    mapped = {suite: set() for suite in inventory}
    gaps = []
    for item in registry['requirements']:
        require(isinstance(item, dict), 'Invalid requirement schema')
        identifier = item.get('id')
        require(isinstance(identifier, str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9-]+', identifier), 'Invalid requirement ID')
        require(identifier not in seen, f'Duplicate requirement ID: {identifier}')
        seen.add(identifier)
        for field in ['domain', 'description']:
            require(isinstance(item.get(field), str) and item[field].strip(), f'{identifier}: Invalid {field}')
        require(isinstance(item.get('status'), str) and item['status'] in {'implemented', 'planned', 'deferred'}, f'{identifier}: Invalid status')
        require(isinstance(item.get('risk'), str) and item['risk'] in {'low','medium','high','critical'}, f'{identifier}: Invalid risk')
        require(isinstance(item.get('coverage'), str) and item['coverage'] in {'covered','partial','missing'}, f'{identifier}: Invalid coverage')
        for field in ['scenarios', 'sources']:
            require(string_list(item.get(field)) and item[field], f'{identifier}: Invalid {field}')
        for source in item['sources']:
            path = (Path(root) / source).resolve()
            require(not Path(source).is_absolute() and path.is_relative_to(Path(root).resolve()) and path.is_file(), f'{identifier}: Invalid source reference: {source}')
        tests = item.get('tests')
        require(isinstance(tests, list), f'{identifier}: Invalid tests')
        local = set()
        for test in tests:
            require(isinstance(test, dict) and isinstance(test.get('suite'), str) and test['suite'] in inventory and isinstance(test.get('ref'), str), f'{identifier}: Invalid executable test reference')
            suite, ref = test['suite'], test['ref']
            require(ref in inventory[suite], f'{identifier}: Unknown test reference: {ref}')
            require((suite, ref) not in local, f'{identifier}: Duplicate test reference')
            local.add((suite, ref))
            mapped[suite].add(ref)
        require((item['coverage'] == 'missing') == (not tests), f'{identifier}: Inconsistent coverage/test references')
        if item['status'] != 'implemented':
            require(not tests and item['coverage'] == 'missing', f'{identifier}: Planned/deferred work cannot claim implemented coverage')
        elif item['risk'] in {'high','critical'}:
            require(tests and item['coverage'] == 'covered', f'{identifier}: Blocking implemented security coverage gap')
        if item['coverage'] != 'covered':
            gaps.append({'id': identifier, 'status': item['status'], 'coverage': item['coverage'], 'description': item['description']})
    for suite, refs in inventory.items():
        missing = refs - mapped[suite]
        require(not missing, f'Unmapped {suite} tests: {", ".join(sorted(missing))}')
    return gaps


def validate_policy(policy):
    require(isinstance(policy, dict) and type(policy.get('version')) is int and policy['version'] == 1, 'Invalid policy schema/version')
    require(policy.get('always') == ['quality'], 'Policy cannot bypass mandatory quality checks')
    require(string_list(policy.get('unknown')) and set(policy['unknown']) == {'frontend','database'}, 'Unknown changes must select full regression')
    require(isinstance(policy.get('rules'), list) and policy['rules'], 'Invalid policy rules')
    names = set()
    for rule in policy['rules']:
        require(isinstance(rule, dict) and isinstance(rule.get('name'), str) and rule['name'] and rule['name'] not in names, 'Invalid/duplicate policy rule')
        names.add(rule['name'])
        require(string_list(rule.get('patterns')) and rule['patterns'], 'Invalid policy patterns')
        require(string_list(rule.get('suites')) and set(rule['suites']) <= SUITES, 'Invalid policy suite')
        if not set(rule['suites']) - {'quality'}:
            require(set(rule['patterns']) <= {'docs/**', 'README.md', 'apps/web/README.md'}, 'Only explicit documentation paths may omit execution suites')


def security_floor(path):
    """Non-configurable minimums: additive policy cannot turn security off."""
    if (path.startswith(('apps/web/src/lib/', 'apps/web/src/app/login/', '.github/', 'scripts/', 'quality/', 'tests/quality/', 'apps/web/src/app/api/'))
            or Path(path).name in {'package.json','package-lock.json','npm-shrinkwrap.json','pnpm-workspace.yaml','requirements.txt','pyproject.toml','Pipfile','uv.lock','pnpm-lock.yaml','yarn.lock'}
            or fnmatch.fnmatchcase(Path(path).name, 'requirements*.txt')
            or Path(path).name.endswith('.lock')
            or any(word in path.lower() for word in ('auth', 'middleware', 'proxy.ts', 'rls', 'guardian', 'connection', 'workspace', 'permission', 'security', 'consent'))):
        return {'frontend','database'}
    if path.startswith(('supabase/', 'tests/database/')):
        return {'database'}
    return set()


def select_suites(files, policy):
    validate_policy(policy)
    selected = {'quality': ['Mandatory registry, policy and engine validation']}
    if not files:
        return {**selected, 'frontend': ['No reliable change set; full regression'], 'database':['No reliable change set; full regression']}
    for path in files:
        require(isinstance(path, str) and path and not PurePosixPath(path).is_absolute()
                and '..' not in PurePosixPath(path).parts and '\\' not in path, 'Invalid changed path')
        matched = False
        for rule in policy['rules']:
            if any(path_matches(path, pattern) for pattern in rule['patterns']):
                matched = True
                for suite in rule['suites']:
                    selected.setdefault(suite, []).append(f'{path}: {rule["name"]}')
        for suite in security_floor(path):
            selected.setdefault(suite, []).append(f'{path}: mandatory security/dependency floor')
        if not matched:
            for suite in policy['unknown']:
                selected.setdefault(suite, []).append(f'{path}: unknown change; full regression')
    return {suite: sorted(set(reasons)) for suite, reasons in sorted(selected.items())}


def changed_files(root, base, head):
    if not base or set(base) == {'0'}:
        return [], 'No usable base; full regression'
    try:
        # A rewritten push can delete security files outside the merge-base
        # diff. Treat all non-ancestor histories conservatively.
        command(['git', 'merge-base', '--is-ancestor', base, head], root)
        # No rename folding: include both deleted and added paths.
        raw = command(['git','diff','--no-renames','--name-only','-z',f'{base}...{head}'], root)
        return sorted(set(filter(None, raw.split('\0')))), 'Git merge-base comparison'
    except GateError:
        return [], 'Git comparison unavailable; full regression'


def build_plan(root, files, comparison):
    inventory = discover(root)
    registry = read_json(root / 'quality/requirements.json')
    gaps = validate_registry(registry, inventory, root)
    policy = read_json(root / 'quality/policy.json')
    selected = select_suites(files, policy)
    return {'version':1, 'status':'planned', 'commit':command(['git','rev-parse','HEAD'], root).strip(),
            'generated_at':datetime.now(timezone.utc).isoformat(), 'source_fingerprint':source_fingerprint(root), 'comparison':comparison,
            'changed_files':files, 'selected':selected, 'gaps':gaps,
            'expected':{k:sorted(v) for k,v in inventory.items()}}


def find_report(directory, name):
    matches = list(Path(directory).rglob(name))
    require(len(matches) == 1, f'Missing or ambiguous evidence: {name}')
    path = matches[0]
    require(0 < path.stat().st_size <= 10_000_000, f'Empty or oversized evidence: {name}')
    return path


BROWSER_CASES = {
    'login.spec.ts::rejects an invalid email in the browser',
    'login.spec.ts::does not claim email delivery when live OTP is disabled',
    'schedule.spec.ts::shows a clearly labelled example schedule',
}


def junit_refs(path, suite):
    try:
        root = ET.parse(path).getroot()
        require(root.tag in {'testsuite','testsuites'}, f'Invalid JUnit root: {path.name}')
        groups = [root] if root.tag == 'testsuite' else list(root.iter('testsuite'))
        require(groups, f'No JUnit suites: {path.name}')
        refs = []
        for group in groups:
            cases = group.findall('testcase')
            require(int(group.get('tests', '-1')) == len(cases) and cases, f'Inconsistent/empty JUnit suite: {path.name}')
            require(all(int(group.get(key, '-1')) == 0 for key in ['failures','errors','skipped']), f'Unsuccessful JUnit suite: {path.name}')
            for case in cases:
                require(not any(case.find(tag) is not None for tag in ['failure','error','skipped']), f'Failed/skipped case: {path.name}')
                duration = float(case.get('time', '-1'))
                require(math.isfinite(duration) and duration >= 0, f'Invalid case duration: {path.name}')
                name, classname = case.get('name'), case.get('classname')
                require(name and classname, f'Missing case identity: {path.name}')
                if suite == 'frontend':
                    require(classname.startswith('src/') and '..' not in PurePosixPath(classname).parts, 'Invalid frontend case path')
                    ref = 'apps/web/' + classname + '::' + name
                elif suite == 'browser':
                    require(classname in {'login.spec.ts', 'schedule.spec.ts'}, 'Invalid browser case path')
                    ref = classname + '::' + name
                elif suite == 'concurrency':
                    require(classname == 'ParentPlus.Concurrency' and Path(name).name == name, 'Invalid standalone case identity')
                    ref = 'tests/database/' + name
                else:
                    ref = classname + '.' + name
                refs.append(ref)
        require(len(list(root.iter('testcase'))) == len(refs), f'Orphan JUnit cases: {path.name}')
        require(not any(node.tag in {'failure', 'error', 'skipped'} for node in root.iter()), f'Unsuccessful JUnit nodes: {path.name}')
        if root.tag == 'testsuites':
            if root.get('tests') is not None:
                require(int(root.get('tests')) == len(refs), f'Inconsistent JUnit root count: {path.name}')
            for key in ['failures', 'errors', 'skipped']:
                if root.get(key) is not None:
                    require(int(root.get(key)) == 0, f'Unsuccessful JUnit root: {path.name}')
        require(len(refs) == len(set(refs)), f'Duplicate runtime cases: {path.name}')
        return set(refs)
    except (OSError, ET.ParseError, ValueError, TypeError) as exc:
        raise GateError(f'Invalid evidence {path.name}: {exc}') from exc


def run_engine_tests(root, stream=None):
    loader = unittest.TestLoader()
    suite = loader.discover(str(root / 'tests/quality'))
    result = unittest.TextTestRunner(verbosity=2, stream=stream).run(suite)
    require(not loader.errors and result.testsRun > 0 and result.wasSuccessful() and not result.skipped and not result.expectedFailures,
            'Quality engine tests failed, skipped, expected failure or executed zero cases')
    return {'executed': result.testsRun, 'skipped': len(result.skipped), 'status': 'passed'}


def execution_context():
    return {'run_id': os.environ.get('GITHUB_RUN_ID', 'local'),
            'run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT', 'local')}


def report_names(suite):
    require(suite in {'frontend', 'database'}, 'Invalid receipt suite')
    return (['vitest-junit.xml', 'playwright-junit.xml'] if suite == 'frontend' else
            ['unittest-junit.xml', 'concurrency-junit.xml', 'cleanup-count.txt'])


def report_digests(directory, suite):
    return {name: hashlib.sha256(find_report(directory, name).read_bytes()).hexdigest()
            for name in report_names(suite)}


def create_receipt(root, suite, directory, plan=None):
    commit = command(['git', 'rev-parse', 'HEAD'], root).strip()
    fingerprint = source_fingerprint(root)
    if plan is not None:
        require(plan.get('commit') == commit and plan.get('source_fingerprint') == fingerprint,
                'Source changed since execution plan; rerun checks on current source')
    for name in report_names(suite):
        path = find_report(directory, name)
        if name.endswith('.xml'):
            kind = 'browser' if name == 'playwright-junit.xml' else ('concurrency' if name.startswith('concurrency') else suite)
            refs = junit_refs(path, kind)
            require(refs, 'Empty execution evidence')
            if kind == 'browser':
                require(refs == BROWSER_CASES, 'Browser evidence differs from required cases')
        else:
            require(path.read_text().strip() == '0', 'Database cleanup incomplete')
    receipt = {'version': 1, 'suite': suite, 'commit': commit,
               'source_fingerprint': fingerprint, **execution_context(),
               'generated_at': datetime.now(timezone.utc).isoformat(),
               'reports': report_digests(directory, suite)}
    path = Path(directory) / (suite + '-receipt.json')
    path.write_text(json.dumps(receipt, indent=2) + '\n')
    return path


def verify_receipt(plan, directory, suite):
    receipt = read_json(find_report(directory, suite + '-receipt.json'))
    require(isinstance(receipt, dict) and type(receipt.get('version')) is int and receipt['version'] == 1,
            f'Invalid {suite} execution receipt')
    for key, expected in {'suite': suite, 'commit': plan['commit'],
                          'source_fingerprint': plan['source_fingerprint'], **execution_context()}.items():
        require(receipt.get(key) == expected, f'Stale or unrelated {suite} receipt: {key}')
    require(receipt.get('reports') == report_digests(directory, suite), f'{suite} report digest mismatch')


def verify_evidence(plan, directory, results, commit):
    require(isinstance(plan, dict) and plan.get('version') == 1 and plan.get('commit') == commit, 'Invalid or stale plan commit')
    require(isinstance(plan.get('source_fingerprint'), str) and re.fullmatch('[0-9a-f]{64}', plan['source_fingerprint']), 'Missing source fingerprint')
    selected, expected = plan.get('selected'), plan.get('expected')
    require(isinstance(selected, dict) and 'quality' in selected and set(selected) <= SUITES, 'Invalid selected suites')
    require(isinstance(expected, dict), 'Missing expected test inventory')
    # Plans written by the CLI carry the change set; reapply protected floors.
    if 'changed_files' in plan:
        floors = {'quality'}
        if not plan['changed_files']:
            floors |= {'frontend','database'}
        for path in plan['changed_files']:
            floors |= security_floor(path)
        require(floors <= set(selected), 'Plan bypassed mandatory security suites')
    for suite in selected:
        require(results.get(suite) == 'success', f'Required {suite} job did not succeed')
    reports = {'frontend':'vitest-junit.xml', 'database':'unittest-junit.xml', 'concurrency':'concurrency-junit.xml'}
    verified = {}
    for suite in ['frontend','database','concurrency']:
        if ('database' if suite == 'concurrency' else suite) not in selected:
            continue
        refs = expected.get(suite)
        require(string_list(refs) and refs and len(refs) == len(set(refs)), f'Missing/invalid expected {suite} cases')
        path = find_report(directory, reports[suite])
        actual = junit_refs(path, suite)
        require(actual == set(refs), f'{suite} evidence differs from inventory: missing={sorted(set(refs)-actual)}, unexpected={sorted(actual-set(refs))}')
        verified[suite] = {'tests':len(actual), 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    if 'frontend' in selected:
        path = find_report(directory, 'playwright-junit.xml')
        actual = junit_refs(path, 'browser')
        require(actual == BROWSER_CASES, 'Browser evidence differs from required cases')
        verified['browser'] = {'tests': len(actual), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    if 'database' in selected:
        require(find_report(directory, 'cleanup-count.txt').read_text().strip() == '0', 'Database cleanup is missing or incomplete')
    for suite in set(selected) & {'frontend', 'database'}:
        verify_receipt(plan, directory, suite)
    return verified


def write_evidence(output, data):
    output.mkdir(parents=True, exist_ok=True)
    (output / 'quality-gate.json').write_text(json.dumps(data, indent=2) + '\n')
    lines = ['# ParentPlus Intelligent Quality Gate', '', f'Status: **{data["status"]}**', f'Commit: `{data.get("commit", "unknown")}`', f'Source fingerprint: `{data.get("source_fingerprint", "not established")}`', '']
    if data['status'] == 'planned':
        lines += ['This is a selection plan. Test success requires runtime evidence.', '']
    selection = data.get('selected')
    if not isinstance(selection, dict):
        selection = {}
    for suite, reasons in selection.items():
        lines += [f'## {suite}', ''] + [f'- {reason}' for reason in reasons] + ['']
    if data.get('verified'):
        lines += ['## Verified runtime evidence', ''] + [f'- {suite}: {item["tests"]} exact cases passed' for suite,item in data['verified'].items()] + ['']
    lines += ['## Coverage gaps', '']
    lines += [f'- {gap["id"]} ({gap["status"]}, {gap["coverage"]}): {gap["description"]}' for gap in data.get('gaps', [])] or ['Coverage not established.' if data['status'] == 'failed' else 'No registered gaps. This does not establish complete product coverage.']
    if data.get('error'):
        lines += ['', '## Blocking error', '', data['error']]
    (output / 'summary.md').write_text('\n'.join(lines) + '\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['plan','verify','inventory','attest','self-test'])
    parser.add_argument('--base')
    parser.add_argument('--suite', choices=['frontend', 'database'])
    parser.add_argument('--head', default='HEAD')
    parser.add_argument('--changed-file', action='append')
    parser.add_argument('--output', type=Path, default=ROOT / 'test-results/quality')
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--reports', type=Path)
    parser.add_argument('--job-result', action='append', default=[])
    args = parser.parse_args(argv)
    data = {'version':1, 'status':'failed'}
    try:
        if args.mode == 'self-test':
            result = run_engine_tests(ROOT)
            args.output.mkdir(parents=True, exist_ok=True)
            (args.output / 'engine-tests.json').write_text(json.dumps(result, indent=2) + '\n')
            return 0
        if args.mode == 'attest':
            require(args.suite and args.reports, 'Attestation requires --suite and --reports')
            plan = read_json(args.plan) if args.plan else None
            require(plan is not None or os.environ.get('GITHUB_ACTIONS') == 'true', 'Local attestation requires a pre-execution --plan')
            print(create_receipt(ROOT, args.suite, args.reports, plan))
            return 0
        if args.mode == 'inventory':
            print(json.dumps({k:sorted(v) for k,v in discover().items()}, indent=2))
            return 0
        if args.mode == 'plan':
            files, comparison = ((args.changed_file, 'Explicit local change set') if args.changed_file is not None else changed_files(ROOT, args.base, args.head))
            data = build_plan(ROOT, files, comparison)
        else:
            require(args.plan and args.reports, 'Verification requires --plan and --reports')
            data = read_json(args.plan)
            require(isinstance(data, dict), 'Invalid evidence plan')
            # Validate current source inventory as well as artifacts; do not accept
            # a stale plan after tests, registry or policy have changed locally.
            if args.base is not None:
                files, comparison = changed_files(ROOT, args.base, args.head)
            else:
                files, comparison = data.get('changed_files', []), 'Verification'
            current = build_plan(ROOT, files, comparison)
            require(data.get('expected') == current['expected'] and data.get('selected') == current['selected'] and data.get('gaps') == current['gaps'] and data.get('source_fingerprint') == current['source_fingerprint'], 'Plan selection/inventory/coverage is stale or modified')
            results = dict(item.split('=', 1) for item in args.job_result)
            verified = verify_evidence(data, args.reports, results, current['commit'])
            data.update(status='passed', verified=verified, job_results=results)
        write_evidence(args.output, data)
        print(f'{data["status"]}: {args.output / "summary.md"}')
        return 0
    except (GateError, OSError, ValueError, KeyError, TypeError, SyntaxError) as exc:
        data = {'version': 1, 'status': 'failed', 'error': str(exc)}
        write_evidence(args.output, data)
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
