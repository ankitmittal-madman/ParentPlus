"""Behavioral regression tests for selection, coverage and runtime evidence."""
import copy
import importlib.util
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('quality_gate', ROOT / 'scripts/quality/quality_gate.py')
if SPEC and SPEC.origin and Path(SPEC.origin).exists():
    gate = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(gate)
else:
    gate = None


class GateTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(gate, 'The quality-gate engine must implement the contract')
        self.inventory = {'frontend': {'apps/web/src/a.test.ts::A > works'},
                          'database': {'tests.database.test_a.Authorization.test_denied'},
                          'concurrency': {'tests/database/test_race.py'}}
        self.registry = {'version': 1, 'requirements': []}
        for i, (suite, refs) in enumerate(self.inventory.items()):
            self.registry['requirements'].append({
                'id': f'REQ-{i}', 'domain': 'authorization', 'description': 'Reject unauthorized access',
                'status': 'implemented', 'risk': 'critical', 'coverage': 'covered',
                'scenarios': ['unauthorized actor is denied'],
                'tests': [{'suite': suite, 'ref': next(iter(refs))}],
                'sources': ['AGENTS.md'],
            })
        self.policy = {'version': 1, 'always': ['quality'],
                       'unknown': ['frontend', 'database'], 'rules': [
            {'name': 'presentation', 'patterns': ['apps/web/src/ui/**'], 'suites': ['frontend']},
            {'name': 'database', 'patterns': ['supabase/**'], 'suites': ['database']},
            {'name': 'documentation', 'patterns': ['docs/**', 'README.md'], 'suites': []},
        ]}


    def test_sensitive_new_feature_paths_cannot_use_presentation_only_policy(self):
        for path in ['apps/web/src/app/api/children/route.ts', 'apps/web/src/modules/connections/approve.ts', 'apps/web/src/ui/guardian-access.tsx']:
            with self.subTest(path=path):
                self.assertEqual(set(gate.select_suites([path], self.policy)), {'quality','frontend','database'})

    def test_git_rename_includes_deleted_security_path(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            def git(*args):
                return subprocess.run(['git', *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
            git('init', '-q')
            old = root / 'auth.ts'
            old.write_text('sensitive source')
            git('add', '.')
            git('-c','user.name=Test','-c','user.email=test@example.test','commit','-qm','base')
            base = git('rev-parse','HEAD')
            old.rename(root / 'button.ts')
            git('add', '-A')
            git('-c','user.name=Test','-c','user.email=test@example.test','commit','-qm','rename')
            files, _ = gate.changed_files(root, base, 'HEAD')
            self.assertEqual(files, ['auth.ts','button.ts'])
            self.assertIn('database', gate.select_suites(files, self.policy))

    def test_missing_git_base_selects_everything(self):
        with tempfile.TemporaryDirectory() as d:
            files, reason = gate.changed_files(Path(d), 'missing-ref', 'HEAD')
            self.assertEqual(files, [])
            self.assertIn('unavailable', reason)
            self.assertEqual(set(gate.select_suites(files, self.policy)), {'quality','frontend','database'})

    def test_malformed_policy_and_changed_path_are_rejected(self):
        for policy in [None, {}, {'version':1, 'always':['quality'], 'unknown':['frontend','database'], 'rules':[None]}]:
            with self.subTest(policy=policy), self.assertRaises(gate.GateError):
                gate.select_suites(['README.md'], policy)
        for path in ['/outside', '../escape', 'bad\\path']:
            with self.subTest(path=path), self.assertRaises(gate.GateError):
                gate.select_suites([path], self.policy)

    def test_junit_root_counters_cannot_contradict_cases(self):
        with tempfile.TemporaryDirectory() as d:
            plan, results, unit = self.evidence_fixture(Path(d))
            unit.write_text(unit.read_text().replace('<testsuites>', '<testsuites tests="1" failures="1" errors="0">'))
            with self.assertRaises(gate.GateError):
                gate.verify_evidence(plan, Path(d), results, 'a'*40)

    def test_malformed_plan_still_produces_failed_json_and_summary(self):
        with tempfile.TemporaryDirectory() as d:
            plan = Path(d)/'plan.json'
            plan.write_text(json.dumps({'version':1, 'selected':[], 'expected':{}}))
            output = Path(d)/'output'
            result = subprocess.run([sys.executable, str(ROOT/'scripts/quality/quality_gate.py'),
                                     'verify','--plan',str(plan),'--reports',d,'--output',str(output)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads((output/'quality-gate.json').read_text())['status'], 'failed')
            self.assertIn('failed', (output/'summary.md').read_text())


    def test_nested_schema_types_fail_with_actionable_validation_errors(self):
        for field, value in [('status', []), ('risk', {}), ('coverage', []), ('tests', [{'suite': [], 'ref': 'x'}])]:
            registry = copy.deepcopy(self.registry)
            registry['requirements'][0][field] = value
            with self.subTest(field=field), self.assertRaises(gate.GateError):
                gate.validate_registry(registry, self.inventory, ROOT)
        policy = copy.deepcopy(self.policy)
        policy['rules'][0]['suites'] = [[]]
        with self.assertRaises(gate.GateError):
            gate.select_suites(['README.md'], policy)

    def test_boolean_version_is_not_schema_version_one(self):
        self.registry['version'] = True
        with self.assertRaises(gate.GateError):
            gate.validate_registry(self.registry, self.inventory, ROOT)


    def test_force_push_cannot_hide_removed_security_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            def git(*args):
                return subprocess.run(['git', *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
            git('init', '-q')
            (root/'README.md').write_text('base')
            git('add', '.')
            git('-c','user.name=Test','-c','user.email=test@example.test','commit','-qm','base')
            ancestor = git('rev-parse','HEAD')
            (root/'auth.ts').write_text('sensitive source')
            git('add', '.')
            git('-c','user.name=Test','-c','user.email=test@example.test','commit','-qm','old head')
            before = git('rev-parse','HEAD')
            git('checkout','-q','--detach',ancestor)
            (root/'README.md').write_text('rewritten history')
            git('add', '.')
            git('-c','user.name=Test','-c','user.email=test@example.test','commit','-qm','new head')
            files, _ = gate.changed_files(root, before, 'HEAD')
            self.assertEqual(set(gate.select_suites(files, self.policy)), {'quality','frontend','database'})


    def test_unregistered_standalone_main_cannot_disappear_from_inventory(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            directory = root/'tests/database'
            directory.mkdir(parents=True)
            (directory/'test_registered.py').write_text('def main():\n    pass\nif __name__ == "__main__":\n    main()\n')
            (directory/'test_orphan.py').write_text('def main():\n    raise AssertionError("not executed")\n')
            with self.assertRaisesRegex(gate.GateError, 'Unregistered standalone'):
                gate.collect_scenarios(root, ['test_registered.py'])

    def test_standalone_inventory_validates_executable_registration(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            directory = root/'tests/database'
            directory.mkdir(parents=True)
            (directory/'test_registered.py').write_text('def main():\n    raise AssertionError("collection must not execute test")\nif __name__ == "__main__":\n    main()\n')
            self.assertEqual(gate.collect_scenarios(root, ['test_registered.py']), {'tests/database/test_registered.py'})
            for names in [['missing.py'], ['test_registered.py','test_registered.py'], ['../outside.py']]:
                with self.subTest(names=names), self.assertRaises(gate.GateError):
                    gate.collect_scenarios(root, names)

    def test_dependency_floor_protects_named_requirements_and_lockfiles(self):
        policy = copy.deepcopy(self.policy)
        policy['rules'].insert(0, {'name':'weakened dependency rule', 'patterns':['**'], 'suites':['frontend']})
        for path in ['requirements-dev.txt', 'services/api/requirements-prod.txt', 'apps/web/npm-shrinkwrap.json', 'Pipfile.lock', 'services/api/poetry.lock', 'pnpm-workspace.yaml']:
            with self.subTest(path=path):
                self.assertEqual(set(gate.select_suites([path], policy)), {'quality','frontend','database'})


    def test_plan_cannot_hide_current_coverage_gaps(self):
        with tempfile.TemporaryDirectory() as d:
            plan = gate.build_plan(ROOT, ['docs/DECISION_LOG.md'], 'test')
            self.assertTrue(plan['gaps'])
            plan['gaps'] = []
            path = Path(d)/'plan.json'
            path.write_text(json.dumps(plan))
            result = subprocess.run([sys.executable, str(ROOT/'scripts/quality/quality_gate.py'),
                'verify', '--plan', str(path), '--reports', d, '--job-result', 'quality=success',
                '--output', str(Path(d)/'output')], text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('stale or modified', result.stderr)


    def test_nested_unittest_cases_are_collected_without_running(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            directory = root/'tests/database/children'
            directory.mkdir(parents=True)
            for package in [root/'tests', root/'tests/database', directory]:
                (package/'__init__.py').write_text('')
            (directory/'test_permissions.py').write_text('import unittest\nclass Permissions(unittest.TestCase):\n    def test_denied(self):\n        raise AssertionError("body must not run during collection")\n')
            script = 'import json,runpy,sys; from pathlib import Path; g=runpy.run_path(sys.argv[1]); print(json.dumps(sorted(g["collect_unittests"](Path(sys.argv[2])))))'
            result = subprocess.run([sys.executable, '-c', script, str(ROOT/'scripts/quality/quality_gate.py'), str(root)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), ['tests.database.children.test_permissions.Permissions.test_denied'])

    def test_nested_standalone_tests_cannot_be_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            directory = root/'tests/database'
            (directory/'children').mkdir(parents=True)
            (directory/'test_registered.py').write_text('def main():\n    pass\nif __name__ == "__main__":\n    main()\n')
            (directory/'children/test_orphan.py').write_text('def main():\n    raise AssertionError("not executed")\n')
            with self.assertRaisesRegex(gate.GateError, 'Unregistered standalone'):
                gate.collect_scenarios(root, ['test_registered.py'])


    def test_root_config_globs_do_not_match_unknown_descendants(self):
        policy = json.loads((ROOT/'quality/policy.json').read_text())
        self.assertEqual(set(gate.select_suites(['apps/web/next.config.ts'], policy)), {'quality','frontend'})
        for path in ['apps/web/src/new-domain/service.ts', 'apps/web/src/modules/billing/calculate.ts']:
            self.assertEqual(set(gate.select_suites([path], policy)), {'quality','frontend','database'})

    def test_unregistered_executable_forms_cannot_escape_inventory(self):
        for body in ['', 'if "__main__" == __name__:\n    raise AssertionError("must run")\n', 'if __name__ == "__main__":\n    raise AssertionError("must run")\n',
                     'async def main():\n    raise AssertionError("must run")\n',
                     'def run_tests():\n    raise AssertionError("must run")\nif __name__ == "__main__":\n    run_tests()\n']:
            with self.subTest(body=body), tempfile.TemporaryDirectory() as d:
                root=Path(d); directory=root/'tests/database'; directory.mkdir(parents=True)
                (directory/'test_registered.py').write_text('def main():\n    pass\nif __name__ == "__main__":\n    main()\n')
                (directory/'test_orphan.py').write_text(body)
                with self.assertRaises(gate.GateError):
                    gate.collect_scenarios(root, ['test_registered.py'])

    def test_registered_standalone_requires_a_real_entrypoint(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); directory=root/'tests/database'; directory.mkdir(parents=True)
            path=directory/'test_registered.py'
            path.write_text('def main():\n    raise AssertionError("never invoked")\n')
            with self.assertRaises(gate.GateError):
                gate.collect_scenarios(root, ['test_registered.py'])

    def test_source_fingerprint_detects_body_edits_and_new_files(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            subprocess.run(['git','init','-q'],cwd=root,check=True)
            (root/'.gitignore').write_text('test-results/\n.env\n')
            file=root/'test_body.py';file.write_text('assert True\n')
            before=gate.source_fingerprint(root)
            file.write_text('assert False\n')
            self.assertNotEqual(before, gate.source_fingerprint(root))
            current=gate.source_fingerprint(root)
            (root/'test-results').mkdir();(root/'test-results/report.json').write_text('{}')
            (root/'.env').write_text('LOCAL_ONLY=value')
            self.assertEqual(current, gate.source_fingerprint(root))
            (root/'new-test.py').write_text('assert False')
            self.assertNotEqual(current, gate.source_fingerprint(root))

    def test_junit_cannot_hide_orphan_failure_nodes(self):
        with tempfile.TemporaryDirectory() as d:
            _, _, unit=self.evidence_fixture(Path(d))
            unit.write_text(unit.read_text().replace('</testsuites>', '<testcase classname="extra" name="hidden" time="0"><failure/></testcase></testsuites>'))
            with self.assertRaises(gate.GateError):
                gate.junit_refs(unit, 'database')


    def test_evidence_requires_source_bound_execution_receipts(self):
        for mutation in ['missing', 'source', 'run', 'digest']:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as d:
                directory=Path(d); plan,results,_=self.evidence_fixture(directory)
                self.write_receipt_fixture(directory, plan)
                receipt=directory/'database-receipt.json'
                data=json.loads(receipt.read_text())
                if mutation=='missing': receipt.unlink()
                else:
                    if mutation=='source': data['source_fingerprint']='0'*64
                    elif mutation=='run': data['run_id']='another-run'
                    else: data['reports']['unittest-junit.xml']='0'*64
                    receipt.write_text(json.dumps(data))
                with self.assertRaises(gate.GateError):
                    gate.verify_evidence(plan,directory,results,'a'*40)

    def test_docs_only_rule_cannot_hide_arbitrary_source_files(self):
        for suites in [[], ['quality']]:
            policy=copy.deepcopy(self.policy)
            policy['rules'].append({'name':'accidental bypass','patterns':['**'],'suites':suites})
            with self.assertRaises(gate.GateError):
                gate.select_suites(['new-domain/code.ts'], policy)

    def test_quality_runner_rejects_zero_or_skipped_tests(self):
        for body in ['', 'import unittest\n@unittest.skip("later")\nclass Checks(unittest.TestCase):\n    def test_security(self):\n        self.fail("must not pass by skipping")\n']:
            with self.subTest(body=body), tempfile.TemporaryDirectory() as d:
                root=Path(d); directory=root/'tests/quality'; directory.mkdir(parents=True)
                (directory/('test_empty.py' if not body else 'test_skipped.py')).write_text(body)
                with self.assertRaises(gate.GateError):
                    gate.run_engine_tests(root, stream=io.StringIO())

    def write_receipt_fixture(self, directory, plan):
        plan.setdefault('source_fingerprint','f'*64)
        for suite, names in [('frontend',['vitest-junit.xml','playwright-junit.xml','playwright-enabled-junit.xml']), ('database',['unittest-junit.xml','concurrency-junit.xml','cleanup-count.txt'])]:
            if suite in plan['selected']:
                receipt={'version':1, 'suite':suite, 'commit':plan['commit'],
                    'source_fingerprint':plan['source_fingerprint'],
                    'run_id':os.environ.get('GITHUB_RUN_ID','local'),
                    'run_attempt':os.environ.get('GITHUB_RUN_ATTEMPT','local'),
                    'reports':{name:hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in names if (directory/name).exists()}}
                (directory/(suite+'-receipt.json')).write_text(json.dumps(receipt))


    def test_quality_runner_rejects_expected_failure_as_success(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); directory=root/'tests/quality'; directory.mkdir(parents=True)
            (directory/'test_expected.py').write_text('import unittest\nclass Checks(unittest.TestCase):\n    @unittest.expectedFailure\n    def test_security(self):\n        self.fail("not implemented")\n')
            with self.assertRaises(gate.GateError):
                gate.run_engine_tests(root, stream=io.StringIO())

    def test_database_collection_rejects_disabled_or_expected_failure_cases(self):
        for decorator in ['@unittest.expectedFailure', '@unittest.skip("later")']:
            with self.subTest(decorator=decorator), tempfile.TemporaryDirectory() as d:
                root=Path(d); directory=root/'tests/database'; directory.mkdir(parents=True)
                for package in [root/'tests', directory]: (package/'__init__.py').write_text('')
                (directory/'test_disabled.py').write_text('import unittest\nclass Checks(unittest.TestCase):\n    '+decorator+'\n    def test_security(self):\n        self.fail("must not count as covered")\n')
                script='import runpy,sys; from pathlib import Path; g=runpy.run_path(sys.argv[1]); g["collect_unittests"](Path(sys.argv[2]))'
                result=subprocess.run([sys.executable,'-c',script,str(ROOT/'scripts/quality/quality_gate.py'),str(root)],capture_output=True,text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Disabled or expected-failure', result.stderr)

    def test_valid_registry(self):
        gate.validate_registry(self.registry, self.inventory, ROOT)

    def test_invalid_schema(self):
        for bad in [None, [], {}, {'version': 2, 'requirements': []}]:
            with self.subTest(bad=bad), self.assertRaises(gate.GateError):
                gate.validate_registry(bad, self.inventory, ROOT)

    def test_duplicate_id(self):
        self.registry['requirements'][1]['id'] = 'REQ-0'
        with self.assertRaisesRegex(gate.GateError, 'Duplicate'):
            gate.validate_registry(self.registry, self.inventory, ROOT)

    def test_missing_reference(self):
        self.registry['requirements'][0]['tests'][0]['ref'] = 'nonexistent'
        with self.assertRaisesRegex(gate.GateError, 'Unknown test'):
            gate.validate_registry(self.registry, self.inventory, ROOT)

    def test_critical_implemented_without_coverage(self):
        self.registry['requirements'][0].update(coverage='missing', tests=[])
        with self.assertRaisesRegex(gate.GateError, 'coverage'):
            gate.validate_registry(self.registry, self.inventory, ROOT)

    def test_new_unmapped_test_is_blocking(self):
        self.inventory['database'].add('tests.database.test_new.RLS.test_denied')
        with self.assertRaisesRegex(gate.GateError, 'Unmapped'):
            gate.validate_registry(self.registry, self.inventory, ROOT)

    def test_planned_and_deferred_are_visible_nonblocking_gaps(self):
        for status in ['planned', 'deferred']:
            item = copy.deepcopy(self.registry['requirements'][0])
            item.update(id='FUTURE-'+status, status=status, coverage='missing', tests=[])
            self.registry['requirements'].append(item)
        gaps = gate.validate_registry(self.registry, self.inventory, ROOT)
        self.assertEqual({g['id'] for g in gaps}, {'FUTURE-planned', 'FUTURE-deferred'})

    def test_planned_cannot_claim_implemented_test_coverage(self):
        self.registry['requirements'][0]['status'] = 'planned'
        with self.assertRaises(gate.GateError):
            gate.validate_registry(self.registry, self.inventory, ROOT)

    def test_bad_requirement_fields_and_source_paths(self):
        for field, value in [('risk', 'safe'), ('status','done'), ('tests', 'test'),
                             ('scenarios', []), ('sources', ['../outside']),
                             ('sources', ['missing-doc.md']), ('description','')]:
            registry = copy.deepcopy(self.registry)
            registry['requirements'][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(gate.GateError):
                gate.validate_registry(registry, self.inventory, ROOT)

    def test_frontend_changes_select_frontend(self):
        self.assertEqual(set(gate.select_suites(['apps/web/src/ui/button.tsx'], self.policy)), {'quality','frontend'})

    def test_authentication_changes_force_both(self):
        for path in ['apps/web/src/lib/auth/new.ts', 'apps/web/src/app/login/page.tsx',
                     'apps/web/src/lib/supabase/server.ts', 'apps/web/src/middleware.ts']:
            with self.subTest(path=path):
                self.assertEqual(set(gate.select_suites([path], self.policy)), {'quality','frontend','database'})

    def test_database_migrations_and_relationships_force_database(self):
        for path in ['supabase/migrations/new_rls.sql', 'tests/database/test_guardian.py']:
            self.assertIn('database', gate.select_suites([path], self.policy))

    def test_shared_dependencies_force_both(self):
        for path in ['apps/web/package-lock.json', 'apps/web/package.json', 'requirements.txt', 'apps/web/src/lib/shared.ts']:
            self.assertEqual(set(gate.select_suites([path], self.policy)), {'quality','frontend','database'})

    def test_unknown_changes_are_full_regression(self):
        self.assertEqual(set(gate.select_suites(['new-service/unknown.go'], self.policy)), {'quality','frontend','database'})

    def test_no_changed_files_is_full_regression(self):
        self.assertEqual(set(gate.select_suites([], self.policy)), {'quality','frontend','database'})

    def test_ci_gate_and_policy_changes_force_both(self):
        for path in ['.github/workflows/new.yml', 'scripts/ci/check.sh', 'quality/policy.json', 'scripts/quality/quality_gate.py', 'tests/quality/test_new.py']:
            self.assertEqual(set(gate.select_suites([path], self.policy)), {'quality','frontend','database'})

    def test_security_floor_survives_permissive_matching_rule(self):
        self.policy['rules'].insert(0, {'name':'bypass','patterns':['**'], 'suites':['frontend']})
        self.assertIn('database', gate.select_suites(['supabase/migrations/rls.sql'], self.policy))
        self.assertIn('database', gate.select_suites(['apps/web/src/lib/auth/otp.ts'], self.policy))

    def test_invalid_policy_cannot_disable_always_or_unknown(self):
        for key in ['always','unknown']:
            policy = copy.deepcopy(self.policy)
            policy[key] = []
            with self.subTest(key=key), self.assertRaises(gate.GateError):
                gate.select_suites(['docs/a.md'], policy)

    def test_invalid_policy_suite_rejected(self):
        self.policy['rules'][0]['suites'] = ['fake']
        with self.assertRaises(gate.GateError):
            gate.select_suites(['apps/web/src/ui/a.tsx'], self.policy)

    def test_reasons_explain_selection(self):
        selected = gate.select_suites(['apps/web/src/ui/button.tsx'], self.policy)
        self.assertTrue(any('button.tsx' in why for why in selected['frontend']))

    def evidence_fixture(self, directory):
        plan = {'version':1, 'commit':'a'*40, 'selected':{'quality':['mandatory'], 'database':['security']},
                'expected':{'database':['tests.database.test_a.Authorization.test_denied'],
                            'concurrency':['tests/database/test_race.py']},
                'job_results': {}}
        unit = directory/'unittest-junit.xml'
        unit.write_text('<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0"><testcase classname="tests.database.test_a.Authorization" name="test_denied" time="0.1"/></testsuite></testsuites>')
        race = directory/'concurrency-junit.xml'
        race.write_text('<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0"><testcase classname="ParentPlus.Concurrency" name="test_race.py" time="0.1"/></testsuite></testsuites>')
        (directory/'cleanup-count.txt').write_text('0\n')
        self.write_receipt_fixture(directory, plan)
        return plan, {'database':'success','quality':'success'}, unit

    def test_valid_exact_runtime_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            plan, results, _ = self.evidence_fixture(Path(d))
            gate.verify_evidence(plan, Path(d), results, 'a'*40)

    def test_missing_invalid_skipped_duplicate_failed_evidence_rejected(self):
        for mutation in ['missing','malformed','skipped','failed','duplicate','wrong_case','zero','nan','inconsistent']:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as d:
                plan, results, unit = self.evidence_fixture(Path(d))
                content = unit.read_text()
                if mutation == 'missing': unit.unlink()
                elif mutation == 'malformed': unit.write_text('<broken')
                elif mutation == 'skipped': unit.write_text(content.replace('/></testsuite>', '><skipped/></testcase></testsuite>'))
                elif mutation == 'failed': unit.write_text(content.replace('failures="0"','failures="1"'))
                elif mutation == 'duplicate': unit.write_text(content.replace('</testsuite>', '<testcase classname="tests.database.test_a.Authorization" name="test_denied" time="0.1"/></testsuite>'))
                elif mutation == 'wrong_case': unit.write_text(content.replace('test_denied','test_other'))
                elif mutation == 'zero': unit.write_text('<testsuites/>')
                elif mutation == 'nan': unit.write_text(content.replace('0.1', 'NaN'))
                else: unit.write_text(content.replace('tests="1"','tests="2"'))
                self.write_receipt_fixture(Path(d), plan)
                with self.assertRaises(gate.GateError):
                    gate.verify_evidence(plan, Path(d), results, 'a'*40)

    def test_stale_commit_unsuccessful_or_skipped_jobs_block(self):
        for change in ['commit','job','missing_job','cleanup']:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as d:
                plan, results, _ = self.evidence_fixture(Path(d))
                if change == 'commit': plan['commit'] = 'b'*40
                elif change == 'job': results['database'] = 'skipped'
                elif change == 'missing_job': results.pop('database')
                else: (Path(d)/'cleanup-count.txt').write_text('1')
                self.write_receipt_fixture(Path(d), plan)
                with self.assertRaises(gate.GateError):
                    gate.verify_evidence(plan, Path(d), results, 'a'*40)

    def write_browser_fixture(self, directory):
        self.write_enabled_browser_fixture(directory)
        (directory/'playwright-junit.xml').write_text('<testsuites tests="4" failures="0" errors="0" skipped="0"><testsuite tests="3" failures="0" errors="0" skipped="0"><testcase classname="login.spec.ts" name="rejects an invalid email in the browser" time="0.1"/><testcase classname="login.spec.ts" name="does not claim email delivery when live OTP is disabled" time="0.1"/><testcase classname="login.spec.ts" name="keeps parent profiles unavailable when disabled" time="0.1"/></testsuite><testsuite tests="1" failures="0" errors="0" skipped="0"><testcase classname="schedule.spec.ts" name="shows a clearly labelled example schedule" time="0.1"/></testsuite></testsuites>')

    def write_enabled_browser_fixture(self, directory):
        (directory/'playwright-enabled-junit.xml').write_text('<testsuites tests="3" failures="0" errors="0" skipped="0"><testsuite tests="3" failures="0" errors="0" skipped="0"><testcase classname="parent-enabled.spec.mjs" name="creates and confirms a profile using a synthetic provider" time="0.1"/><testcase classname="parent-enabled.spec.mjs" name="recovers an unconfirmed request after another tab creates a later profile" time="0.1"/><testcase classname="parent-enabled.spec.mjs" name="keeps an unresolved request locked after an account switch" time="0.1"/></testsuite></testsuites>')

    def test_browser_evidence_rejects_skips_missing_cases_and_tampering(self):
        for mutation in ['missing', 'skipped', 'wrong_case', 'digest']:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as d:
                directory = Path(d)
                plan = {'version': 1, 'commit': 'a'*40, 'selected': {'quality': [], 'frontend': []},
                        'expected': {'frontend': ['apps/web/src/a.test.ts::A > works']}}
                (directory/'vitest-junit.xml').write_text('<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0"><testcase classname="src/a.test.ts" name="A &gt; works" time="0.1"/></testsuite></testsuites>')
                self.write_browser_fixture(directory)
                self.write_receipt_fixture(directory, plan)
                report = directory/'playwright-junit.xml'
                if mutation == 'missing':
                    report.unlink()
                elif mutation == 'skipped':
                    report.write_text(report.read_text().replace('skipped="0"', 'skipped="1"'))
                elif mutation == 'wrong_case':
                    report.write_text(report.read_text().replace('rejects an invalid email in the browser', 'different case'))
                else:
                    report.write_text(report.read_text().replace('time="0.1"', 'time="0.2"', 1))
                if mutation in {'skipped', 'wrong_case'}:
                    self.write_receipt_fixture(directory, plan)
                with self.assertRaises(gate.GateError):
                    gate.verify_evidence(plan, directory, {'quality': 'success', 'frontend': 'success'}, 'a'*40)

    def test_frontend_requires_browser_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            plan = {'version': 1, 'commit': 'a'*40, 'selected': {'quality': [], 'frontend': []},
                    'expected': {'frontend': ['apps/web/src/a.test.ts::A > works']}}
            Path(d, 'vitest-junit.xml').write_text('<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0"><testcase classname="src/a.test.ts" name="A &gt; works" time="0.1"/></testsuite></testsuites>')
            self.write_receipt_fixture(Path(d), plan)
            with self.assertRaises(gate.GateError):
                gate.verify_evidence(plan, Path(d), {'quality': 'success', 'frontend': 'success'}, 'a'*40)

    def test_enabled_browser_evidence_rejects_skips_missing_cases_and_tampering(self):
        for mutation in ['missing', 'skipped', 'wrong_case', 'digest']:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as d:
                directory = Path(d)
                plan = {'version': 1, 'commit': 'a'*40, 'selected': {'quality': [], 'frontend': []},
                        'expected': {'frontend': ['apps/web/src/a.test.ts::A > works']}}
                (directory/'vitest-junit.xml').write_text('<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0"><testcase classname="src/a.test.ts" name="A &gt; works" time="0.1"/></testsuite></testsuites>')
                self.write_browser_fixture(directory)
                self.write_receipt_fixture(directory, plan)
                report = directory/'playwright-enabled-junit.xml'
                if mutation == 'missing': report.unlink()
                elif mutation == 'skipped': report.write_text(report.read_text().replace('skipped="0"', 'skipped="1"'))
                elif mutation == 'wrong_case': report.write_text(report.read_text().replace('creates and confirms a profile using a synthetic provider', 'different case'))
                else: report.write_text(report.read_text().replace('time="0.1"', 'time="0.2"', 1))
                if mutation in {'skipped', 'wrong_case'}: self.write_receipt_fixture(directory, plan)
                with self.assertRaises(gate.GateError):
                    gate.verify_evidence(plan, directory, {'quality': 'success', 'frontend': 'success'}, 'a'*40)

    def test_enabled_browser_stops_when_namespace_or_caller_is_unsafe(self):
        with tempfile.TemporaryDirectory() as d:
            fake = Path(d)/'unshare'
            fake.write_text('#!/bin/sh\nexit 1\n')
            fake.chmod(0o755)
            env = {'PATH': d+os.pathsep+os.environ.get('PATH', ''), 'PARENTPLUS_CHROMIUM_PATH': '/bin/true', 'PARENTPLUS_SKIP_PRIVILEGED_FALLBACK': '1'}
            result = subprocess.run(['bash', str(ROOT/'scripts/ci/enabled-parent-browser.sh')], cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            expected = 'browser runner cannot run as root' if os.getuid() == 0 or os.getgid() == 0 else 'network namespace is unavailable'
            self.assertIn(expected, result.stderr)
            self.assertNotIn('PASS: Isolated enabled parent browser checks completed', result.stdout)

    def test_enabled_browser_rejects_an_unverified_privilege_drop(self):
        with tempfile.TemporaryDirectory() as d:
            env = {'PATH': os.environ.get('PATH', ''), 'PARENTPLUS_SYNTHETIC_BROWSER': '1',
                   'PARENTPLUS_VERIFY_DROPPED_UID': str(os.getuid()+1), 'PARENTPLUS_VERIFY_DROPPED_GID': str(os.getgid()+1)}
            result = subprocess.run(['bash', str(ROOT/'scripts/ci/enabled-parent-browser-inner.sh'), d], cwd=ROOT, env=env, capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('privileged bootstrap verification failed', result.stderr)
            self.assertFalse((Path(d)/'test-next.log').exists())

    def test_privileged_browser_verifier_rejects_each_unsafe_identity_or_capability(self):
        import runpy
        verify = runpy.run_path(str(ROOT/'scripts/ci/verify-browser-privileges.py'))['valid_drop']
        fields = {'Uid': '1001 1001 1001 1001', 'Gid': '1002 1002 1002 1002', 'Groups': '',
                  'CapInh': '0000000000000000', 'CapPrm': '0000000000000000', 'CapEff': '0000000000000000',
                  'CapBnd': '0000000000000000', 'CapAmb': '0000000000000000', 'NoNewPrivs': '1'}
        self.assertTrue(verify(fields, 1001, 1002))
        changes = {'Uid': '1001 0 1001 1001', 'Gid': '1002 1002 0 1002', 'Groups': '1002',
                   'CapInh': '1', 'CapPrm': '1', 'CapEff': '1', 'CapBnd': '1', 'CapAmb': '1', 'NoNewPrivs': '0'}
        for name, value in changes.items():
            with self.subTest(field=name):
                bad = dict(fields); bad[name] = value
                self.assertFalse(verify(bad, 1001, 1002))
        missing = dict(fields); missing.pop('CapEff')
        self.assertFalse(verify(missing, 1001, 1002))
        self.assertFalse(verify(fields, 0, 1002))
        self.assertFalse(verify(fields, 1001, 0))
        empty_uid = dict(fields); empty_uid['Uid'] = ''
        self.assertFalse(verify(empty_uid, 1001, 1002))
        invalid_capability = dict(fields); invalid_capability['CapPrm'] = 'not-hex'
        self.assertFalse(verify(invalid_capability, 1001, 1002))

    def test_enabled_browser_config_rejects_nonlocal_provider(self):
        env = {'PATH': os.environ.get('PATH', ''), 'PARENTPLUS_SYNTHETIC_BROWSER': '1',
               'PARENTPLUS_CHROMIUM_PATH': '/synthetic/browser', 'NEXT_PUBLIC_SUPABASE_URL': 'https://example.invalid',
               'NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY': 'synthetic-public-key', 'NEXT_PUBLIC_ENABLE_LIVE_OTP': 'true',
               'PARENTPLUS_ENABLE_PARENT_CHILD_LIST': 'true', 'PARENTPLUS_ENABLE_CHILD_CREATION': 'true'}
        config = (ROOT/'apps/web/playwright.enabled.config.mjs').as_uri()
        result = subprocess.run(['node', '--input-type=module', '-e', 'await import(process.argv[1])', config], env=env, capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('isolated synthetic provider', result.stderr)

    def test_synthetic_provider_rejects_nonlocal_configuration(self):
        env = {'PATH': os.environ.get('PATH', ''), 'PARENTPLUS_SYNTHETIC_BROWSER': '1',
               'NEXT_PUBLIC_SUPABASE_URL': 'https://example.invalid', 'NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY': 'synthetic-public-key'}
        result = subprocess.run(['node', str(ROOT/'apps/web/e2e-enabled/fake-supabase.mjs')], env=env, capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Synthetic provider configuration required', result.stderr)

    def test_frontend_requires_enabled_browser_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            plan = {'version': 1, 'commit': 'a'*40, 'selected': {'quality': [], 'frontend': []},
                    'expected': {'frontend': ['apps/web/src/a.test.ts::A > works']}}
            (directory/'vitest-junit.xml').write_text('<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0"><testcase classname="src/a.test.ts" name="A &gt; works" time="0.1"/></testsuite></testsuites>')
            self.write_browser_fixture(directory)
            enabled = directory/'playwright-enabled-junit.xml'
            if enabled.exists(): enabled.unlink()
            self.write_receipt_fixture(directory, plan)
            with self.assertRaises(gate.GateError):
                gate.verify_evidence(plan, directory, {'quality': 'success', 'frontend': 'success'}, 'a'*40)

    def test_frontend_evidence_identity_normalization(self):
        with tempfile.TemporaryDirectory() as d:
            plan = {'version':1,'commit':'a'*40,'selected':{'quality':[], 'frontend':[]},
                    'expected':{'frontend':['apps/web/src/a.test.ts::A > works']}}
            Path(d, 'vitest-junit.xml').write_text('<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0"><testcase classname="src/a.test.ts" name="A &gt; works" time="0.1"/></testsuite></testsuites>')
            self.write_browser_fixture(Path(d))
            self.write_receipt_fixture(Path(d), plan)
            gate.verify_evidence(plan, Path(d), {'quality':'success','frontend':'success'}, 'a'*40)


if __name__ == '__main__':
    unittest.main()
