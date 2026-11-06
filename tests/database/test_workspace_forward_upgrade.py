"""Forward repair from the original 042/043 draft, in disposable PostgreSQL."""

import json
import subprocess
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTAINER = 'parentplus-workspace-forward-ci'
ACTOR = '11111111-1111-4111-8111-111111111111'
MISSING_KEY = 'a1111111-aaaa-4aaa-8aaa-111111111111'
KNOWN_KEY = 'a2222222-aaaa-4aaa-8aaa-222222222222'


def docker(*args, input_text=None, check=True):
    return subprocess.run(['docker', *args], text=True, input=input_text, capture_output=True, check=check, timeout=60)


def sql(text):
    return docker('exec', '-i', CONTAINER, 'psql', '-X', '-A', '-t', '-q', '-v', 'ON_ERROR_STOP=1',
                  '-U', 'parentplus_test', '-d', 'parentplus_test', input_text=text).stdout.strip()


def session():
    return subprocess.Popen(['docker', 'exec', '-i', CONTAINER, 'psql', '-X', '-A', '-t', '-q',
                             '-v', 'ON_ERROR_STOP=1', '-U', 'parentplus_test', '-d', 'parentplus_test'],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def wait_for(query):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if sql(query) == 't':
            return True
        time.sleep(0.1)
    return False


class WorkspaceForwardUpgradeTests(unittest.TestCase):
    def test_old_installation_repairs_missing_surviving_receipt_without_guessing(self):
        created = False
        volumes = []
        locker = writer = guarded = migration = None
        if docker('container', 'inspect', CONTAINER, check=False).returncode == 0:
            self.fail('STOP: forward-upgrade container already exists')
        try:
            docker('run', '-d', '--pull=never', '--name', CONTAINER, '--network', 'none', '--tmpfs', '/var/lib/postgresql', '--tmpfs', '/tmp', '-e', 'POSTGRES_USER=parentplus_test', '-e', 'POSTGRES_DB=parentplus_test', '-e', 'POSTGRES_PASSWORD=parentplus_local_only', '-e', 'PGDATA=/var/lib/postgresql/pgdata', 'postgres:17')
            created = True
            mounts = json.loads(docker('inspect', CONTAINER, '--format', '{{json .Mounts}}').stdout)
            volumes = [mount['Name'] for mount in mounts if mount['Type'] == 'volume']
            for _ in range(100):
                if docker('exec', CONTAINER, 'pg_isready', '-h', '127.0.0.1', '-U', 'parentplus_test', '-d', 'parentplus_test', check=False).returncode == 0:
                    break
                time.sleep(0.2)
            else:
                self.fail('STOP: forward-upgrade database was not ready')
            self.assertEqual(docker('inspect', CONTAINER, '--format', '{{.HostConfig.NetworkMode}}').stdout.strip(), 'none')
            self.assertEqual(docker('port', CONTAINER).stdout.strip(), '')
            sql((ROOT / 'tests/database/supabase_auth_fixture.sql').read_text())
            migrations = sorted(p for p in (ROOT / 'supabase/migrations').glob('*.sql') if p.name < '20261106004200_workspace_creation_receipts.sql')
            self.assertEqual(len(migrations), 41)
            for path in migrations:
                sql(path.read_text())
            sql((ROOT / 'tests/database/fixtures/workspace_legacy_042.sql').read_text())
            sql(f"""BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{ACTOR}',true);
SELECT public.create_workspace('Missing Academy','academy','{MISSING_KEY}');
SELECT public.create_workspace('Known Academy','academy','{KNOWN_KEY}'); COMMIT;""")
            missing_id = sql(f"SELECT id FROM public.workspaces WHERE created_by='{ACTOR}' AND creation_request_id='{MISSING_KEY}';")
            known_id = sql(f"SELECT id FROM public.workspaces WHERE created_by='{ACTOR}' AND creation_request_id='{KNOWN_KEY}';")
            sql(f"DELETE FROM public.workspace_creation_receipts WHERE actor_id='{ACTOR}' AND request_key='{MISSING_KEY}';")
            sql((ROOT / 'supabase/migrations/20261106004300_workspace_creation_database_control.sql').read_text())
            forward = ROOT / 'supabase/migrations/20261106004400_workspace_creation_forward_repair.sql'
            self.assertTrue(forward.is_file(), 'Forward repair migration is missing')
            # A conflicting retained key must abort the entire migration, including disablement.
            sql(f"UPDATE public.workspace_creation_receipts SET workspace_id='{missing_id}' WHERE actor_id='{ACTOR}' AND request_key='{KNOWN_KEY}'; UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;")
            failed = docker('exec', '-i', CONTAINER, 'psql', '-X', '-q', '-v', 'ON_ERROR_STOP=1', '-U', 'parentplus_test', '-d', 'parentplus_test', input_text=forward.read_text(), check=False)
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn('Workspace creation recovery unavailable', failed.stderr)
            self.assertEqual(sql("SELECT enabled FROM public.workspace_creation_controls WHERE id=true;"), 't')
            self.assertEqual(sql(f"SELECT workspace_id FROM public.workspace_creation_receipts WHERE actor_id='{ACTOR}' AND request_key='{KNOWN_KEY}';"), missing_id)
            sql(f"UPDATE public.workspace_creation_receipts SET workspace_id='{known_id}' WHERE actor_id='{ACTOR}' AND request_key='{KNOWN_KEY}'; UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;")

            # Pause an already-running old 042 body before its insert, then repair.
            sql("""CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid LANGUAGE plpgsql AS $$
BEGIN
 IF current_setting('parentplus.test_pause',true)='yes' THEN PERFORM pg_advisory_xact_lock(797979); END IF;
 RETURN nullif(current_setting('request.jwt.claim.sub',true),'')::uuid;
END $$;""")
            locker, writer = session(), session()
            locker.stdin.write("BEGIN; SET application_name='pp_forward_locker'; SELECT pg_advisory_xact_lock(797979);\n")
            locker.stdin.flush()
            self.assertTrue(wait_for("SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE application_name='pp_forward_locker' AND state='idle in transaction');"))
            writer.stdin.write(f"BEGIN; SET application_name='pp_forward_writer'; SELECT set_config('request.jwt.claim.sub','{ACTOR}',true); SELECT set_config('parentplus.test_pause','yes',true); SELECT public.create_workspace_unguarded_private('Late Academy','academy','a3333333-aaaa-4aaa-8aaa-333333333333'); COMMIT;\n\\q\n")
            writer.stdin.flush()
            self.assertTrue(wait_for("SELECT EXISTS(SELECT 1 FROM pg_stat_activity a JOIN pg_stat_activity b ON b.pid = ANY(pg_blocking_pids(a.pid)) WHERE a.application_name='pp_forward_writer' AND b.application_name='pp_forward_locker');"))
            guarded = session()
            guarded.stdin.write(f"BEGIN; SET application_name='pp_forward_guarded'; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{ACTOR}',true); SELECT public.create_workspace('Known Academy','academy','{KNOWN_KEY}'); SELECT 'guarded_ready';\n")
            guarded.stdin.flush()
            self.assertTrue(wait_for("SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE application_name='pp_forward_guarded' AND state='idle in transaction');"))
            migration = session()
            migration.stdin.write("SET application_name='pp_forward_migration';\n" + forward.read_text() + "\n\\q\n")
            migration.stdin.flush()
            self.assertTrue(wait_for("SELECT EXISTS(SELECT 1 FROM pg_stat_activity a JOIN pg_stat_activity b ON b.pid = ANY(pg_blocking_pids(a.pid)) WHERE a.application_name='pp_forward_migration' AND b.application_name='pp_forward_guarded');"))
            guarded.stdin.write('COMMIT;\n\\q\n')
            guarded.stdin.flush()
            guarded.stdin.close()
            guarded.stdin = None
            _, errors = guarded.communicate(timeout=20)
            self.assertEqual(guarded.returncode, 0, errors)
            migration.stdin.close()
            migration.stdin = None
            _, errors = migration.communicate(timeout=20)
            self.assertEqual(migration.returncode, 0, errors)
            locker.stdin.write('COMMIT;\n\\q\n')
            locker.stdin.flush()
            locker.stdin.close()
            locker.stdin = None
            _, errors = locker.communicate(timeout=20)
            self.assertEqual(locker.returncode, 0, errors)
            writer.stdin.close()
            writer.stdin = None
            _, errors = writer.communicate(timeout=20)
            self.assertNotEqual(writer.returncode, 0)
            self.assertIn('duplicate key', errors)
            self.assertEqual(sql(f"SELECT count(*) FROM public.workspaces WHERE created_by='{ACTOR}' AND creation_request_id='a3333333-aaaa-4aaa-8aaa-333333333333';"), '0')
            self.assertEqual(sql(f"SELECT count(*) FROM public.workspace_creation_receipts WHERE actor_id='{ACTOR}' AND request_key='a3333333-aaaa-4aaa-8aaa-333333333333';"), '0')
            self.assertEqual(sql("SELECT enabled FROM public.workspace_creation_controls WHERE id=true;"), 'f')
            self.assertEqual(sql(f"SELECT workspace_id, original_name IS NULL, original_type IS NULL FROM public.workspace_creation_receipts WHERE actor_id='{ACTOR}' AND request_key='{MISSING_KEY}';"), f'{missing_id}|t|t')
            self.assertEqual(sql(f"SELECT workspace_id, original_name, original_type FROM public.workspace_creation_receipts WHERE actor_id='{ACTOR}' AND request_key='{KNOWN_KEY}';"), f'{known_id}|Known Academy|academy')
            self.assertEqual(sql(f"SELECT count(*) FROM public.workspace_memberships WHERE workspace_id IN ('{missing_id}','{known_id}') AND user_id='{ACTOR}' AND role='owner' AND status='active';"), '2')
            blocked = docker('exec', '-i', CONTAINER, 'psql', '-X', '-q', '-v', 'ON_ERROR_STOP=1', '-U', 'parentplus_test', '-d', 'parentplus_test', check=False, input_text=f"BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{ACTOR}',true); SELECT public.create_workspace('Known Academy','academy','{KNOWN_KEY}'); COMMIT;")
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn('Workspace creation unavailable', blocked.stderr)
            sql('UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;')
            result = docker('exec', '-i', CONTAINER, 'psql', '-X', '-q', '-v', 'ON_ERROR_STOP=1', '-U', 'parentplus_test', '-d', 'parentplus_test', check=False, input_text=f"BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{ACTOR}',true); SELECT public.create_workspace('Missing Academy','academy','{MISSING_KEY}'); COMMIT;")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Workspace creation recovery unavailable', result.stderr)
            self.assertEqual(sql(f"BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{ACTOR}',true); SELECT public.create_workspace('Known Academy','academy','{KNOWN_KEY}'); COMMIT;").splitlines()[-1], known_id)
            created_id = sql(f"BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{ACTOR}',true); SELECT public.create_workspace('Fresh Academy','academy','a4444444-aaaa-4aaa-8aaa-444444444444'); COMMIT;").splitlines()[-1]
            self.assertEqual(sql(f"SELECT original_name,original_type FROM public.workspace_creation_receipts WHERE workspace_id='{created_id}';"), 'Fresh Academy|academy')
            self.assertEqual(sql("SELECT has_function_privilege('authenticated','public.create_workspace_unguarded_private(text,text,uuid)','EXECUTE');"), 'f')
        finally:
            for process in (migration, guarded, writer, locker):
                if process and process.poll() is None:
                    process.kill()
                    process.communicate(timeout=10)
            if created:
                docker('rm', '-f', '-v', CONTAINER)
                for volume in volumes:
                    self.assertNotEqual(docker('volume', 'inspect', volume, check=False).returncode, 0)
