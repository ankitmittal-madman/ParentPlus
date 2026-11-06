"""Synthetic checks for private workspace creation recovery status."""

import unittest
import uuid

from tests.database.test_authorization import MEERA, RAHUL, run_sql, run_sql_with_notices
from tests.database.test_concurrent_authorization import (
    close_psql_session, extract_labeled_id, query, start_psql_session, wait_for_blocking_relationship, wait_for_session_marker,
)

KEY = 'f1111111-aaaa-4aaa-8aaa-111111111111'


class WorkspaceRecoveryStatusTests(unittest.TestCase):
    def test_unknown_request_returns_unknown_without_mutation(self):
        result = run_sql(f"""
BEGIN; UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;
SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
SELECT status || ':' || coalesce(workspace_id::text,'-') FROM public.workspace_creation_recovery_status('{KEY}');
SELECT (SELECT count(*) FROM public.workspaces) || ':' || (SELECT count(*) FROM public.workspace_creation_receipts);
ROLLBACK;
""")
        self.assertEqual(result.splitlines()[-2:], ['unknown:-', '0:0'])

    def test_known_request_returns_only_id_for_current_actor_after_rename(self):
        notice = run_sql_with_notices(f"""
BEGIN; UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;
CREATE TEMP TABLE ids(id uuid); GRANT SELECT, INSERT ON ids TO authenticated;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
INSERT INTO ids SELECT public.create_workspace('Original Academy','academy','{KEY}');
RESET ROLE; UPDATE public.workspaces SET name='Renamed Academy' WHERE id=(SELECT id FROM ids);
DO $test$ DECLARE item record; BEGIN
  SELECT * INTO item FROM public.workspace_creation_recovery_status('{KEY}');
  IF item.status <> 'known' OR item.workspace_id <> (SELECT id FROM ids) THEN RAISE EXCEPTION 'FAIL: incorrect known status'; END IF;
  RAISE NOTICE 'PASS: known status returns exact workspace';
END $test$;
ROLLBACK;
""")
        self.assertIn('PASS: known status returns exact workspace', notice)

    def test_other_actor_legacy_and_inactive_access_are_unknown(self):
        notice = run_sql_with_notices(f"""
BEGIN; UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;
CREATE TEMP TABLE ids(id uuid); GRANT SELECT, INSERT ON ids TO authenticated;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
INSERT INTO ids SELECT public.create_workspace('Private Academy','academy','{KEY}');
RESET ROLE; SELECT set_config('request.jwt.claim.sub','{RAHUL}',true);
DO $test$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.workspace_creation_recovery_status('{KEY}') WHERE status='unknown' AND workspace_id IS NULL) THEN RAISE EXCEPTION 'FAIL: other actor learned workspace'; END IF;
END $test$;
SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
UPDATE public.workspace_creation_receipts SET original_name=NULL,original_type=NULL WHERE actor_id='{MEERA}' AND request_key='{KEY}';
DO $test$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.workspace_creation_recovery_status('{KEY}') WHERE status='unknown' AND workspace_id IS NULL) THEN RAISE EXCEPTION 'FAIL: legacy receipt exposed'; END IF;
END $test$;
UPDATE public.workspace_creation_receipts SET original_name='Private Academy',original_type='academy' WHERE actor_id='{MEERA}' AND request_key='{KEY}';
UPDATE public.workspace_memberships SET status='suspended' WHERE workspace_id=(SELECT id FROM ids) AND user_id='{MEERA}';
DO $test$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.workspace_creation_recovery_status('{KEY}') WHERE status='unknown' AND workspace_id IS NULL) THEN RAISE EXCEPTION 'FAIL: suspended membership exposed'; END IF;
END $test$;
UPDATE public.workspace_memberships SET status='active' WHERE workspace_id=(SELECT id FROM ids) AND user_id='{MEERA}';
UPDATE public.workspace_creation_receipts SET original_name=' ' WHERE actor_id='{MEERA}' AND request_key='{KEY}';
DO $test$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.workspace_creation_recovery_status('{KEY}') WHERE status='unknown' AND workspace_id IS NULL) THEN RAISE EXCEPTION 'FAIL: malformed payload exposed'; END IF;
END $test$;
UPDATE public.workspace_creation_receipts SET original_name='Private Academy',workspace_id='ffffffff-ffff-4fff-8fff-ffffffffffff' WHERE actor_id='{MEERA}' AND request_key='{KEY}';
DO $test$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.workspace_creation_recovery_status('{KEY}') WHERE status='unknown' AND workspace_id IS NULL) THEN RAISE EXCEPTION 'FAIL: mismatched workspace exposed'; END IF;
END $test$;
UPDATE public.workspace_creation_receipts SET workspace_id=(SELECT id FROM ids) WHERE actor_id='{MEERA}' AND request_key='{KEY}';
UPDATE public.workspaces SET status='suspended' WHERE id=(SELECT id FROM ids);
DO $test$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.workspace_creation_recovery_status('{KEY}') WHERE status='unknown' AND workspace_id IS NULL) THEN RAISE EXCEPTION 'FAIL: suspended workspace exposed'; END IF;
END $test$;
DELETE FROM public.workspace_memberships WHERE workspace_id=(SELECT id FROM ids);
DELETE FROM public.workspaces WHERE id=(SELECT id FROM ids);
DO $test$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.workspace_creation_recovery_status('{KEY}') WHERE status='unknown' AND workspace_id IS NULL) THEN RAISE EXCEPTION 'FAIL: deleted workspace exposed'; END IF;
  RAISE NOTICE 'PASS: unknown and inactive states reveal no identifier';
END $test$;
ROLLBACK;
""")
        self.assertIn('PASS: unknown and inactive states reveal no identifier', notice)

    def test_private_access_disabled_control_and_invalid_inputs(self):
        notice = run_sql_with_notices(f"""
BEGIN; UPDATE public.workspace_creation_controls SET enabled=false WHERE id=true;
SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
DO $test$ DECLARE denied boolean := false; BEGIN
  IF has_function_privilege('anon','public.workspace_creation_recovery_status(uuid)','EXECUTE') OR has_function_privilege('authenticated','public.workspace_creation_recovery_status(uuid)','EXECUTE') THEN RAISE EXCEPTION 'FAIL: application role can call private status'; END IF;
  BEGIN PERFORM public.workspace_creation_recovery_status('{KEY}'); EXCEPTION WHEN insufficient_privilege THEN denied := true; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: disabled control allowed status'; END IF;
END $test$;
SET LOCAL ROLE authenticated;
DO $test$ DECLARE denied boolean := false; BEGIN
  BEGIN PERFORM public.workspace_creation_recovery_status('{KEY}');
  EXCEPTION WHEN insufficient_privilege THEN IF SQLERRM LIKE 'permission denied for function%' THEN denied := true; ELSE RAISE; END IF; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: authenticated direct call allowed'; END IF;
END $test$;
RESET ROLE;
SET LOCAL ROLE anon;
DO $test$ DECLARE denied boolean := false; BEGIN
  BEGIN PERFORM public.workspace_creation_recovery_status('{KEY}');
  EXCEPTION WHEN insufficient_privilege THEN IF SQLERRM LIKE 'permission denied for function%' THEN denied := true; ELSE RAISE; END IF; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: anonymous direct call allowed'; END IF;
END $test$;
RESET ROLE;
DELETE FROM public.workspace_creation_controls WHERE id=true;
DO $test$ DECLARE denied boolean := false; BEGIN
  BEGIN PERFORM public.workspace_creation_recovery_status('{KEY}'); EXCEPTION WHEN insufficient_privilege THEN denied := true; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: missing control allowed status'; END IF;
END $test$;
INSERT INTO public.workspace_creation_controls(id,enabled) VALUES (true,true);
SELECT set_config('request.jwt.claim.sub','',true);
DO $test$ DECLARE denied boolean := false; BEGIN
  BEGIN PERFORM public.workspace_creation_recovery_status('{KEY}'); EXCEPTION WHEN OTHERS THEN IF SQLERRM='Authentication required' THEN denied := true; ELSE RAISE; END IF; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: null actor allowed'; END IF;
END $test$;
SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
DO $test$ DECLARE denied boolean := false; BEGIN
  BEGIN PERFORM public.workspace_creation_recovery_status(NULL); EXCEPTION WHEN OTHERS THEN IF SQLERRM='Request ID required' THEN denied := true; ELSE RAISE; END IF; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: null key allowed'; END IF;
  RAISE NOTICE 'PASS: private status rejects invalid access';
END $test$;
ROLLBACK;
""")
        self.assertIn('PASS: private status rejects invalid access', notice)

    def test_unknown_snapshot_does_not_prevent_later_creation(self):
        result = run_sql(f"""
BEGIN; UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;
SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
SELECT status FROM public.workspace_creation_recovery_status('{KEY}');
SET LOCAL ROLE authenticated; SELECT public.create_workspace('Later Academy','academy','{KEY}');
RESET ROLE; SELECT status FROM public.workspace_creation_recovery_status('{KEY}');
ROLLBACK;
""")
        self.assertIn('unknown', result.splitlines())
        self.assertEqual(result.splitlines()[-1], 'known')

    def exercise_inflight_creation(self, commits):
        key = str(uuid.uuid4())
        first = second = None
        first_name, second_name = 'recovery_create_' + uuid.uuid4().hex, 'recovery_status_' + uuid.uuid4().hex
        previous_enabled = query("SELECT enabled FROM public.workspace_creation_controls WHERE id=true;")
        query('UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;')
        try:
            first, second = start_psql_session(), start_psql_session()
            first.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{first_name}',false); SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT public.create_workspace('Race Academy','academy','{key}'); SELECT 'CREATE_READY';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'CREATE_READY'))
            second.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{second_name}',false); SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT 'STATUS:' || status || ':' || coalesce(workspace_id::text,'-') FROM public.workspace_creation_recovery_status('{key}'); COMMIT;\n")
            second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name, first_name))
            first.stdin.write(('COMMIT' if commits else 'ROLLBACK') + "; SELECT 'CREATE_DONE';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'CREATE_DONE'))
            second.stdin.close()
            second.stdin = None
            output, errors = second.communicate(timeout=15)
            self.assertEqual(second.returncode, 0, errors)
            if commits:
                workspace_id = query(f"SELECT id FROM public.workspaces WHERE created_by='{MEERA}' AND creation_request_id='{key}';")
                self.assertIn('STATUS:known:' + workspace_id, output)
            else:
                self.assertIn('STATUS:unknown:-', output)
        finally:
            for process in (second, first):
                if process is not None:
                    close_psql_session(process)
            query(f"BEGIN; DELETE FROM public.workspace_memberships WHERE workspace_id IN (SELECT id FROM public.workspaces WHERE created_by='{MEERA}' AND creation_request_id='{key}'); DELETE FROM public.workspace_creation_receipts WHERE actor_id='{MEERA}' AND request_key='{key}'; DELETE FROM public.workspaces WHERE created_by='{MEERA}' AND creation_request_id='{key}'; UPDATE public.workspace_creation_controls SET enabled={'true' if previous_enabled == 't' else 'false'} WHERE id=true; COMMIT;")

    def test_recovery_waits_for_committed_creation(self):
        self.exercise_inflight_creation(True)

    def test_recovery_waits_for_rolled_back_creation(self):
        self.exercise_inflight_creation(False)

    def exercise_access_race(self, target, change_first, commits):
        key = str(uuid.uuid4())
        first = second = None
        first_name, second_name = 'recovery_first_' + uuid.uuid4().hex, 'recovery_second_' + uuid.uuid4().hex
        previous_enabled = query("SELECT enabled FROM public.workspace_creation_controls WHERE id=true;")
        query('UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;')
        workspace_id = None
        try:
            output = query(f"BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT 'WID:' || public.create_workspace('Race Academy','academy','{key}')::text; COMMIT;")
            workspace_id = extract_labeled_id(output, 'WID:')
            change = ('UPDATE public.workspace_creation_controls SET enabled=false WHERE id=true' if target == 'control' else
                      f"UPDATE public.workspaces SET status='suspended' WHERE id='{workspace_id}'" if target == 'workspace' else
                      f"UPDATE public.workspace_memberships SET status='suspended' WHERE workspace_id='{workspace_id}' AND user_id='{MEERA}'")
            status = f"SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT 'STATUS:' || status || ':' || coalesce(workspace_id::text,'-') FROM public.workspace_creation_recovery_status('{key}')"
            first, second = start_psql_session(), start_psql_session()
            first_sql, second_sql = (change, status) if change_first else (status, change)
            first.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{first_name}',false); {first_sql}; SELECT 'FIRST_READY';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_READY'))
            second.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{second_name}',false); {second_sql}; COMMIT; SELECT 'SECOND_DONE';\n")
            second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name, first_name))
            first.stdin.write(('COMMIT' if commits else 'ROLLBACK') + "; SELECT 'FIRST_DONE';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_DONE'))
            second.stdin.close()
            second.stdin = None
            output, errors = second.communicate(timeout=15)
            if change_first and commits and target == 'control':
                self.assertNotEqual(second.returncode, 0)
                self.assertIn('Workspace creation unavailable', errors)
            else:
                self.assertEqual(second.returncode, 0, errors)
                if change_first:
                    expected = 'STATUS:unknown:-' if commits else 'STATUS:known:' + workspace_id
                    self.assertIn(expected, output)
        finally:
            for process in (second, first):
                if process is not None:
                    close_psql_session(process)
            if workspace_id:
                query(f"BEGIN; DELETE FROM public.workspace_memberships WHERE workspace_id='{workspace_id}'; DELETE FROM public.workspace_creation_receipts WHERE actor_id='{MEERA}' AND request_key='{key}'; DELETE FROM public.workspaces WHERE id='{workspace_id}'; UPDATE public.workspace_creation_controls SET enabled={'true' if previous_enabled == 't' else 'false'} WHERE id=true; COMMIT;")
            else:
                query(f"UPDATE public.workspace_creation_controls SET enabled={'true' if previous_enabled == 't' else 'false'} WHERE id=true;")

    def test_control_disable_commit_before_recovery(self):
        self.exercise_access_race('control', True, True)

    def test_control_disable_rollback_before_recovery(self):
        self.exercise_access_race('control', True, False)

    def test_membership_suspend_commit_before_recovery(self):
        self.exercise_access_race('membership', True, True)

    def test_membership_suspend_rollback_before_recovery(self):
        self.exercise_access_race('membership', True, False)

    def test_recovery_blocks_control_disable_until_commit(self):
        self.exercise_access_race('control', False, True)

    def test_recovery_blocks_membership_suspend_until_commit(self):
        self.exercise_access_race('membership', False, True)

    def test_workspace_suspend_commit_before_recovery(self):
        self.exercise_access_race('workspace', True, True)

    def test_workspace_suspend_rollback_before_recovery(self):
        self.exercise_access_race('workspace', True, False)

    def test_recovery_blocks_workspace_suspend_until_commit(self):
        self.exercise_access_race('workspace', False, True)

    def test_unknown_before_later_transaction_does_not_prove_absence(self):
        key = str(uuid.uuid4())
        previous_enabled = query("SELECT enabled FROM public.workspace_creation_controls WHERE id=true;")
        query('UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;')
        try:
            output = query(f"BEGIN; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT 'STATUS:' || status FROM public.workspace_creation_recovery_status('{key}'); COMMIT;")
            self.assertIn('STATUS:unknown', output)
            query(f"BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT public.create_workspace('Later Academy','academy','{key}'); COMMIT;")
            output = query(f"BEGIN; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT 'STATUS:' || status FROM public.workspace_creation_recovery_status('{key}'); COMMIT;")
            self.assertIn('STATUS:known', output)
        finally:
            query(f"BEGIN; DELETE FROM public.workspace_memberships WHERE workspace_id IN (SELECT id FROM public.workspaces WHERE created_by='{MEERA}' AND creation_request_id='{key}'); DELETE FROM public.workspace_creation_receipts WHERE actor_id='{MEERA}' AND request_key='{key}'; DELETE FROM public.workspaces WHERE created_by='{MEERA}' AND creation_request_id='{key}'; UPDATE public.workspace_creation_controls SET enabled={'true' if previous_enabled == 't' else 'false'} WHERE id=true; COMMIT;")

    def test_receipt_is_rechecked_after_workspace_lock_wait(self):
        key = str(uuid.uuid4())
        first = second = None
        first_name, second_name = 'receipt_first_' + uuid.uuid4().hex, 'receipt_second_' + uuid.uuid4().hex
        previous_enabled = query("SELECT enabled FROM public.workspace_creation_controls WHERE id=true;")
        query('UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;')
        try:
            query(f"BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT public.create_workspace('Receipt Academy','academy','{key}'); COMMIT;")
            first, second = start_psql_session(), start_psql_session()
            first.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{first_name}',false); UPDATE public.workspaces SET name=name WHERE created_by='{MEERA}' AND creation_request_id='{key}'; UPDATE public.workspace_creation_receipts SET original_name=NULL,original_type=NULL WHERE actor_id='{MEERA}' AND request_key='{key}'; SELECT 'FIRST_READY';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_READY'))
            second.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{second_name}',false); SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT 'STATUS:' || status FROM public.workspace_creation_recovery_status('{key}'); COMMIT;\n")
            second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name, first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_DONE';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_DONE'))
            second.stdin.close()
            second.stdin = None
            output, errors = second.communicate(timeout=15)
            self.assertEqual(second.returncode, 0, errors)
            self.assertIn('STATUS:unknown', output)
        finally:
            for process in (second, first):
                if process is not None:
                    close_psql_session(process)
            query(f"BEGIN; DELETE FROM public.workspace_memberships WHERE workspace_id IN (SELECT id FROM public.workspaces WHERE created_by='{MEERA}' AND creation_request_id='{key}'); DELETE FROM public.workspace_creation_receipts WHERE actor_id='{MEERA}' AND request_key='{key}'; DELETE FROM public.workspaces WHERE created_by='{MEERA}' AND creation_request_id='{key}'; UPDATE public.workspace_creation_controls SET enabled={'true' if previous_enabled == 't' else 'false'} WHERE id=true; COMMIT;")
