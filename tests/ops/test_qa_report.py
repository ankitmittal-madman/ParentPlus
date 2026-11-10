import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
import zipfile
import xml.etree.ElementTree as ET
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


class BrowserReportTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('qa_report', ROOT / 'scripts/qa/report.py')
        self.report = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.report)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        (self.out/'outcome.png').write_bytes(b'\x89PNG\r\n\x1a\nfixture')
        self.catalog = {'projects': ['desktop'], 'scenarios': [{'id': 'AUTH-001', 'feature': 'Login', 'persona': 'Parent', 'title': '<script>bad()</script>', 'preconditions': 'Synthetic local account', 'steps': ['Click Continue'], 'expected': '=1+1', 'status': 'automated', 'kind': 'real local backend'}], 'actions': [], 'gaps': []}
        self.payload = {'suites': [{'specs': [{'title': '[AUTH-001] Login', 'tests': [{'projectName': 'desktop', 'expectedStatus': 'passed', 'results': [{'status': 'passed', 'duration': 10, 'attachments': [{'name': 'outcome', 'path': str(self.out/'outcome.png')}]}]}]}]}]}

    def write(self, payload=None):
        return self.report.write_report(self.catalog, self.payload if payload is None else payload, self.out, {'projects': ['desktop'], 'commit': 'fixture', 'environment': 'synthetic unit fixture'}, [])

    def test_failed_invitation_navigation_redacts_secret_in_all_shareable_reports(self):
        secret='bc'*32
        result=self.payload['suites'][0]['specs'][0]['tests'][0]['results'][0]
        result['status']='failed'
        result['errors']=[{'message':'Navigation failed: http://127.0.0.1:3193/join#'+secret}]
        summary=self.write()
        self.assertFalse(summary['ok'])
        for name in ['index.html','summary.json']:
            self.assertNotIn(secret,(self.out/name).read_text())
        with zipfile.ZipFile(self.out/'ParentPlus-Test-Scenarios.xlsx') as book:
            self.assertNotIn(secret,b''.join(book.read(n) for n in book.namelist()).decode())
        self.assertNotIn(secret,self.report.redact('goto join#'+secret+' failed'))

    def test_generates_escaped_self_contained_html_and_real_inline_string_xlsx(self):
        summary = self.write()
        self.assertTrue(summary['ok'])
        html = (self.out/'index.html').read_text()
        self.assertNotIn('<script>bad()', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('data:image/png;base64,', html)
        with zipfile.ZipFile(self.out/'ParentPlus-Test-Scenarios.xlsx') as z:
            for name in z.namelist():
                if name.endswith('.xml'): ET.fromstring(z.read(name))
            self.assertIn(b'=1+1', z.read('xl/worksheets/sheet2.xml'))
            self.assertNotIn(b'<f>', z.read('xl/worksheets/sheet2.xml'))

    def test_zero_scenarios_and_mismatched_projects_never_pass(self):
        self.catalog['scenarios']=[]
        self.assertFalse(self.write({'suites':[]})['ok'])
        self.setUp()
        result=self.report.write_report(self.catalog,self.payload,self.out,{'projects':['desktop','mobile']},[])
        self.assertFalse(result['ok'])

    def test_missing_results_and_missing_project_cannot_pass(self):
        self.assertFalse(self.write({'suites': []})['ok'])
        self.assertIn('NOT RUN', (self.out/'index.html').read_text())

    def test_skipped_and_flaky_results_cannot_pass(self):
        case = self.payload['suites'][0]['specs'][0]['tests'][0]
        case['results'][0]['status'] = 'skipped'
        self.assertFalse(self.write()['ok'])
        case['results'] = [{'status': 'failed'}, {'status': 'passed', 'attachments': [{'name': 'outcome', 'path': str(self.out/'outcome.png')}]}]
        self.assertFalse(self.write()['ok'])

    def test_missing_or_external_screenshot_cannot_pass_or_exfiltrate(self):
        att = self.payload['suites'][0]['specs'][0]['tests'][0]['results'][0]['attachments'][0]
        att['path'] = '/etc/hostname'
        self.assertFalse(self.write()['ok'])
        self.assertNotIn(Path('/etc/hostname').read_text().strip(), (self.out/'index.html').read_text())

    def test_duplicate_and_unknown_scenarios_cannot_pass(self):
        specs = self.payload['suites'][0]['specs']
        specs.append(json.loads(json.dumps(specs[0])))
        self.assertFalse(self.write()['ok'])
        specs.pop(); specs[0]['title'] = '[AUTH-999] unexpected'
        self.assertFalse(self.write()['ok'])

    def test_future_feature_is_not_built_and_never_in_pass_total(self):
        self.catalog['gaps'] = [{'feature': 'Attendance', 'status': 'not built', 'next': 'Implement enrolled-child attendance'}]
        summary = self.write()
        self.assertEqual(summary['passed'], 1)
        self.assertEqual(summary['not_built'], 1)
        self.assertIn('not built', (self.out/'index.html').read_text())

    def test_all_founder_features_are_planning_inventory_separate_from_runtime_totals(self):
        summary=self.write()
        self.assertEqual(summary['founder_features'],58)
        self.assertEqual(summary['passed'],1)
        self.assertEqual(summary['expected'],1)
        html=(self.out/'index.html').read_text()
        self.assertIn('Planning status is not a browser test result',html)
        self.assertIn('M2-58',html)
        with zipfile.ZipFile(self.out/'ParentPlus-Test-Scenarios.xlsx') as book:
            self.assertIn(b'Founder feature inventory',book.read('xl/workbook.xml'))
            self.assertIn(b'M2-58',book.read('xl/worksheets/sheet7.xml'))

    def test_missing_duplicate_and_malformed_founder_rows_are_rejected(self):
        source=(ROOT/'docs/BUILD_PROGRESS.md').read_text()
        rows=self.report.founder_features(source)
        self.assertEqual(len(rows),58)
        line=next(line for line in source.splitlines() if line.startswith('| M2-58 |'))
        for broken in (source.replace(line,''),source+'\n'+line,source.replace(line,line.replace(' | P0 |',' | INVALID |')),source.replace(line,'| M2-58 | broken |')):
            with self.subTest(broken=broken[-40:]),self.assertRaisesRegex(ValueError,'Founder feature inventory'):
                self.report.founder_features(broken)

    def test_invalid_founder_inventory_keeps_reports_but_cannot_pass(self):
        with patch.object(self.report,'founder_features',side_effect=ValueError('bad fixture')):
            summary=self.write()
        self.assertFalse(summary['ok'])
        self.assertEqual(summary['passed'],1)
        self.assertEqual(summary['founder_features'],0)
        self.assertTrue((self.out/'ParentPlus-Test-Scenarios.xlsx').is_file())
        self.assertIn('Founder feature inventory is missing or malformed',(self.out/'index.html').read_text())

    def test_observed_control_is_not_counted_as_exercised(self):
        self.catalog['actions']=[{'route':'/login','name':'Continue','scenarios':['AUTH-001']}]
        p=self.out/'actions.json'
        p.write_text(json.dumps([{'route':'/login','name':'Continue','kind':'observed'}]))
        self.payload['suites'][0]['specs'][0]['tests'][0]['results'][0]['attachments'].append({'name':'ui-actions','path':str(p)})
        incomplete=self.write()
        self.assertEqual(incomplete['action_gaps'],1)
        self.assertFalse(incomplete['ok'])
        p.write_text(json.dumps([{'route':'/login','name':'Continue','kind':'clicked'}]))
        self.assertEqual(self.write()['action_gaps'],0)

    def test_a_desktop_pass_does_not_cover_a_missing_mobile_run(self):
        result=self.report.write_report(self.catalog,self.payload,self.out,{'projects':['desktop','mobile']},[])
        self.assertFalse(result['ok'])
        self.assertEqual(result['passed'],1)
        self.assertEqual(result['not_run'],1)

    def test_a_new_observed_control_without_mapping_fails_action_coverage(self):
        p=self.out/'new-action.json'
        p.write_text(json.dumps([{'route':'/login','name':'New untested action','kind':'observed'}]))
        self.payload['suites'][0]['specs'][0]['tests'][0]['results'][0]['attachments'].append({'name':'ui-actions','path':str(p)})
        result=self.write()
        self.assertFalse(result['ok'])
        self.assertEqual(result['action_gaps'],1)
        self.assertIn('UNMAPPED CONTROL',(self.out/'index.html').read_text())

    def test_interrupted_json_still_produces_failed_html_and_excel(self):
        (self.out/'run-metadata.json').write_text(json.dumps({'projects':['desktop','mobile']}))
        (self.out/'playwright.json').write_text('{incomplete')
        result=subprocess.run([sys.executable,str(ROOT/'scripts/qa/report.py'),'--out',str(self.out)],capture_output=True,text=True)
        self.assertEqual(result.returncode,1)
        self.assertTrue((self.out/'ParentPlus-Test-Scenarios.xlsx').is_file())
        self.assertIn('NOT RUN',(self.out/'index.html').read_text())


if __name__ == '__main__':
    unittest.main()
