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
CONTROLS=['parent_child_read_controls','child_creation_controls','class_setup_controls','workspace_creation_controls']
class Response(io.BytesIO):
    def __enter__(self):return self
    def __exit__(self,*args):self.close()

class AllDataUpgradeTests(unittest.TestCase):
    def exercise(self, changed=False, inspect=False, metadata_columns=None, controls=False, corrupt_after_activation=False, gap_change_table=None):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);script=root/'scripts/deploy/upgrade-testing-backend.py';script.parent.mkdir(parents=True)
            shutil.copy2(ROOT/'scripts/deploy/upgrade-testing-backend.py',script)
            shutil.copytree(ROOT/'supabase/migrations',root/'supabase/migrations')
            versions=[p.name.split('_',1)[0] for p in sorted((root/'supabase/migrations').glob('*.sql'))]
            snapshots=0
            controls_enabled=False
            gap_write=False
            def fake(request,**kwargs):
                nonlocal snapshots,controls_enabled,gap_write
                sql=json.loads(request.data)['query']
                if inspect:self.assertTrue(sql.lstrip().lower().startswith('select '))
                if 'select version' in sql:result=[{'version':v} for v in versions]
                elif 'GROUP BY' in sql and 'column_name' in sql:
                    result=[]
                    for table in TABLES+(CONTROLS if controls else []):
                        fields=['id','enabled','updated_at'] if table in CONTROLS else ['workspace_id','batch_id','membership_id'] if table=='batch_coach_assignments' else ['id']
                        # Management API encodes PostgreSQL arrays as strings;
                        # only a JSON aggregate yields a native JSON list.
                        if inspect and not re.search(r'jsonb_agg\(c\.column_name ORDER BY c\.ordinal_position\)',sql):
                            fields='{'+','.join(fields)+'}'
                        if metadata_columns is not None:fields=metadata_columns
                        result.append({'table_name':table,'columns':fields})
                elif 'bool_and(enabled)' in sql:
                    # A concurrent write after the migration preservation check,
                    # before activation, must never become the new expectation.
                    gap_write=bool(gap_change_table)
                    result=[{'table_name':t,'records':1,'enabled':controls_enabled} for t in CONTROLS]
                elif 'update public.parent_child_read_controls set enabled=true' in sql.lower():
                    controls_enabled=True
                    result=[]
                elif 'column_name' in sql:result=[{'column_name':'id'}]
                elif 'fingerprint' in sql:
                    names=re.findall(r'from public\."([a-z_]+)"',sql,re.I)
                    if len(names)>1:
                        snapshots+=1
                        self.assertNotIn('order by t.id',sql.lower())
                        result=[]
                        for n in names:
                            fingerprint='unchanged'
                            if n in CONTROLS:fingerprint='controls-on' if controls_enabled or "'enabled',true" in sql and 'enabled_fingerprint' not in sql else 'controls-off'
                            elif n=='courses' and (changed and snapshots==2 or corrupt_after_activation and controls_enabled):fingerprint='changed'
                            if gap_write and n==gap_change_table:fingerprint+='-other-column-changed'
                            row={'table_name':n,'records':1,'fingerprint':fingerprint}
                            if 'enabled_fingerprint' in sql:
                                row['enabled_fingerprint']='controls-on'+('-other-column-changed' if gap_write and n==gap_change_table else '') if n in CONTROLS else None
                            result.append(row)
                        if 'from auth.users' in sql.lower():result.append({'table_name':'auth_users','records':1,'fingerprint':'unchanged'})
                    else:result=[{'records':1,'fingerprint':'unchanged'}]
                else:result=[]
                return Response(json.dumps(result).encode())
            output=io.StringIO()
            with patch('urllib.request.urlopen',side_effect=fake),patch.dict('os.environ',{'SUPABASE_ACCESS_TOKEN':'offline-only'}),patch('sys.argv',[str(script)]+([] if inspect else ['--execute'])),contextlib.redirect_stdout(output):
                if changed or corrupt_after_activation or gap_change_table:
                    with self.assertRaisesRegex(RuntimeError,'post-activation' if corrupt_after_activation or gap_change_table else 'fingerprints changed'):runpy.run_path(str(script),run_name='__main__')
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
    def test_control_activation_is_audited_separately_from_original_records(self):
        report=self.exercise(controls=True)
        self.assertEqual(report['after_records'],report['baseline_records'])
        self.assertEqual(report['post_activation_records'],report['expected_post_activation_records'])
        changed={name for name in report['baseline_records'] if report['baseline_records'][name]!=report['post_activation_records'][name]}
        self.assertEqual(changed,set(CONTROLS))
        self.assertEqual(report['intentional_control_changes'],{name:{'before':False,'after':True} for name in CONTROLS})
        self.assertEqual(report['post_activation_preservation'],'passed')
    def test_existing_record_change_during_activation_fails_the_final_audit(self):
        report=self.exercise(controls=True,corrupt_after_activation=True)
        self.assertEqual(report['status'],'failed')
    def test_unrelated_gap_write_cannot_become_the_final_expectation(self):
        report=self.exercise(controls=True,gap_change_table='courses')
        self.assertEqual(report['after_records'],report['baseline_records'])
        self.assertEqual(report['expected_post_activation_records']['courses'],report['baseline_records']['courses'])
        self.assertEqual(report['status'],'failed')
        self.assertNotIn('post_activation_preservation',report)
    def test_control_other_column_gap_write_fails_the_final_audit(self):
        report=self.exercise(controls=True,gap_change_table=CONTROLS[0])
        self.assertEqual(report['after_records'],report['baseline_records'])
        self.assertNotEqual(report['post_activation_records'][CONTROLS[0]],report['expected_post_activation_records'][CONTROLS[0]])
        self.assertEqual(report['status'],'failed')
        self.assertNotIn('post_activation_preservation',report)
    def test_inspect_uses_native_json_columns_from_management_api(self):
        try:output=self.exercise(inspect=True)
        except SystemExit as error:self.fail(f'JSON metadata inspection stopped: {error}')
        self.assertIn('Inspection only:',output)
    def test_inspect_rejects_non_list_or_non_string_columns(self):
        for fields in ('{id}','["id"]',{'id':'id'},[],[['id']],[1],['id','id']):
            with self.subTest(fields=fields),self.assertRaisesRegex(SystemExit,'unexpected pre-upgrade table metadata'):
                try:self.exercise(inspect=True,metadata_columns=fields)
                except (TypeError,ValueError) as error:self.fail(f'Malformed columns bypassed metadata validation: {error}')
