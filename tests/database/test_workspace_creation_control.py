"""Synthetic tests for the default-off workspace creation boundary."""

import unittest
import uuid

from tests.database.test_authorization import MEERA, run_sql_with_notices
from tests.database.test_concurrent_authorization import (
    close_psql_session, query, start_psql_session, wait_for_blocking_relationship,
    wait_for_session_marker,
)


class WorkspaceCreationControlTests(unittest.TestCase):
    def test_authenticated_workspace_creation_is_disabled_by_default(self):
        notice = run_sql_with_notices(f"""
BEGIN;
UPDATE public.workspace_creation_controls SET enabled=false WHERE id=true;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
DO $test$
DECLARE denied boolean := false;
BEGIN
  BEGIN
    PERFORM public.create_workspace('Test Academy','academy','a1111111-1111-4111-8111-111111111111');
  EXCEPTION WHEN insufficient_privilege THEN
    IF SQLERRM <> 'Workspace creation unavailable' THEN RAISE; END IF;
    denied := true;
  END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: default workspace creation was allowed'; END IF;
  RAISE NOTICE 'PASS: workspace creation is disabled';
END $test$;
ROLLBACK;
""")
        self.assertIn('PASS: workspace creation is disabled', notice)

    def test_missing_control_and_disabled_replay_fail_closed(self):
        notice = run_sql_with_notices(f"""
BEGIN;
UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
SELECT public.create_workspace('Replay Academy','academy','a2222222-2222-4222-8222-222222222222');
RESET ROLE;
UPDATE public.workspace_creation_controls SET enabled=false WHERE id=true;
SET LOCAL ROLE authenticated;
DO $test$ DECLARE denied boolean := false; BEGIN
  BEGIN PERFORM public.create_workspace('Replay Academy','academy','a2222222-2222-4222-8222-222222222222');
  EXCEPTION WHEN insufficient_privilege THEN denied := true; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: disabled replay allowed'; END IF;
END $test$;
RESET ROLE;
DELETE FROM public.workspace_creation_controls WHERE id=true;
SET LOCAL ROLE authenticated;
DO $test$ DECLARE denied boolean := false; BEGIN
  BEGIN PERFORM public.create_workspace('Missing Academy','academy','a3333333-3333-4333-8333-333333333333');
  EXCEPTION WHEN insufficient_privilege THEN denied := true; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: missing control allowed creation'; END IF;
END $test$;
RESET ROLE;
DO $test$ BEGIN
  IF (SELECT count(*) FROM public.workspaces) <> 1 OR
     (SELECT count(*) FROM public.workspace_memberships) <> 1 OR
     (SELECT count(*) FROM public.workspace_creation_receipts) <> 1 THEN
    RAISE EXCEPTION 'FAIL: disabled or missing control mutated records';
  END IF;
  RAISE NOTICE 'PASS: disabled and missing controls fail closed';
END $test$;
ROLLBACK;
""")
        self.assertIn('PASS: disabled and missing controls fail closed', notice)

    def test_enabled_creation_and_retry_preserve_receipt(self):
        notice = run_sql_with_notices(f"""
BEGIN;
UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
DO $test$ DECLARE first_id uuid; second_id uuid; BEGIN
  first_id := public.create_workspace('Enabled Academy','academy','a4444444-4444-4444-8444-444444444444');
  second_id := public.create_workspace('Enabled Academy','academy','a4444444-4444-4444-8444-444444444444');
  IF first_id IS NULL OR first_id <> second_id THEN RAISE EXCEPTION 'FAIL: retry changed workspace'; END IF;
  RAISE NOTICE 'PASS: enabled creation and retry';
END $test$;
ROLLBACK;
""")
        self.assertIn('PASS: enabled creation and retry', notice)

    def test_application_roles_cannot_access_control_or_private_function(self):
        notice = run_sql_with_notices("""
BEGIN;
UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;
DO $test$ DECLARE role_name text; privilege_name text; BEGIN
  IF NOT has_function_privilege('authenticated','public.create_workspace(text,text,uuid)','EXECUTE') OR
     has_function_privilege('anon','public.create_workspace(text,text,uuid)','EXECUTE') THEN
    RAISE EXCEPTION 'FAIL: wrapper privileges incorrect';
  END IF;
  FOREACH role_name IN ARRAY ARRAY['anon','authenticated'] LOOP
    FOREACH privilege_name IN ARRAY ARRAY['SELECT','INSERT','UPDATE','DELETE'] LOOP
      IF has_table_privilege(role_name,'public.workspace_creation_controls',privilege_name) THEN
        RAISE EXCEPTION 'FAIL: control accessible';
      END IF;
    END LOOP;
    IF has_function_privilege(role_name,'public.create_workspace_unguarded_private(text,text,uuid)','EXECUTE') THEN
      RAISE EXCEPTION 'FAIL: private creation accessible';
    END IF;
  END LOOP;
  RAISE NOTICE 'PASS: control and private function inaccessible';
END $test$;
SET LOCAL ROLE authenticated;
DO $test$ DECLARE denied boolean := false; BEGIN
  BEGIN PERFORM public.create_workspace_unguarded_private('Private Academy','academy','a5555555-5555-4555-8555-555555555555');
  EXCEPTION WHEN insufficient_privilege THEN denied := true; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: direct private creation allowed'; END IF;
END $test$;
ROLLBACK;
""")
        self.assertIn('PASS: control and private function inaccessible', notice)

    def exercise_disable_first(self, replay, commits):
        key = str(uuid.uuid4())
        name = 'Control Race Academy'
        if replay:
            query(f"BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT public.create_workspace('{name}','academy','{key}'); COMMIT;")
        first = second = None
        first_name, second_name = 'control_' + uuid.uuid4().hex, 'creation_' + uuid.uuid4().hex
        try:
            first, second = start_psql_session(), start_psql_session()
            first.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{first_name}',false); UPDATE public.workspace_creation_controls SET enabled=false WHERE id=true; SELECT 'DISABLE_LOCKED';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'DISABLE_LOCKED'))
            second.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{second_name}',false); SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT public.create_workspace('{name}','academy','{key}'); COMMIT; SELECT 'CREATION_DONE';\n")
            second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name, first_name))
            first.stdin.write(('COMMIT' if commits else 'ROLLBACK') + "; SELECT 'DISABLE_DONE';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'DISABLE_DONE'))
            second.stdin.close()
            second.stdin = None
            output, errors = second.communicate(timeout=15)
            if commits:
                self.assertNotEqual(second.returncode, 0)
                self.assertIn('Workspace creation unavailable', errors)
            else:
                self.assertEqual(second.returncode, 0, errors)
                self.assertIn('CREATION_DONE', output)
            self.assertEqual(query(f"SELECT count(*) FROM public.workspaces WHERE created_by='{MEERA}' AND creation_request_id='{key}';"), '1' if replay or not commits else '0')
        finally:
            for process in (second, first):
                if process is not None:
                    close_psql_session(process)
            query(f"BEGIN; UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true; DELETE FROM public.workspace_memberships WHERE workspace_id IN (SELECT id FROM public.workspaces WHERE created_by='{MEERA}' AND creation_request_id='{key}'); DELETE FROM public.workspace_creation_receipts WHERE actor_id='{MEERA}' AND request_key='{key}'; DELETE FROM public.workspaces WHERE created_by='{MEERA}' AND creation_request_id='{key}'; COMMIT;")

    def test_disable_commit_blocks_new_creation(self):
        self.exercise_disable_first(False, True)

    def test_disable_rollback_allows_new_creation(self):
        self.exercise_disable_first(False, False)

    def test_disable_commit_blocks_replay(self):
        self.exercise_disable_first(True, True)

    def test_disable_rollback_allows_replay(self):
        self.exercise_disable_first(True, False)

    def exercise_creation_first(self, replay, commits):
        key = str(uuid.uuid4())
        name = 'Control Race Academy'
        if replay:
            query(f"BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT public.create_workspace('{name}','academy','{key}'); COMMIT;")
        first = second = None
        first_name, second_name = 'creation_' + uuid.uuid4().hex, 'control_' + uuid.uuid4().hex
        try:
            first, second = start_psql_session(), start_psql_session()
            first.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{first_name}',false); SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT public.create_workspace('{name}','academy','{key}'); SELECT 'CREATION_LOCKED';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'CREATION_LOCKED'))
            second.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{second_name}',false); UPDATE public.workspace_creation_controls SET enabled=false WHERE id=true; COMMIT; SELECT 'DISABLE_DONE';\n")
            second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name, first_name))
            first.stdin.write(('COMMIT' if commits else 'ROLLBACK') + "; SELECT 'CREATION_DONE';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'CREATION_DONE'))
            second.stdin.close()
            second.stdin = None
            output, errors = second.communicate(timeout=15)
            self.assertEqual(second.returncode, 0, errors)
            self.assertIn('DISABLE_DONE', output)
            self.assertEqual(query("SELECT enabled FROM public.workspace_creation_controls WHERE id=true;"), 'f')
            self.assertEqual(query(f"SELECT count(*) FROM public.workspaces WHERE created_by='{MEERA}' AND creation_request_id='{key}';"), '1' if replay or commits else '0')
        finally:
            for process in (second, first):
                if process is not None:
                    close_psql_session(process)
            query(f"BEGIN; UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true; DELETE FROM public.workspace_memberships WHERE workspace_id IN (SELECT id FROM public.workspaces WHERE created_by='{MEERA}' AND creation_request_id='{key}'); DELETE FROM public.workspace_creation_receipts WHERE actor_id='{MEERA}' AND request_key='{key}'; DELETE FROM public.workspaces WHERE created_by='{MEERA}' AND creation_request_id='{key}'; COMMIT;")

    def test_creation_first_blocks_disable_until_commit(self):
        self.exercise_creation_first(False, True)

    def test_replay_first_blocks_disable_until_commit(self):
        self.exercise_creation_first(True, True)

    def test_creation_rollback_unblocks_disable(self):
        self.exercise_creation_first(False, False)

    def test_replay_rollback_unblocks_disable(self):
        self.exercise_creation_first(True, False)
