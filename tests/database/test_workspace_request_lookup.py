"""Synthetic checks for a private, single-workspace request lookup."""

import unittest
import uuid

from tests.database.test_authorization import MEERA, RAHUL, run_sql, run_sql_with_notices
from tests.database.test_concurrent_authorization import (
    close_psql_session, query, start_psql_session, wait_for_blocking_relationship, wait_for_session_marker,
)

KEY = '20000000-aaaa-4aaa-8aaa-222222222222'


class WorkspaceRequestLookupTests(unittest.TestCase):
    def test_missing_workspace_is_unknown_without_mutation(self):
        output = run_sql(f"""
BEGIN; UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;
SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
SELECT public.workspace_creation_key_for_workspace('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa');
SELECT (SELECT count(*) FROM public.workspaces) || ':' || (SELECT count(*) FROM public.workspace_creation_receipts);
ROLLBACK;
""")
        self.assertEqual(output.splitlines()[-2:], ['{"status": "unknown"}', '0:0'])

    def test_creator_can_find_known_key_without_names(self):
        notice = run_sql_with_notices(f"""
BEGIN; UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;
CREATE TEMP TABLE ids(id uuid); GRANT SELECT, INSERT ON ids TO authenticated;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
INSERT INTO ids SELECT public.create_workspace('Known Academy','academy','{KEY}'); RESET ROLE;
DO $test$ DECLARE item jsonb; BEGIN
  item:=public.workspace_creation_key_for_workspace((SELECT id FROM ids));
  IF item->>'status' IS DISTINCT FROM 'known' OR item->>'request_key' IS DISTINCT FROM '{KEY}' OR item->>'workspace_id' IS DISTINCT FROM (SELECT id::text FROM ids) OR (SELECT count(*) FROM jsonb_object_keys(item)) <> 3 THEN RAISE EXCEPTION 'FAIL: incorrect result'; END IF;
  RAISE NOTICE 'PASS: own known request returns IDs only';
END $test$;
ROLLBACK;
""")
        self.assertIn('PASS: own known request returns IDs only', notice)

    def test_empty_or_null_nested_status_fails_closed(self):
        notice = run_sql_with_notices(f"""
BEGIN; UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;
CREATE TEMP TABLE ids(id uuid); GRANT SELECT, INSERT ON ids TO authenticated;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
INSERT INTO ids SELECT public.create_workspace('Known Academy','academy','{KEY}'); RESET ROLE;
CREATE OR REPLACE FUNCTION public.workspace_creation_recovery_status(p_request_id uuid)
RETURNS TABLE(status text,workspace_id uuid) LANGUAGE sql SECURITY DEFINER SET search_path='' AS $body$ SELECT NULL::text,NULL::uuid $body$;
DO $test$ BEGIN
  IF public.workspace_creation_key_for_workspace((SELECT id FROM ids)) <> '{{"status":"unknown"}}'::jsonb THEN RAISE EXCEPTION 'FAIL: null helper result exposed'; END IF;
END $test$;
CREATE OR REPLACE FUNCTION public.workspace_creation_recovery_status(p_request_id uuid)
RETURNS TABLE(status text,workspace_id uuid) LANGUAGE sql SECURITY DEFINER SET search_path='' AS $body$ SELECT NULL::text,NULL::uuid WHERE false $body$;
DO $test$ BEGIN
  IF public.workspace_creation_key_for_workspace((SELECT id FROM ids)) <> '{{"status":"unknown"}}'::jsonb THEN RAISE EXCEPTION 'FAIL: missing helper result exposed'; END IF;
  RAISE NOTICE 'PASS: null or missing nested result fails closed';
END $test$;
ROLLBACK;
""")
        self.assertIn('PASS: null or missing nested result fails closed', notice)

    def test_other_creator_and_inaccessible_receipts_are_unknown(self):
        notice = run_sql_with_notices(f"""
BEGIN; UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;
CREATE TEMP TABLE ids(id uuid); GRANT SELECT, INSERT ON ids TO authenticated;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
INSERT INTO ids SELECT public.create_workspace('Shared Academy','academy','{KEY}'); RESET ROLE;
INSERT INTO public.workspace_memberships(workspace_id,user_id,role,status) VALUES ((SELECT id FROM ids),'{RAHUL}','coach','active');
SELECT set_config('request.jwt.claim.sub','{RAHUL}',true);
DO $test$ BEGIN
  IF public.workspace_creation_key_for_workspace((SELECT id FROM ids)) <> '{{"status":"unknown"}}'::jsonb THEN RAISE EXCEPTION 'FAIL: other creator key exposed'; END IF;
END $test$;
SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
UPDATE public.workspace_creation_receipts SET original_name=NULL,original_type=NULL WHERE actor_id='{MEERA}' AND request_key='{KEY}';
DO $test$ BEGIN
  IF public.workspace_creation_key_for_workspace((SELECT id FROM ids)) <> '{{"status":"unknown"}}'::jsonb THEN RAISE EXCEPTION 'FAIL: unknown legacy key exposed'; END IF;
END $test$;
UPDATE public.workspace_creation_receipts SET original_name='Shared Academy',original_type='academy' WHERE actor_id='{MEERA}' AND request_key='{KEY}';
UPDATE public.workspace_creation_receipts SET workspace_id='ffffffff-ffff-4fff-8fff-ffffffffffff' WHERE actor_id='{MEERA}' AND request_key='{KEY}';
DO $test$ BEGIN
  IF public.workspace_creation_key_for_workspace((SELECT id FROM ids)) <> '{{"status":"unknown"}}'::jsonb THEN RAISE EXCEPTION 'FAIL: mismatched receipt exposed'; END IF;
END $test$;
UPDATE public.workspace_creation_receipts SET workspace_id=(SELECT id FROM ids) WHERE actor_id='{MEERA}' AND request_key='{KEY}';
UPDATE public.workspace_memberships SET status='suspended' WHERE workspace_id=(SELECT id FROM ids) AND user_id='{MEERA}';
DO $test$ BEGIN
  IF public.workspace_creation_key_for_workspace((SELECT id FROM ids)) <> '{{"status":"unknown"}}'::jsonb THEN RAISE EXCEPTION 'FAIL: suspended membership exposed'; END IF;
END $test$;
UPDATE public.workspace_memberships SET status='active' WHERE workspace_id=(SELECT id FROM ids) AND user_id='{MEERA}';
UPDATE public.workspaces SET status='suspended' WHERE id=(SELECT id FROM ids);
DO $test$ BEGIN
  IF public.workspace_creation_key_for_workspace((SELECT id FROM ids)) <> '{{"status":"unknown"}}'::jsonb THEN RAISE EXCEPTION 'FAIL: suspended workspace exposed'; END IF;
  RAISE NOTICE 'PASS: inaccessible requests remain unknown';
END $test$;
ROLLBACK;
""")
        self.assertIn('PASS: inaccessible requests remain unknown', notice)

    def test_private_access_and_disabled_control_fail_closed(self):
        notice = run_sql_with_notices(f"""
BEGIN; UPDATE public.workspace_creation_controls SET enabled=false WHERE id=true;
SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
DO $test$ DECLARE denied boolean := false; BEGIN
  IF has_function_privilege('authenticated','public.workspace_creation_key_for_workspace(uuid)','EXECUTE') OR has_function_privilege('anon','public.workspace_creation_key_for_workspace(uuid)','EXECUTE') THEN RAISE EXCEPTION 'FAIL: app role exposed'; END IF;
  BEGIN PERFORM public.workspace_creation_key_for_workspace('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'); EXCEPTION WHEN insufficient_privilege THEN IF SQLERRM='Workspace creation unavailable' THEN denied:=true; ELSE RAISE; END IF; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: disabled control allowed lookup'; END IF;
END $test$;
SET LOCAL ROLE authenticated;
DO $test$ DECLARE denied boolean := false; BEGIN
  BEGIN PERFORM public.workspace_creation_key_for_workspace('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'); EXCEPTION WHEN insufficient_privilege THEN IF SQLERRM LIKE 'permission denied for function%' THEN denied:=true; ELSE RAISE; END IF; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: direct app call'; END IF;
END $test$; RESET ROLE;
SET LOCAL ROLE anon;
DO $test$ DECLARE denied boolean := false; BEGIN
  BEGIN PERFORM public.workspace_creation_key_for_workspace('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'); EXCEPTION WHEN insufficient_privilege THEN IF SQLERRM LIKE 'permission denied for function%' THEN denied:=true; ELSE RAISE; END IF; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: direct anonymous call'; END IF;
END $test$; RESET ROLE;
DELETE FROM public.workspace_creation_controls WHERE id=true;
DO $test$ DECLARE denied boolean := false; BEGIN
  BEGIN PERFORM public.workspace_creation_key_for_workspace('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'); EXCEPTION WHEN insufficient_privilege THEN denied:=true; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: missing control allowed lookup'; END IF;
END $test$;
INSERT INTO public.workspace_creation_controls(id,enabled) VALUES (true,true);
SELECT set_config('request.jwt.claim.sub','',true);
DO $test$ DECLARE denied boolean := false; BEGIN
  BEGIN PERFORM public.workspace_creation_key_for_workspace('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'); EXCEPTION WHEN OTHERS THEN IF SQLERRM='Authentication required' THEN denied:=true; ELSE RAISE; END IF; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: missing actor'; END IF;
END $test$;
SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
DO $test$ DECLARE denied boolean := false; BEGIN
  BEGIN PERFORM public.workspace_creation_key_for_workspace(NULL); EXCEPTION WHEN OTHERS THEN IF SQLERRM='Workspace ID required' THEN denied:=true; ELSE RAISE; END IF; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: null workspace ID'; END IF;
  RAISE NOTICE 'PASS: private lookup rejects invalid access';
END $test$;
ROLLBACK;
""")
        self.assertIn('PASS: private lookup rejects invalid access', notice)

    def test_non_read_committed_isolation_fails_closed(self):
        for isolation in ('READ UNCOMMITTED','REPEATABLE READ','SERIALIZABLE'):
            with self.subTest(isolation=isolation):
                notice = run_sql_with_notices(f"""
BEGIN ISOLATION LEVEL {isolation}; UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;
SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
DO $test$ DECLARE denied boolean := false; BEGIN
  BEGIN PERFORM public.workspace_creation_key_for_workspace('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa');
  EXCEPTION WHEN feature_not_supported THEN IF SQLERRM='Workspace recovery isolation unsupported' THEN denied:=true; ELSE RAISE; END IF; END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: non-read-committed lookup allowed'; END IF;
  RAISE NOTICE 'PASS: isolation fails closed';
END $test$;
ROLLBACK;
""")
                self.assertIn('PASS: isolation fails closed', notice)

    def exercise_access_race(self, target, change_first, commits):
        key = str(uuid.uuid4())
        first = second = None
        first_name, second_name = 'lookup_first_' + uuid.uuid4().hex, 'lookup_second_' + uuid.uuid4().hex
        previous_enabled = query('SELECT enabled FROM public.workspace_creation_controls WHERE id=true;')
        query('UPDATE public.workspace_creation_controls SET enabled=true WHERE id=true;')
        try:
            query(f"BEGIN; SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT public.create_workspace('Lookup Academy','academy','{key}'); COMMIT;")
            workspace_id = query(f"SELECT id FROM public.workspaces WHERE created_by='{MEERA}' AND creation_request_id='{key}';").splitlines()[-1]
            uuid.UUID(workspace_id)
            change = ('UPDATE public.workspace_creation_controls SET enabled=false WHERE id=true' if target == 'control' else
                      f"UPDATE public.workspaces SET status='suspended' WHERE id='{workspace_id}'" if target == 'workspace' else
                      f"UPDATE public.workspace_memberships SET status='suspended' WHERE workspace_id='{workspace_id}' AND user_id='{MEERA}'")
            lookup = f"SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT 'STATUS:' || (public.workspace_creation_key_for_workspace('{workspace_id}')->>'status')"
            first_sql, second_sql = (change, lookup) if change_first else (lookup, change)
            if not change_first:
                first_sql += f"; DO $test$ BEGIN IF public.workspace_creation_key_for_workspace('{workspace_id}')->>'request_key' IS DISTINCT FROM '{key}' THEN RAISE EXCEPTION 'FAIL: initial lookup not known'; END IF; END $test$"
            first, second = start_psql_session(), start_psql_session()
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
                    self.assertIn('STATUS:unknown' if commits else 'STATUS:known', output)
        finally:
            for process in (second, first):
                if process is not None:
                    close_psql_session(process)
            query(f"BEGIN; DELETE FROM public.workspace_memberships WHERE workspace_id IN (SELECT id FROM public.workspaces WHERE created_by='{MEERA}' AND creation_request_id='{key}'); DELETE FROM public.workspace_creation_receipts WHERE actor_id='{MEERA}' AND request_key='{key}'; DELETE FROM public.workspaces WHERE created_by='{MEERA}' AND creation_request_id='{key}'; UPDATE public.workspace_creation_controls SET enabled={'true' if previous_enabled == 't' else 'false'} WHERE id=true; COMMIT;")

    def test_membership_revocation_commit_before_lookup(self):
        self.exercise_access_race('membership', True, True)

    def test_membership_revocation_rollback_before_lookup(self):
        self.exercise_access_race('membership', True, False)

    def test_lookup_holds_membership_until_commit(self):
        self.exercise_access_race('membership', False, True)

    def test_workspace_suspend_commit_before_lookup(self):
        self.exercise_access_race('workspace', True, True)

    def test_workspace_suspend_rollback_before_lookup(self):
        self.exercise_access_race('workspace', True, False)

    def test_lookup_holds_workspace_until_commit(self):
        self.exercise_access_race('workspace', False, True)

    def test_control_disable_commit_before_lookup(self):
        self.exercise_access_race('control', True, True)

    def test_control_disable_rollback_before_lookup(self):
        self.exercise_access_race('control', True, False)

    def test_lookup_holds_control_until_commit(self):
        self.exercise_access_race('control', False, True)
