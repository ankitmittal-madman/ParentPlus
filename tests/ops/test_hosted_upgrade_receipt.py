"""Offline regression: clean-checkout audit receipt, no hosted requests/writes."""
import contextlib
import io
import json
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
class Response(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self,*args): self.close()
class UpgradeReceiptTests(unittest.TestCase):
    def test_clean_checkout_creates_receipt_directory_before_hosted_operations(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            script=root/'scripts/deploy/upgrade-testing-backend.py';script.parent.mkdir(parents=True)
            shutil.copy2(ROOT/'scripts/deploy/upgrade-testing-backend.py',script)
            shutil.copytree(ROOT/'supabase/migrations',root/'supabase/migrations')
            versions=[p.name.split('_',1)[0] for p in sorted((root/'supabase/migrations').glob('*.sql'))]
            def fake_request(request,**kwargs):
                sql=json.loads(request.data)['query']
                if 'select version' in sql: result=[{'version':v} for v in versions]
                elif 'column_name' in sql: result=[{'table_name':t,'columns':['id']} for t in ['profiles','workspaces','workspace_memberships','children','guardianships','connection_requests','workspace_children','connection_events']]
                elif 'fingerprint' in sql:
                    import re
                    tables=re.findall(r'FROM public\."([a-z_]+)"',sql)
                    result=[{'table_name':t,'records':1,'fingerprint':'unchanged'} for t in tables+['auth_users']]
                else: result=[]
                return Response(json.dumps(result).encode())
            with patch('urllib.request.urlopen',side_effect=fake_request),patch.dict('os.environ',{'SUPABASE_ACCESS_TOKEN':'offline-test-token'}),patch('sys.argv',[str(script),'--execute']),contextlib.redirect_stdout(io.StringIO()):
                runpy.run_path(str(script),run_name='__main__')
            report=(root/'work/hosted-testing-upgrade-report.json').read_text()
            self.assertEqual(json.loads(report)['status'],'passed')
            self.assertNotIn('offline-test-token',report)
if __name__=='__main__':unittest.main()
