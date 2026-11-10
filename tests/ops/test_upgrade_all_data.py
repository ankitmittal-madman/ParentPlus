"""Offline tests: later-feature user records must be included in upgrade preservation."""
import contextlib
import io
import json
from pathlib import Path
import re
import runpy
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
BASE=['profiles','workspaces','workspace_memberships','children','guardianships','connection_requests','workspace_children','connection_events']
TABLES=BASE+['courses','family_invites','batch_coach_assignments']
class Response(io.BytesIO):
    def __enter__(self):return self
    def __exit__(self,*args):self.close()

class AllDataUpgradeTests(unittest.TestCase):
    def exercise(self, changed=False, inspect=False, metadata_columns=None):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);script=root/'scripts/deploy/upgrade-testing-backend.py';script.parent.mkdir(parents=True)
            shutil.copy2(ROOT/'scripts/deploy/upgrade-testing-backend.py',script)
            shutil.copytree(ROOT/'supabase/migrations',root/'supabase/migrations')
            versions=[p.name.split('_',1)[0] for p in sorted((root/'supabase/migrations').glob('*.sql'))]
            snapshots=0
            def fake(request,**kwargs):
                nonlocal snapshots
                sql=json.loads(request.data)['query']
                if inspect:self.assertTrue(sql.lstrip().lower().startswith('select '))
                if 'select version' in sql:result=[{'version':v} for v in versions]
                elif 'GROUP BY' in sql and 'column_name' in sql:
                    result=[]
                    for table in TABLES:
                        fields=['workspace_id','batch_id','membership_id'] if table=='batch_coach_assignments' else ['id']
                        # Management API encodes PostgreSQL arrays as strings;
                        # only a JSON aggregate yields a native JSON list.
                        if inspect and not re.search(r'jsonb_agg\(c\.column_name ORDER BY c\.ordinal_position\)',sql):
                            fields='{'+','.join(fields)+'}'
                        if metadata_columns is not None:fields=metadata_columns
                        result.append({'table_name':table,'columns':fields})
                elif 'column_name' in sql:result=[{'column_name':'id'}]
                elif 'fingerprint' in sql:
                    names=re.findall(r'from public\."([a-z_]+)"',sql,re.I)
                    if len(names)>1:
                        snapshots+=1
                        self.assertNotIn('order by t.id',sql.lower())
                        result=[{'table_name':n,'records':1,'fingerprint':'changed' if changed and snapshots==2 and n=='courses' else 'unchanged'} for n in names]
                        if 'from auth.users' in sql.lower():result.append({'table_name':'auth_users','records':1,'fingerprint':'unchanged'})
                    else:result=[{'records':1,'fingerprint':'unchanged'}]
                else:result=[]
                return Response(json.dumps(result).encode())
            output=io.StringIO()
            with patch('urllib.request.urlopen',side_effect=fake),patch.dict('os.environ',{'SUPABASE_ACCESS_TOKEN':'offline-only'}),patch('sys.argv',[str(script)]+([] if inspect else ['--execute'])),contextlib.redirect_stdout(output):
                if changed:
                    with self.assertRaisesRegex(RuntimeError,'fingerprints changed'):runpy.run_path(str(script),run_name='__main__')
                else:runpy.run_path(str(script),run_name='__main__')
            if inspect:
                self.assertEqual(snapshots,1)
                self.assertFalse((root/'work/hosted-testing-upgrade-report.json').exists())
                return output.getvalue()
            report=json.loads((root/'work/hosted-testing-upgrade-report.json').read_text())
            self.assertTrue(set(TABLES).issubset(report['baseline_records']))
            return report
    def test_snapshots_include_classes_invites_and_composite_key_tables(self):
        self.assertEqual(self.exercise()['status'],'passed')
    def test_changed_existing_class_data_stops_the_upgrade(self):
        self.exercise(changed=True)
    def test_inspect_uses_native_json_columns_from_management_api(self):
        try:output=self.exercise(inspect=True)
        except SystemExit as error:self.fail(f'JSON metadata inspection stopped: {error}')
        self.assertIn('Inspection only:',output)
    def test_inspect_rejects_non_list_or_non_string_columns(self):
        for fields in ('{id}','["id"]',{'id':'id'},[],[['id']],[1],['id','id']):
            with self.subTest(fields=fields),self.assertRaisesRegex(SystemExit,'unexpected pre-upgrade table metadata'):
                try:self.exercise(inspect=True,metadata_columns=fields)
                except (TypeError,ValueError) as error:self.fail(f'Malformed columns bypassed metadata validation: {error}')
