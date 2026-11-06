"""Exercise an in-flight 041 writer across the 042 cutover in disposable PostgreSQL."""

import json
import subprocess
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTAINER = 'parentplus-workspace-cutover-ci'
ACTOR = '11111111-1111-4111-8111-111111111111'
KEY = '99999999-aaaa-4aaa-8aaa-999999999999'


def docker(*args, check=True, input_text=None):
    return subprocess.run(['docker', *args], text=True, input=input_text, capture_output=True, check=check, timeout=60)


def sql(query):
    return docker('exec', '-i', CONTAINER, 'psql', '-X', '-A', '-t', '-q', '-v', 'ON_ERROR_STOP=1',
                  '-U', 'parentplus_test', '-d', 'parentplus_test', input_text=query).stdout.strip()


def session():
    return subprocess.Popen(['docker', 'exec', '-i', CONTAINER, 'psql', '-X', '-A', '-t', '-q',
                             '-v', 'ON_ERROR_STOP=1', '-U', 'parentplus_test', '-d', 'parentplus_test'],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def wait_for(query, seconds=15):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if sql(query) == 't':
            return True
        time.sleep(0.1)
    return False


class WorkspaceCutoverRaceTests(unittest.TestCase):
    def test_legacy_call_paused_before_insert_is_recorded_after_cutover(self):
        created = False
        volumes = []
        locker = writer = None
        if docker('container', 'inspect', CONTAINER, check=False).returncode == 0:
            self.fail('STOP: cutover test container already exists')
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
                self.fail('STOP: cutover database was not ready')
            self.assertEqual(docker('inspect', CONTAINER, '--format', '{{.HostConfig.NetworkMode}}').stdout.strip(), 'none')
            self.assertEqual(docker('port', CONTAINER).stdout.strip(), '')
            sql((ROOT / 'tests/database/supabase_auth_fixture.sql').read_text())
            cutoff = '20261106004200_workspace_creation_receipts.sql'
            migrations = sorted(p for p in (ROOT / 'supabase/migrations').glob('*.sql') if p.name < cutoff)
            self.assertEqual(len(migrations), 41)
            for path in migrations:
                sql(path.read_text())
            # Synthetic session-only barrier pauses the old function before it touches workspaces.
            sql("""CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid LANGUAGE plpgsql AS $$
BEGIN
 IF current_setting('parentplus.test_pause',true)='yes' THEN
   PERFORM pg_advisory_xact_lock(989898);
 END IF;
 RETURN nullif(current_setting('request.jwt.claim.sub',true),'')::uuid;
END $$;""")
            locker, writer = session(), session()
            locker.stdin.write("BEGIN; SET application_name='pp_cutover_locker'; SELECT pg_advisory_xact_lock(989898);\n")
            locker.stdin.flush()
            self.assertTrue(wait_for("SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE application_name='pp_cutover_locker' AND state='idle in transaction');"))
            writer.stdin.write(f"BEGIN; SET application_name='pp_cutover_late_writer'; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{ACTOR}',true); SELECT set_config('parentplus.test_pause','yes',true); SELECT public.create_workspace('Late Academy','academy','{KEY}'); COMMIT;\n\\q\n")
            writer.stdin.flush()
            self.assertTrue(wait_for("SELECT EXISTS(SELECT 1 FROM pg_stat_activity a JOIN pg_stat_activity b ON b.pid = ANY(pg_blocking_pids(a.pid)) WHERE a.application_name='pp_cutover_late_writer' AND b.application_name='pp_cutover_locker');"))
            sql((ROOT / 'supabase/migrations' / cutoff).read_text())
            locker.stdin.write('COMMIT;\n\\q\n')
            locker.stdin.flush()
            locker.stdin.close()
            locker.stdin = None
            _, errors = locker.communicate(timeout=20)
            self.assertEqual(locker.returncode, 0, errors)
            writer.stdin.close()
            writer.stdin = None
            _, errors = writer.communicate(timeout=20)
            self.assertEqual(writer.returncode, 0, errors)
            self.assertEqual(sql(f"SELECT count(*) FROM public.workspace_creation_receipts WHERE actor_id='{ACTOR}' AND request_key='{KEY}' AND original_name IS NULL;"), '1')
            original_id = sql(f"SELECT workspace_id FROM public.workspace_creation_receipts WHERE actor_id='{ACTOR}' AND request_key='{KEY}';")
            sql(f"DELETE FROM public.workspace_memberships WHERE workspace_id IN (SELECT id FROM public.workspaces WHERE created_by='{ACTOR}' AND creation_request_id='{KEY}'); DELETE FROM public.workspaces WHERE created_by='{ACTOR}' AND creation_request_id='{KEY}';")
            conflict = docker('exec', '-i', CONTAINER, 'psql', '-X', '-q', '-v', 'ON_ERROR_STOP=1', '-U', 'parentplus_test', '-d', 'parentplus_test', check=False, input_text=f"INSERT INTO public.workspaces(id,name,type,created_by,creation_request_id) VALUES ('{original_id}','Late Academy','academy','{ACTOR}','{KEY}');")
            self.assertNotEqual(conflict.returncode, 0)
            self.assertIn('Workspace creation recovery unavailable', conflict.stderr)
            result = docker('exec', '-i', CONTAINER, 'psql', '-X', '-q', '-v', 'ON_ERROR_STOP=1', '-U', 'parentplus_test', '-d', 'parentplus_test', check=False, input_text=f"BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{ACTOR}',true); SELECT public.create_workspace('Late Academy','academy','{KEY}'); COMMIT;")
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(sql(f"SELECT count(*) FROM public.workspaces WHERE created_by='{ACTOR}' AND creation_request_id='{KEY}';"), '0')
        finally:
            for process in (writer, locker):
                if process and process.poll() is None:
                    process.kill()
                    process.communicate(timeout=10)
            if created:
                docker('rm', '-f', '-v', CONTAINER)
                for volume in volumes:
                    self.assertNotEqual(docker('volume', 'inspect', volume, check=False).returncode, 0)

    def test_preexisting_uncommitted_writer_is_drained_before_backfill(self):
        created = False
        volumes = []
        writer = migration = None
        if docker('container', 'inspect', CONTAINER, check=False).returncode == 0:
            self.fail('STOP: cutover test container already exists')
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
                self.fail('STOP: cutover database was not ready')
            self.assertEqual(docker('inspect', CONTAINER, '--format', '{{.HostConfig.NetworkMode}}').stdout.strip(), 'none')
            self.assertEqual(docker('port', CONTAINER).stdout.strip(), '')
            sql((ROOT / 'tests/database/supabase_auth_fixture.sql').read_text())
            cutoff = '20261106004200_workspace_creation_receipts.sql'
            migrations = sorted(p for p in (ROOT / 'supabase/migrations').glob('*.sql') if p.name < cutoff)
            self.assertEqual(len(migrations), 41)
            for path in migrations:
                sql(path.read_text())
            writer = session()
            writer.stdin.write(f"BEGIN; SET application_name='pp_cutover_writer'; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{ACTOR}',true); SELECT public.create_workspace('Race Academy','academy','{KEY}'); SELECT 'writer_ready';\n")
            writer.stdin.flush()
            self.assertTrue(wait_for("SELECT EXISTS(SELECT 1 FROM pg_stat_activity WHERE application_name='pp_cutover_writer' AND state='idle in transaction');"))
            migration = session()
            migration.stdin.write("SET application_name='pp_cutover_migration';\n" + (ROOT / 'supabase/migrations' / cutoff).read_text() + "\nSELECT 'migration_done';\n")
            migration.stdin.flush()
            self.assertTrue(wait_for("SELECT EXISTS(SELECT 1 FROM pg_stat_activity a JOIN pg_stat_activity b ON b.pid = ANY(pg_blocking_pids(a.pid)) WHERE a.application_name='pp_cutover_migration' AND b.application_name='pp_cutover_writer');", seconds=5), 'migration did not wait for the in-flight legacy writer')
            writer.stdin.write('COMMIT;\n\\q\n')
            writer.stdin.flush()
            writer.stdin.close()
            writer.stdin = None
            _, errors = writer.communicate(timeout=20)
            self.assertEqual(writer.returncode, 0, errors)
            migration.stdin.write('\\q\n')
            migration.stdin.flush()
            migration.stdin.close()
            migration.stdin = None
            _, errors = migration.communicate(timeout=20)
            self.assertEqual(migration.returncode, 0, errors)
            self.assertEqual(sql(f"SELECT count(*) FROM public.workspace_creation_receipts WHERE actor_id='{ACTOR}' AND request_key='{KEY}' AND original_name IS NULL;"), '1')
            sql(f"DELETE FROM public.workspace_memberships WHERE workspace_id IN (SELECT id FROM public.workspaces WHERE created_by='{ACTOR}' AND creation_request_id='{KEY}'); DELETE FROM public.workspaces WHERE created_by='{ACTOR}' AND creation_request_id='{KEY}';")
            result = docker('exec', '-i', CONTAINER, 'psql', '-X', '-q', '-v', 'ON_ERROR_STOP=1', '-U', 'parentplus_test', '-d', 'parentplus_test', check=False, input_text=f"BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{ACTOR}',true); SELECT public.create_workspace('Race Academy','academy','{KEY}'); COMMIT;")
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(sql(f"SELECT count(*) FROM public.workspaces WHERE created_by='{ACTOR}' AND creation_request_id='{KEY}';"), '0')
        finally:
            for process in (migration, writer):
                if process and process.poll() is None:
                    process.kill()
                    process.communicate(timeout=10)
            if created:
                docker('rm', '-f', '-v', CONTAINER)
                for volume in volumes:
                    self.assertNotEqual(docker('volume', 'inspect', volume, check=False).returncode, 0)
