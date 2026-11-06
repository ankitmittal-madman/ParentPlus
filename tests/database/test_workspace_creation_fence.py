"""Synthetic tests for the private exact-request workspace fence."""

import unittest
import uuid

from tests.database.test_authorization import MEERA, RAHUL, run_sql, run_sql_with_notices
from tests.database.test_concurrent_authorization import (
    close_psql_session, query, start_psql_session, wait_for_blocking_relationship, wait_for_session_marker,
)

KEY = 'b1111111-aaaa-4aaa-8aaa-111111111111'


class WorkspaceCreationFenceTests(unittest.TestCase):
    def test_absent_request_can_be_fenced_idempotently(self):
        output = run_sql(f"""
BEGIN; UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;
SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
SELECT public.fence_workspace_creation('{KEY}');
SELECT public.fence_workspace_creation('{KEY}');
ROLLBACK;
""")
        self.assertEqual(output.splitlines()[-2:], ['fenced', 'fenced'])

    def test_stricter_transaction_isolation_rejects_fence_and_insert(self):
        for isolation in ('READ UNCOMMITTED', 'REPEATABLE READ', 'SERIALIZABLE'):
            with self.subTest(isolation=isolation):
                notice = run_sql_with_notices(f"""
BEGIN ISOLATION LEVEL {isolation}; UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;
SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
DO $test$ DECLARE denied boolean := false; BEGIN
  BEGIN PERFORM public.fence_workspace_creation('{KEY}');
  EXCEPTION WHEN feature_not_supported THEN IF SQLERRM='Workspace creation isolation unsupported' THEN denied:=true; ELSE RAISE; END IF; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: stricter isolation allowed fence'; END IF;
  denied:=false;
  BEGIN INSERT INTO public.workspaces(name,type,created_by,creation_request_id) VALUES ('Isolation Academy','academy','{MEERA}','{KEY}');
  EXCEPTION WHEN feature_not_supported THEN IF SQLERRM='Workspace creation isolation unsupported' THEN denied:=true; ELSE RAISE; END IF; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: stricter isolation allowed insert'; END IF;
  RAISE NOTICE 'PASS: stricter isolation fails closed';
END $test$;
ROLLBACK;
""")
                self.assertIn('PASS: stricter isolation fails closed', notice)

    def test_stale_snapshot_cannot_bypass_a_committed_fence(self):
        for isolation in ('REPEATABLE READ', 'SERIALIZABLE'):
            for legacy in (False, True):
                with self.subTest(isolation=isolation, legacy=legacy):
                    key = str(uuid.uuid4())
                    writer = None
                    name = 'stale_snapshot_' + uuid.uuid4().hex
                    previous_enabled = query('SELECT enabled FROM public.workspace_creation_controls WHERE id=true;')
                    query('UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;')
                    try:
                        writer = start_psql_session()
                        writer.stdin.write(f"BEGIN ISOLATION LEVEL {isolation}; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{name}',false); SELECT count(*) FROM public.workspace_creation_fences; SELECT 'SNAPSHOT_READY';\n")
                        writer.stdin.flush()
                        self.assertTrue(wait_for_session_marker(writer, 'SNAPSHOT_READY'))
                        result = query(f"BEGIN; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT 'FENCE:' || public.fence_workspace_creation('{key}'); COMMIT;")
                        self.assertIn('FENCE:fenced', result)
                        attempt = (f"INSERT INTO public.workspaces(name,type,created_by,creation_request_id) VALUES ('Stale Academy','academy','{MEERA}','{key}')" if legacy else
                                   f"SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT public.create_workspace('Stale Academy','academy','{key}')")
                        writer.stdin.write(attempt + '; COMMIT;\n')
                        writer.stdin.flush()
                        writer.stdin.close()
                        writer.stdin = None
                        _, errors = writer.communicate(timeout=15)
                        self.assertNotEqual(writer.returncode, 0)
                        self.assertIn('Workspace creation isolation unsupported', errors)
                        self.assertEqual(query(f"SELECT (SELECT count(*) FROM public.workspaces WHERE created_by='{MEERA}' AND creation_request_id='{key}') || ':' || (SELECT count(*) FROM public.workspace_creation_receipts WHERE actor_id='{MEERA}' AND request_key='{key}');").splitlines()[-1], '0:0')
                    finally:
                        if writer is not None:
                            close_psql_session(writer)
                        query(f"BEGIN; DELETE FROM public.workspace_creation_fences WHERE actor_id='{MEERA}' AND request_key='{key}'; UPDATE public.workspace_creation_controls SET enabled={'true' if previous_enabled == 't' else 'false'} WHERE id=true; COMMIT;")

    def test_existing_receipt_or_workspace_never_reports_fenced(self):
        notice = run_sql_with_notices(f"""
BEGIN; UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
SELECT public.create_workspace('Existing Academy','academy','{KEY}'); RESET ROLE;
DO $test$ BEGIN
  IF public.fence_workspace_creation('{KEY}') <> 'unknown' THEN RAISE EXCEPTION 'FAIL: existing receipt fenced'; END IF;
END $test$;
UPDATE public.workspace_creation_receipts SET original_name=NULL,original_type=NULL WHERE actor_id='{MEERA}' AND request_key='{KEY}';
DO $test$ BEGIN
  IF public.fence_workspace_creation('{KEY}') <> 'unknown' THEN RAISE EXCEPTION 'FAIL: legacy receipt fenced'; END IF;
END $test$;
DELETE FROM public.workspace_creation_receipts WHERE actor_id='{MEERA}' AND request_key='{KEY}';
DO $test$ BEGIN
  IF public.fence_workspace_creation('{KEY}') <> 'unknown' THEN RAISE EXCEPTION 'FAIL: surviving workspace fenced'; END IF;
  RAISE NOTICE 'PASS: existing outcomes stay unknown';
END $test$;
ROLLBACK;
""")
        self.assertIn('PASS: existing outcomes stay unknown', notice)

    def test_fence_blocks_modern_and_direct_late_insert_without_mutation(self):
        notice = run_sql_with_notices(f"""
BEGIN; UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;
SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
SELECT public.fence_workspace_creation('{KEY}');
SET LOCAL ROLE authenticated;
DO $test$ DECLARE denied boolean := false; BEGIN
  BEGIN PERFORM public.create_workspace('Delayed Academy','academy','{KEY}');
  EXCEPTION WHEN insufficient_privilege THEN IF SQLERRM='Workspace creation request fenced' THEN denied:=true; ELSE RAISE; END IF; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: modern request not blocked'; END IF;
END $test$;
RESET ROLE;
DO $test$ DECLARE denied boolean := false; BEGIN
  BEGIN INSERT INTO public.workspaces(name,type,created_by,creation_request_id) VALUES ('Delayed Academy','academy','{MEERA}','{KEY}');
  EXCEPTION WHEN insufficient_privilege THEN IF SQLERRM='Workspace creation request fenced' THEN denied:=true; ELSE RAISE; END IF; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: legacy insertion not blocked'; END IF;
  IF EXISTS(SELECT 1 FROM public.workspaces WHERE created_by='{MEERA}' AND creation_request_id='{KEY}') OR EXISTS(SELECT 1 FROM public.workspace_creation_receipts WHERE actor_id='{MEERA}' AND request_key='{KEY}') THEN RAISE EXCEPTION 'FAIL: fenced request mutated records'; END IF;
  RAISE NOTICE 'PASS: exact key blocks both insertion paths';
END $test$;
ROLLBACK;
""")
        self.assertIn('PASS: exact key blocks both insertion paths', notice)

    def test_private_access_control_and_actor_scope(self):
        notice = run_sql_with_notices(f"""
BEGIN; UPDATE public.workspace_creation_controls SET enabled=false WHERE id=true;
SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
DO $test$ DECLARE denied boolean := false; BEGIN
  IF has_function_privilege('authenticated','public.fence_workspace_creation(uuid)','EXECUTE') OR has_function_privilege('anon','public.fence_workspace_creation(uuid)','EXECUTE') OR has_function_privilege('authenticated','public.guard_fenced_workspace_creation()','EXECUTE') OR has_function_privilege('anon','public.guard_fenced_workspace_creation()','EXECUTE') OR has_table_privilege('authenticated','public.workspace_creation_fences','SELECT') OR has_table_privilege('authenticated','public.workspace_creation_fences','INSERT') OR has_table_privilege('authenticated','public.workspace_creation_fences','UPDATE') OR has_table_privilege('authenticated','public.workspace_creation_fences','DELETE') THEN RAISE EXCEPTION 'FAIL: fence exposed'; END IF;
  BEGIN PERFORM public.fence_workspace_creation('{KEY}'); EXCEPTION WHEN insufficient_privilege THEN denied:=true; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: disabled control allowed fencing'; END IF;
END $test$;
SET LOCAL ROLE authenticated;
DO $test$ DECLARE denied boolean := false; BEGIN
  BEGIN PERFORM public.fence_workspace_creation('{KEY}');
  EXCEPTION WHEN insufficient_privilege THEN IF SQLERRM LIKE 'permission denied for function%' THEN denied:=true; ELSE RAISE; END IF; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: authenticated fence call allowed'; END IF;
END $test$;
RESET ROLE;
SET LOCAL ROLE anon;
DO $test$ DECLARE denied boolean := false; BEGIN
  BEGIN PERFORM public.fence_workspace_creation('{KEY}');
  EXCEPTION WHEN insufficient_privilege THEN IF SQLERRM LIKE 'permission denied for function%' THEN denied:=true; ELSE RAISE; END IF; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: anonymous fence call allowed'; END IF;
END $test$;
RESET ROLE;
DELETE FROM public.workspace_creation_controls WHERE id=true;
DO $test$ DECLARE denied boolean := false; BEGIN
  BEGIN PERFORM public.fence_workspace_creation('{KEY}'); EXCEPTION WHEN insufficient_privilege THEN denied:=true; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: missing control allowed fencing'; END IF;
END $test$;
INSERT INTO public.workspace_creation_controls(id,enabled) VALUES (true,true);
SELECT set_config('request.jwt.claim.sub','',true);
DO $test$ DECLARE denied boolean := false; BEGIN
  BEGIN PERFORM public.fence_workspace_creation('{KEY}'); EXCEPTION WHEN OTHERS THEN IF SQLERRM='Authentication required' THEN denied:=true; ELSE RAISE; END IF; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: missing actor allowed fencing'; END IF;
END $test$;
SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
DO $test$ DECLARE denied boolean := false; BEGIN
  BEGIN PERFORM public.fence_workspace_creation(NULL); EXCEPTION WHEN OTHERS THEN IF SQLERRM='Request ID required' THEN denied:=true; ELSE RAISE; END IF; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: missing key allowed fencing'; END IF;
END $test$;
UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;
SELECT public.fence_workspace_creation('{KEY}');
SELECT set_config('request.jwt.claim.sub','{RAHUL}',true);
DO $test$ BEGIN
  IF public.fence_workspace_creation('{KEY}') <> 'fenced' THEN RAISE EXCEPTION 'FAIL: separate actor not independent'; END IF;
  IF (SELECT count(*) FROM public.workspace_creation_fences WHERE request_key='{KEY}') <> 2 THEN RAISE EXCEPTION 'FAIL: actor scope lost'; END IF;
  RAISE NOTICE 'PASS: fence is private, controlled and actor scoped';
END $test$;
ROLLBACK;
""")
        self.assertIn('PASS: fence is private, controlled and actor scoped', notice)

    def test_conflicting_insert_does_not_create_extra_receipt(self):
        output = run_sql(f"""
BEGIN; UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
SELECT public.create_workspace('Existing Academy','academy','{KEY}'); RESET ROLE;
INSERT INTO public.workspaces(name,type,created_by,creation_request_id) VALUES ('Existing Academy','academy','{MEERA}','{KEY}') ON CONFLICT (created_by,creation_request_id) DO NOTHING;
SELECT (SELECT count(*) FROM public.workspaces) || ':' || (SELECT count(*) FROM public.workspace_creation_receipts) || ':' || (SELECT count(*) FROM public.workspace_creation_fences);
ROLLBACK;
""")
        self.assertEqual(output.splitlines()[-1], '1:1:0')

    def test_fence_for_one_actor_does_not_block_another_actor(self):
        output = run_sql(f"""
BEGIN; UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;
SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
SELECT public.fence_workspace_creation('{KEY}');
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{RAHUL}',true);
SELECT 'OTHER:' || public.create_workspace('Other Academy','academy','{KEY}')::text;
RESET ROLE;
SELECT count(*) FROM public.workspaces WHERE created_by='{RAHUL}' AND creation_request_id='{KEY}';
ROLLBACK;
""")
        self.assertTrue(any(line.startswith('OTHER:') for line in output.splitlines()))
        self.assertEqual(output.splitlines()[-1], '1')

    def test_concurrent_identical_fences_are_idempotent(self):
        key = str(uuid.uuid4())
        first = second = None
        first_name, second_name = 'fence_one_' + uuid.uuid4().hex, 'fence_two_' + uuid.uuid4().hex
        previous_enabled = query('SELECT enabled FROM public.workspace_creation_controls WHERE id=true;')
        query('UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;')
        try:
            first, second = start_psql_session(), start_psql_session()
            first.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{first_name}',false); SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT public.fence_workspace_creation('{key}'); SELECT 'FIRST_READY';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_READY'))
            second.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{second_name}',false); SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT 'RESULT:' || public.fence_workspace_creation('{key}'); COMMIT;\n")
            second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name, first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_DONE';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_DONE'))
            second.stdin.close()
            second.stdin = None
            output, errors = second.communicate(timeout=15)
            self.assertEqual(second.returncode, 0, errors)
            self.assertIn('RESULT:fenced', output)
            self.assertEqual(query(f"SELECT count(*) FROM public.workspace_creation_fences WHERE actor_id='{MEERA}' AND request_key='{key}';"), '1')
        finally:
            for process in (second, first):
                if process is not None:
                    close_psql_session(process)
            query(f"BEGIN; DELETE FROM public.workspace_creation_fences WHERE actor_id='{MEERA}' AND request_key='{key}'; UPDATE public.workspace_creation_controls SET enabled={'true' if previous_enabled == 't' else 'false'} WHERE id=true; COMMIT;")

    def exercise_legacy_modern_race(self, legacy_first, commits):
        key = str(uuid.uuid4())
        first = second = None
        first_name, second_name = 'legacy_first_' + uuid.uuid4().hex, 'modern_second_' + uuid.uuid4().hex
        previous_enabled = query('SELECT enabled FROM public.workspace_creation_controls WHERE id=true;')
        query('UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;')
        try:
            first, second = start_psql_session(), start_psql_session()
            legacy = f"INSERT INTO public.workspaces(name,type,created_by,creation_request_id) VALUES ('Race Academy','academy','{MEERA}','{key}') ON CONFLICT (created_by,creation_request_id) DO NOTHING"
            modern = f"SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT public.create_workspace('Race Academy','academy','{key}')"
            first_sql, second_sql = (legacy, modern) if legacy_first else (modern, legacy)
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
            if legacy_first and commits:
                self.assertNotEqual(second.returncode, 0)
                self.assertIn('Workspace unavailable', errors)
            else:
                self.assertEqual(second.returncode, 0, errors)
                self.assertIn('SECOND_DONE', output)
            self.assertNotIn('deadlock detected', errors.lower())
            self.assertEqual(query(f"SELECT count(*) FROM public.workspaces WHERE created_by='{MEERA}' AND creation_request_id='{key}';"), '1')
            self.assertEqual(query(f"SELECT count(*) FROM public.workspace_creation_receipts WHERE actor_id='{MEERA}' AND request_key='{key}';"), '1')
        finally:
            for process in (second, first):
                if process is not None:
                    close_psql_session(process)
            query(f"BEGIN; DELETE FROM public.workspace_memberships WHERE workspace_id IN (SELECT id FROM public.workspaces WHERE created_by='{MEERA}' AND creation_request_id='{key}'); DELETE FROM public.workspace_creation_receipts WHERE actor_id='{MEERA}' AND request_key='{key}'; DELETE FROM public.workspaces WHERE created_by='{MEERA}' AND creation_request_id='{key}'; DELETE FROM public.workspace_creation_fences WHERE actor_id='{MEERA}' AND request_key='{key}'; UPDATE public.workspace_creation_controls SET enabled={'true' if previous_enabled == 't' else 'false'} WHERE id=true; COMMIT;")

    def test_legacy_insert_commit_precedes_modern_creation(self):
        self.exercise_legacy_modern_race(True, True)

    def test_legacy_insert_rollback_precedes_modern_creation(self):
        self.exercise_legacy_modern_race(True, False)

    def test_modern_creation_commit_precedes_legacy_insert(self):
        self.exercise_legacy_modern_race(False, True)

    def test_modern_creation_rollback_precedes_legacy_insert(self):
        self.exercise_legacy_modern_race(False, False)

    def exercise_fence_creation_race(self, fence_first, commits):
        key = str(uuid.uuid4())
        first = second = None
        first_name, second_name = 'fence_first_' + uuid.uuid4().hex, 'fence_second_' + uuid.uuid4().hex
        previous_enabled = query('SELECT enabled FROM public.workspace_creation_controls WHERE id=true;')
        query('UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;')
        try:
            first, second = start_psql_session(), start_psql_session()
            fence = f"SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT 'RESULT:' || public.fence_workspace_creation('{key}')"
            create = f"SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT 'CREATED:' || public.create_workspace('Race Academy','academy','{key}')::text"
            first_sql, second_sql = (fence, create) if fence_first else (create, fence)
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
            if fence_first and commits:
                self.assertNotEqual(second.returncode, 0)
                self.assertIn('Workspace creation request fenced', errors)
            else:
                self.assertEqual(second.returncode, 0, errors)
                if not fence_first:
                    self.assertIn('RESULT:unknown' if commits else 'RESULT:fenced', output)
            self.assertEqual(query(f"SELECT count(*) FROM public.workspaces WHERE created_by='{MEERA}' AND creation_request_id='{key}';"), '1' if commits != fence_first else '0')
        finally:
            for process in (second, first):
                if process is not None:
                    close_psql_session(process)
            query(f"BEGIN; DELETE FROM public.workspace_memberships WHERE workspace_id IN (SELECT id FROM public.workspaces WHERE created_by='{MEERA}' AND creation_request_id='{key}'); DELETE FROM public.workspace_creation_receipts WHERE actor_id='{MEERA}' AND request_key='{key}'; DELETE FROM public.workspaces WHERE created_by='{MEERA}' AND creation_request_id='{key}'; DELETE FROM public.workspace_creation_fences WHERE actor_id='{MEERA}' AND request_key='{key}'; UPDATE public.workspace_creation_controls SET enabled={'true' if previous_enabled == 't' else 'false'} WHERE id=true; COMMIT;")

    def test_fence_commit_blocks_waiting_creation(self):
        self.exercise_fence_creation_race(True, True)

    def test_fence_rollback_allows_waiting_creation(self):
        self.exercise_fence_creation_race(True, False)

    def test_creation_commit_leaves_waiting_fence_unknown(self):
        self.exercise_fence_creation_race(False, True)

    def test_creation_rollback_allows_waiting_fence(self):
        self.exercise_fence_creation_race(False, False)

    def exercise_control_race(self, disable_first, commits):
        key = str(uuid.uuid4())
        first = second = None
        first_name, second_name = 'fence_control_one_' + uuid.uuid4().hex, 'fence_control_two_' + uuid.uuid4().hex
        previous_enabled = query('SELECT enabled FROM public.workspace_creation_controls WHERE id=true;')
        query('UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;')
        try:
            first, second = start_psql_session(), start_psql_session()
            disable = 'UPDATE public.workspace_creation_controls SET enabled=false WHERE id=true'
            fence = f"SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT 'RESULT:' || public.fence_workspace_creation('{key}')"
            first_sql, second_sql = (disable, fence) if disable_first else (fence, disable)
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
            if disable_first and commits:
                self.assertNotEqual(second.returncode, 0)
                self.assertIn('Workspace creation unavailable', errors)
                self.assertEqual(query(f"SELECT count(*) FROM public.workspace_creation_fences WHERE actor_id='{MEERA}' AND request_key='{key}';"), '0')
            else:
                self.assertEqual(second.returncode, 0, errors)
                self.assertIn('SECOND_DONE', output)
        finally:
            for process in (second, first):
                if process is not None:
                    close_psql_session(process)
            query(f"BEGIN; DELETE FROM public.workspace_creation_fences WHERE actor_id='{MEERA}' AND request_key='{key}'; UPDATE public.workspace_creation_controls SET enabled={'true' if previous_enabled == 't' else 'false'} WHERE id=true; COMMIT;")

    def test_control_disable_commit_blocks_fence(self):
        self.exercise_control_race(True, True)

    def test_control_disable_rollback_allows_fence(self):
        self.exercise_control_race(True, False)

    def test_fence_holds_control_until_commit(self):
        self.exercise_control_race(False, True)
