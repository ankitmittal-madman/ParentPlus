"""Real 041-to-042 migration test in a separate, disposable PostgreSQL container."""

import json
import subprocess
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTAINER = 'parentplus-workspace-upgrade-ci'
USER = 'parentplus_test'
DB = 'parentplus_test'
ACTOR = '11111111-1111-4111-8111-111111111111'
OLD_KEY = '11111111-aaaa-4aaa-8aaa-111111111111'
NEW_KEY = '22222222-aaaa-4aaa-8aaa-222222222222'
UPGRADE = ROOT / 'supabase/migrations/20261106004200_workspace_creation_receipts.sql'


def docker(*args, input_text=None, check=True):
    return subprocess.run(['docker', *args], input=input_text, text=True, capture_output=True, check=check, timeout=60)


def sql(text):
    return docker('exec', '-i', CONTAINER, 'psql', '-X', '-A', '-t', '-q', '-v', 'ON_ERROR_STOP=1',
                  '-U', USER, '-d', DB, input_text=text).stdout.strip()


class WorkspaceReceiptUpgradeTests(unittest.TestCase):
    def test_existing_renamed_workspace_is_preserved_and_legacy_retry_fails_closed(self):
        created = False
        created_volumes = []
        stage = 'container_precheck'
        try:
            if docker('container', 'inspect', CONTAINER, check=False).returncode == 0:
                self.fail('STOP: upgrade test container already exists')
            stage = 'container_start'
            docker('run', '-d', '--pull=never', '--name', CONTAINER, '--network', 'none', '--tmpfs', '/var/lib/postgresql',
                   '--tmpfs', '/tmp', '-e', 'POSTGRES_USER=parentplus_test', '-e', 'POSTGRES_DB=parentplus_test',
                   '-e', 'POSTGRES_PASSWORD=parentplus_local_only', '-e', 'PGDATA=/var/lib/postgresql/pgdata', 'postgres:17')
            created = True
            mounts = json.loads(docker('inspect', CONTAINER, '--format', '{{json .Mounts}}').stdout)
            created_volumes = [mount['Name'] for mount in mounts if mount['Type'] == 'volume']
            stage = 'container_ready'
            for _ in range(100):
                # The image starts a temporary socket-only server during initialization.
                # Wait for the final server's loopback listener before loading fixtures.
                if docker('exec', CONTAINER, 'pg_isready', '-h', '127.0.0.1', '-U', USER, '-d', DB, check=False).returncode == 0:
                    break
                time.sleep(0.2)
            else:
                self.fail('STOP: disposable upgrade database did not become ready')
            self.assertEqual(docker('inspect', CONTAINER, '--format', '{{.HostConfig.NetworkMode}}').stdout.strip(), 'none')
            self.assertEqual(docker('port', CONTAINER).stdout.strip(), '')
            stage = 'migration_inventory'
            migrations = sorted((ROOT / 'supabase/migrations').glob('*.sql'))
            self.assertEqual(len(migrations), 42)
            self.assertEqual(migrations[-1], UPGRADE)
            stage = 'auth_fixture'
            sql((ROOT / 'tests/database/supabase_auth_fixture.sql').read_text())
            stage = 'old_migrations'
            for migration in migrations[:-1]:
                sql(migration.read_text())
            stage = 'legacy_creation'
            legacy_id = sql(f"""
BEGIN; SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub','{ACTOR}',true);
SELECT 'LEGACY:' || public.create_workspace('Original Academy','academy','{OLD_KEY}')::text;
COMMIT;
""").split('LEGACY:')[-1].strip()
            self.assertRegex(legacy_id, r'^[0-9a-f-]{36}$')
            stage = 'legacy_rename'
            sql(f"UPDATE public.workspaces SET name='Renamed Academy' WHERE id='{legacy_id}';")
            stage = 'upgrade_migration'
            sql(UPGRADE.read_text())
            stage = 'legacy_state'
            self.assertEqual(sql(f"""
SELECT w.name, m.role, m.status, (r.original_name IS NULL), (r.original_type IS NULL)
FROM public.workspaces w JOIN public.workspace_memberships m ON m.workspace_id=w.id
JOIN public.workspace_creation_receipts r ON r.workspace_id=w.id
WHERE w.id='{legacy_id}' AND m.user_id='{ACTOR}' AND r.actor_id='{ACTOR}' AND r.request_key='{OLD_KEY}';
"""), 'Renamed Academy|owner|active|t|t')
            stage = 'legacy_retry'
            for supplied_name in ('Original Academy', 'Renamed Academy'):
                result = docker('exec', '-i', CONTAINER, 'psql', '-X', '-A', '-t', '-q', '-v', 'ON_ERROR_STOP=1',
                                '-U', USER, '-d', DB, input_text=f"""
BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{ACTOR}',true);
SELECT public.create_workspace('{supplied_name}','academy','{OLD_KEY}'); COMMIT;
""", check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Workspace creation recovery unavailable', result.stderr)
            self.assertEqual(sql(f"SELECT count(*) FROM public.workspaces WHERE created_by='{ACTOR}' AND creation_request_id='{OLD_KEY}';"), '1')
            stage = 'new_retry'
            result = sql(f"""
BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{ACTOR}',true);
SELECT public.create_workspace('New Academy','academy','{NEW_KEY}') = public.create_workspace('New Academy','academy','{NEW_KEY}');
COMMIT;
""")
            self.assertEqual(result.splitlines()[-1], 't')
        except Exception as error:
            raise AssertionError(f'UPGRADE_DIAG:{stage}:{type(error).__name__}') from error
        finally:
            if created:
                try:
                    docker('rm', '-f', '-v', CONTAINER)
                    for volume in created_volumes:
                        self.assertNotEqual(docker('volume', 'inspect', volume, check=False).returncode, 0,
                                            'Disposable upgrade volume was not removed')
                except Exception as error:
                    raise AssertionError(f'UPGRADE_DIAG:cleanup:{type(error).__name__}') from error
