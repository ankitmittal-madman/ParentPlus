"""Deterministic scheduling authorization races on a disposable database."""
import unittest
import uuid

from tests.database.test_concurrent_authorization import (
    MEERA, query, start_psql_session, wait_for_session_marker,
    wait_for_blocking_relationship, close_psql_session,
)


class SchedulingAuthorizationRaceTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(self.restore_legacy_acl)
        legacy = self._testMethodName.startswith(('test_authenticated_course_', 'test_authenticated_batch_', 'test_atomic_setup_'))
        legacy_grants = '''GRANT EXECUTE ON FUNCTION public.create_course(uuid,text,uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION public.create_batch(uuid,uuid,text,uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION public.create_course_and_batch(uuid,text,text,uuid) TO authenticated;''' if legacy else ''
        self.workspace, self.membership, self.course, self.batch, request = (str(uuid.uuid4()) for _ in range(5))
        query(f"""
BEGIN;
UPDATE public.class_setup_controls SET enabled=true WHERE id=true;
-- Only historical behavior races temporarily restore grants in this disposable DB.
{legacy_grants}
INSERT INTO public.workspaces (id, name, type, created_by, creation_request_id)
VALUES ('{self.workspace}', 'Race academy', 'academy', '{MEERA}', '{request}');
INSERT INTO public.workspace_memberships (id, workspace_id, user_id, role, status)
VALUES ('{self.membership}', '{self.workspace}', '{MEERA}', 'coach', 'active');
INSERT INTO public.courses (id, workspace_id, name) VALUES ('{self.course}', '{self.workspace}', 'Music');
INSERT INTO public.batches (id, workspace_id, course_id, name)
VALUES ('{self.batch}', '{self.workspace}', '{self.course}', 'Original');
INSERT INTO public.batch_coach_assignments (workspace_id, batch_id, membership_id)
VALUES ('{self.workspace}', '{self.batch}', '{self.membership}');
COMMIT;
""")

    def restore_legacy_acl(self):
        query("""REVOKE EXECUTE ON FUNCTION public.create_course(uuid,text,uuid) FROM authenticated;
REVOKE EXECUTE ON FUNCTION public.create_batch(uuid,uuid,text,uuid) FROM authenticated;
REVOKE EXECUTE ON FUNCTION public.create_course_and_batch(uuid,text,text,uuid) FROM authenticated;
UPDATE public.class_setup_controls SET enabled=false WHERE id=true;""")

    def tearDown(self):
        query(f"""
BEGIN;
DELETE FROM public.class_setup_next_requests WHERE workspace_id = '{self.workspace}';
DELETE FROM public.class_setup_intent_history WHERE workspace_id = '{self.workspace}';
DELETE FROM public.class_setup_intents WHERE workspace_id = '{self.workspace}';
DELETE FROM public.class_setup_requests WHERE workspace_id = '{self.workspace}';
DELETE FROM public.batch_coach_mutation_requests WHERE workspace_id = '{self.workspace}';
DELETE FROM public.schedule_sessions WHERE workspace_id = '{self.workspace}';
DELETE FROM public.batch_coach_assignments WHERE workspace_id = '{self.workspace}';
DELETE FROM public.batches WHERE workspace_id = '{self.workspace}';
DELETE FROM public.courses WHERE workspace_id = '{self.workspace}';
DELETE FROM public.workspace_memberships WHERE workspace_id = '{self.workspace}';
DELETE FROM public.workspaces WHERE id = '{self.workspace}';
UPDATE public.class_setup_controls SET enabled=false WHERE id=true;
REVOKE EXECUTE ON FUNCTION public.create_course(uuid,text,uuid) FROM authenticated;
REVOKE EXECUTE ON FUNCTION public.create_batch(uuid,uuid,text,uuid) FROM authenticated;
REVOKE EXECUTE ON FUNCTION public.create_course_and_batch(uuid,text,text,uuid) FROM authenticated;
COMMIT;
""")

    def run_race(self, target, revocation_first):
        changes = {
            'workspace': f"UPDATE public.workspaces SET status = 'suspended' WHERE id = '{self.workspace}'",
            'membership': f"UPDATE public.workspace_memberships SET status = 'suspended' WHERE id = '{self.membership}'",
            'assignment': f"DELETE FROM public.batch_coach_assignments WHERE workspace_id = '{self.workspace}' AND batch_id = '{self.batch}' AND membership_id = '{self.membership}'",
        }
        revocation = changes[target]
        first_name = 'sched_first_' + uuid.uuid4().hex
        second_name = 'sched_second_' + uuid.uuid4().hex
        first, second = start_psql_session(), start_psql_session()
        check_and_write = f"""
SELECT set_config('request.jwt.claim.sub', '{MEERA}', true);
SELECT public.assert_schedule_write_access('{self.workspace}', '{self.batch}');
UPDATE public.batches SET name = 'Changed' WHERE id = '{self.batch}';
"""
        try:
            first.stdin.write(f"BEGIN; SET LOCAL lock_timeout = '10s'; SELECT set_config('application_name', '{first_name}', false);\n")
            first.stdin.write((revocation + ';\n') if revocation_first else check_and_write)
            first.stdin.write("SELECT 'FIRST_LOCKED';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_LOCKED'), 'first transaction did not reach its lock')

            second.stdin.write(f"BEGIN; SET LOCAL lock_timeout = '10s'; SELECT set_config('application_name', '{second_name}', false);\n")
            second.stdin.write(check_and_write if revocation_first else (revocation + ';\n'))
            second.stdin.write("COMMIT; SELECT 'SECOND_COMMITTED';\n")
            second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name, first_name), 'second transaction did not wait for the first')
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_COMMITTED'), 'first transaction did not commit')
            if revocation_first:
                second.stdin.close()
                second.stdin = None
                _, errors = second.communicate(timeout=15)
                self.assertNotEqual(second.returncode, 0, 'write after revocation succeeded')
                self.assertIn('Schedule access denied', errors)
                expected = 'Original'
            else:
                self.assertTrue(wait_for_session_marker(second, 'SECOND_COMMITTED'), 'revocation did not complete after the write')
                expected = 'Changed'
            self.assertEqual(query(f"SELECT name FROM public.batches WHERE id = '{self.batch}';"), expected)
        finally:
            close_psql_session(second)
            close_psql_session(first)

    def test_workspace_revoked_before_write(self):
        self.run_race('workspace', True)

    def test_workspace_revoked_after_write(self):
        self.run_race('workspace', False)

    def test_membership_revoked_before_write(self):
        self.run_race('membership', True)

    def test_membership_revoked_after_write(self):
        self.run_race('membership', False)

    def test_assignment_revoked_before_write(self):
        self.run_race('assignment', True)

    def test_assignment_revoked_after_write(self):
        self.run_race('assignment', False)

    def run_session_race(self, target, revocation_first):
        changes = {
            'workspace': f"UPDATE public.workspaces SET status = 'suspended' WHERE id = '{self.workspace}'",
            'membership': f"UPDATE public.workspace_memberships SET status = 'suspended' WHERE id = '{self.membership}'",
            'assignment': f"DELETE FROM public.batch_coach_assignments WHERE workspace_id = '{self.workspace}' AND batch_id = '{self.batch}' AND membership_id = '{self.membership}'",
        }
        request = str(uuid.uuid4())
        write = f"""
SELECT set_config('request.jwt.claim.sub', '{MEERA}', true);
SELECT public.create_private_session('{self.workspace}', '{self.batch}', '2026-11-03 11:30+00', '2026-11-03 12:30+00', '{request}');
"""
        first_name, second_name = 'session_first_' + uuid.uuid4().hex, 'session_second_' + uuid.uuid4().hex
        first, second = start_psql_session(), start_psql_session()
        try:
            first.stdin.write(f"BEGIN; SET LOCAL lock_timeout = '10s'; SELECT set_config('application_name', '{first_name}', false);\n")
            first.stdin.write(changes[target] + ';\n' if revocation_first else write)
            first.stdin.write("SELECT 'FIRST_LOCKED';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_LOCKED'))
            second.stdin.write(f"BEGIN; SET LOCAL lock_timeout = '10s'; SELECT set_config('application_name', '{second_name}', false);\n")
            second.stdin.write(write if revocation_first else changes[target] + ';\n')
            second.stdin.write("COMMIT; SELECT 'SECOND_COMMITTED';\n")
            second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name, first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_COMMITTED'))
            if revocation_first:
                second.stdin.close()
                second.stdin = None
                _, errors = second.communicate(timeout=15)
                self.assertNotEqual(second.returncode, 0)
                self.assertIn('Schedule access denied', errors)
            else:
                self.assertTrue(wait_for_session_marker(second, 'SECOND_COMMITTED'))
            self.assertEqual(query(f"SELECT count(*) FROM public.schedule_sessions WHERE creation_request_id = '{request}';"), '0' if revocation_first else '1')
        finally:
            close_psql_session(second)
            close_psql_session(first)

    def run_duplicate_race(self, changed):
        request = str(uuid.uuid4())
        first_name, second_name = 'retry_first_' + uuid.uuid4().hex, 'retry_second_' + uuid.uuid4().hex
        first, second = start_psql_session(), start_psql_session()
        def write(end):
            return f"SELECT public.create_private_session('{self.workspace}', '{self.batch}', '2026-11-03 11:30+00', '{end}', '{request}')"
        try:
            first.stdin.write(f"BEGIN; SET LOCAL lock_timeout = '10s'; SELECT set_config('application_name', '{first_name}', false); SELECT set_config('request.jwt.claim.sub', '{MEERA}', true); {write('2026-11-03 12:30+00')}; SELECT 'FIRST_LOCKED';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_LOCKED'))
            second.stdin.write(f"BEGIN; SET LOCAL lock_timeout = '10s'; SELECT set_config('application_name', '{second_name}', false); SELECT set_config('request.jwt.claim.sub', '{MEERA}', true);\n")
            if changed:
                second.stdin.write(write('2026-11-03 13:30+00') + "; COMMIT;\n")
            else:
                second.stdin.write(f"CREATE TEMP TABLE retry_result(id uuid); INSERT INTO retry_result {write('2026-11-03 12:30+00')}; SELECT 'MATCH:' || (id = (SELECT id FROM public.schedule_sessions WHERE creation_request_id = '{request}'))::text FROM retry_result; COMMIT; SELECT 'SECOND_COMMITTED';\n")
            second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name, first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_COMMITTED'))
            if changed:
                second.stdin.close()
                second.stdin = None
                _, errors = second.communicate(timeout=15)
                self.assertNotEqual(second.returncode, 0)
                self.assertIn('Session request conflicts', errors)
            else:
                self.assertTrue(wait_for_session_marker(second, 'MATCH:true'), 'retry did not return the original session')
                self.assertTrue(wait_for_session_marker(second, 'SECOND_COMMITTED'))
            self.assertEqual(query(f"SELECT count(*) FROM public.schedule_sessions WHERE creation_request_id = '{request}' AND ends_at = '2026-11-03 12:30+00';"), '1')
        finally:
            close_psql_session(second)
            close_psql_session(first)

    def test_session_workspace_revoked_before_write(self):
        self.run_session_race('workspace', True)

    def test_session_workspace_revoked_after_write(self):
        self.run_session_race('workspace', False)

    def test_session_membership_revoked_before_write(self):
        self.run_session_race('membership', True)

    def test_session_membership_revoked_after_write(self):
        self.run_session_race('membership', False)

    def test_session_assignment_revoked_before_write(self):
        self.run_session_race('assignment', True)

    def test_session_assignment_revoked_after_write(self):
        self.run_session_race('assignment', False)

    def test_simultaneous_identical_session_retries(self):
        self.run_duplicate_race(False)

    def test_simultaneous_changed_session_retry(self):
        self.run_duplicate_race(True)

    def run_zone_configuration_race(self, setup_first):
        query(f"UPDATE public.workspace_memberships SET role='owner' WHERE id='{self.membership}';")
        if not setup_first:
            query(f"UPDATE public.workspaces SET scheduling_time_zone='Asia/Kolkata' WHERE id='{self.workspace}';")
        request = str(uuid.uuid4())
        first_name, second_name = 'zone_first_' + uuid.uuid4().hex, 'zone_second_' + uuid.uuid4().hex
        first, second = start_psql_session(), start_psql_session()
        local_write = f"SELECT public.create_private_local_session('{self.workspace}', '{self.batch}', '2026-11-03 17:00', 60, '{request}');\n"
        configure = f"SELECT public.configure_private_workspace_zone('{self.workspace}', '{'Asia/Kolkata' if setup_first else 'Europe/London'}');\n"
        try:
            for process, name in ((first, first_name), (second, second_name)):
                process.stdin.write(f"BEGIN; SET LOCAL lock_timeout = '10s'; SELECT set_config('application_name', '{name}', false); SELECT set_config('request.jwt.claim.sub', '{MEERA}', true);\n")
            first.stdin.write(configure if setup_first else local_write)
            first.stdin.write("SELECT 'FIRST_LOCKED';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_LOCKED'))
            second.stdin.write(local_write if setup_first else configure)
            second.stdin.write("COMMIT; SELECT 'SECOND_COMMITTED';\n")
            second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name, first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_COMMITTED'))
            if setup_first:
                self.assertTrue(wait_for_session_marker(second, 'SECOND_COMMITTED'))
            else:
                second.stdin.close()
                second.stdin = None
                _, errors = second.communicate(timeout=15)
                self.assertNotEqual(second.returncode, 0)
                self.assertIn('Workspace time zone already configured', errors)
            self.assertEqual(query(f"SELECT count(*) FROM public.schedule_sessions WHERE creation_request_id='{request}' AND starts_at='2026-11-03 11:30+00';"), '1')
            self.assertEqual(query(f"SELECT scheduling_time_zone FROM public.workspaces WHERE id='{self.workspace}';"), 'Asia/Kolkata')
        finally:
            close_psql_session(second)
            close_psql_session(first)

    def test_zone_setup_commits_before_local_session(self):
        self.run_zone_configuration_race(True)

    def test_zone_change_rejected_after_local_session(self):
        self.run_zone_configuration_race(False)

    def run_coach_assignment_race(self, mode):
        manager = '22222222-2222-4222-8222-222222222222'
        query(f"""
DELETE FROM public.batch_coach_assignments WHERE workspace_id='{self.workspace}';
INSERT INTO public.workspace_memberships (workspace_id,user_id,role,status)
VALUES ('{self.workspace}', '{manager}', 'owner', 'active');
""")
        first_name, second_name = 'assign_first_' + uuid.uuid4().hex, 'assign_second_' + uuid.uuid4().hex
        first, second = start_psql_session(), start_psql_session()
        assign = f"SELECT public.assign_private_batch_coach('{self.workspace}', '{self.batch}', '{self.membership}', 'e1000000-0000-4000-8000-000000000001');\n"
        suspend = f"UPDATE public.workspace_memberships SET status='suspended' WHERE id='{self.membership}';\n"
        try:
            for process, name in ((first, first_name), (second, second_name)):
                process.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name', '{name}', false); SELECT set_config('request.jwt.claim.sub', '{manager}', true);\n")
            first.stdin.write(suspend if mode == 'suspend_first' else assign)
            first.stdin.write("SELECT 'FIRST_LOCKED';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_LOCKED'))
            second.stdin.write(assign if mode in ('suspend_first', 'duplicate') else suspend)
            second.stdin.write("COMMIT; SELECT 'SECOND_COMMITTED';\n")
            second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name, first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_COMMITTED'))
            if mode == 'suspend_first':
                second.stdin.close()
                second.stdin = None
                _, errors = second.communicate(timeout=15)
                self.assertNotEqual(second.returncode, 0)
                self.assertIn('Invalid coach assignment', errors)
                expected = '0'
            else:
                self.assertTrue(wait_for_session_marker(second, 'SECOND_COMMITTED'))
                expected = '1'
            self.assertEqual(query(f"SELECT count(*) FROM public.batch_coach_assignments WHERE workspace_id='{self.workspace}' AND batch_id='{self.batch}' AND membership_id='{self.membership}';"), expected)
            if mode != 'duplicate':
                self.assertEqual(query(f"SELECT status FROM public.workspace_memberships WHERE id='{self.membership}';"), 'suspended')
        finally:
            close_psql_session(second)
            close_psql_session(first)

    def test_coach_suspended_before_assignment(self):
        self.run_coach_assignment_race('suspend_first')

    def test_coach_suspended_after_assignment(self):
        self.run_coach_assignment_race('assign_first')

    def test_simultaneous_duplicate_coach_assignments(self):
        self.run_coach_assignment_race('duplicate')

    def run_coach_removal_race(self, other, removal_first):
        manager = '22222222-2222-4222-8222-222222222222'
        request = str(uuid.uuid4())
        query(f"INSERT INTO public.workspace_memberships (workspace_id,user_id,role,status) VALUES ('{self.workspace}', '{manager}', 'owner', 'active');")
        first_name, second_name = 'remove_first_' + uuid.uuid4().hex, 'remove_second_' + uuid.uuid4().hex
        first, second = start_psql_session(), start_psql_session()
        remove = f"SELECT set_config('request.jwt.claim.sub', '{manager}', true); SELECT public.remove_private_batch_coach('{self.workspace}', '{self.batch}', '{self.membership}', 'e2000000-0000-4000-8000-000000000002');\n"
        if other == 'session':
            action = f"SELECT set_config('request.jwt.claim.sub', '{MEERA}', true); SELECT public.create_private_session('{self.workspace}', '{self.batch}', '2026-11-03 11:30+00', '2026-11-03 12:30+00', '{request}');\n"
        else:
            action = f"SELECT set_config('request.jwt.claim.sub', '{manager}', true); SELECT public.assign_private_batch_coach('{self.workspace}', '{self.batch}', '{self.membership}', 'e1000000-0000-4000-8000-000000000001');\n"
        try:
            first.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name', '{first_name}', false);\n")
            first.stdin.write(remove if removal_first else action)
            first.stdin.write("SELECT 'FIRST_LOCKED';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_LOCKED'))
            second.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name', '{second_name}', false);\n")
            second.stdin.write(action if removal_first else remove)
            second.stdin.write("COMMIT; SELECT 'SECOND_COMMITTED';\n")
            second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name, first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_COMMITTED'))
            if other == 'session' and removal_first:
                second.stdin.close()
                second.stdin = None
                _, errors = second.communicate(timeout=15)
                self.assertNotEqual(second.returncode, 0)
                self.assertIn('Schedule access denied', errors)
            else:
                self.assertTrue(wait_for_session_marker(second, 'SECOND_COMMITTED'))
            expected_assignment = '1' if other == 'assign' and removal_first else '0'
            expected_session = '1' if other == 'session' and not removal_first else '0'
            self.assertEqual(query(f"SELECT count(*) FROM public.batch_coach_assignments WHERE workspace_id='{self.workspace}' AND batch_id='{self.batch}' AND membership_id='{self.membership}';"), expected_assignment)
            self.assertEqual(query(f"SELECT count(*) FROM public.schedule_sessions WHERE creation_request_id='{request}';"), expected_session)
        finally:
            close_psql_session(second)
            close_psql_session(first)

    def test_coach_removal_before_session_write(self):
        self.run_coach_removal_race('session', True)

    def test_coach_removal_after_session_write(self):
        self.run_coach_removal_race('session', False)

    def test_coach_removal_before_reassignment(self):
        self.run_coach_removal_race('assign', True)

    def test_coach_removal_after_reassignment(self):
        self.run_coach_removal_race('assign', False)

    def run_conflicting_coach_request_race(self, conflict):
        manager = '22222222-2222-4222-8222-222222222222'
        request = str(uuid.uuid4())
        other_batch = str(uuid.uuid4())
        query(f"""
INSERT INTO public.workspace_memberships (workspace_id,user_id,role,status) VALUES ('{self.workspace}', '{manager}', 'owner', 'active');
INSERT INTO public.batches (id,workspace_id,course_id,name) VALUES ('{other_batch}','{self.workspace}','{self.course}','Other');
""")
        first_name, second_name = 'conflict_first_' + uuid.uuid4().hex, 'conflict_second_' + uuid.uuid4().hex
        first, second = start_psql_session(), start_psql_session()
        first_call = f"SELECT public.assign_private_batch_coach('{self.workspace}','{self.batch}','{self.membership}','{request}');\n"
        second_call = (f"SELECT public.remove_private_batch_coach('{self.workspace}','{self.batch}','{self.membership}','{request}');\n" if conflict == 'action' else f"SELECT public.assign_private_batch_coach('{self.workspace}','{other_batch}','{self.membership}','{request}');\n")
        try:
            for process, name in ((first, first_name), (second, second_name)):
                process.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{name}',false); SELECT set_config('request.jwt.claim.sub','{manager}',true);\n")
            first.stdin.write(first_call + "SELECT 'FIRST_LOCKED';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_LOCKED'))
            second.stdin.write(second_call + "COMMIT;\n")
            second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name, first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_COMMITTED'))
            second.stdin.close()
            second.stdin = None
            _, errors = second.communicate(timeout=15)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn('request conflicts', errors)
            self.assertEqual(query(f"SELECT (SELECT count(*) FROM public.batch_coach_mutation_requests WHERE actor_id='{manager}' AND request_id='{request}') || ':' || (SELECT count(*) FROM public.batch_coach_assignments WHERE workspace_id='{self.workspace}' AND batch_id='{self.batch}') || ':' || (SELECT count(*) FROM public.batch_coach_assignments WHERE workspace_id='{self.workspace}' AND batch_id='{other_batch}');"), '1:1:0')
        finally:
            close_psql_session(second)
            close_psql_session(first)

    def test_concurrent_request_id_with_changed_action_is_rejected(self):
        self.run_conflicting_coach_request_race('action')

    def test_concurrent_request_id_with_changed_batch_is_rejected(self):
        self.run_conflicting_coach_request_race('batch')

    def test_private_class_journey_persists_across_transactions(self):
        from tests.database.test_concurrent_authorization import extract_labeled_id
        manager = '22222222-2222-4222-8222-222222222222'
        query(f"INSERT INTO public.workspace_memberships (workspace_id,user_id,role,status) VALUES ('{self.workspace}','{manager}','owner','active');")
        course_request, batch_request, assign_request, session_request, remove_request = (str(uuid.uuid4()) for _ in range(5))
        course = extract_labeled_id(query(f"""
BEGIN; SELECT set_config('request.jwt.claim.sub','{manager}',true);
SELECT 'ID:' || public.create_private_course('{self.workspace}','Dance','{course_request}')::text; COMMIT;
"""), 'ID:')
        batch = extract_labeled_id(query(f"""
BEGIN; SELECT set_config('request.jwt.claim.sub','{manager}',true);
SELECT 'ID:' || public.create_private_batch('{self.workspace}','{course}','Beginners','{batch_request}')::text; COMMIT;
"""), 'ID:')
        query(f"""
BEGIN; SELECT set_config('request.jwt.claim.sub','{manager}',true);
SELECT public.configure_private_workspace_zone('{self.workspace}','Asia/Kolkata');
SELECT public.assign_private_batch_coach('{self.workspace}','{batch}','{self.membership}','{assign_request}'); COMMIT;
""")
        session = extract_labeled_id(query(f"""
BEGIN; SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
SELECT 'ID:' || public.create_private_local_session('{self.workspace}','{batch}','2026-11-03 17:00',60,'{session_request}')::text; COMMIT;
"""), 'ID:')
        query(f"""
BEGIN; SELECT set_config('request.jwt.claim.sub','{manager}',true);
SELECT public.remove_private_batch_coach('{self.workspace}','{batch}','{self.membership}','{remove_request}'); COMMIT;
BEGIN; SELECT set_config('request.jwt.claim.sub','{manager}',true);
SELECT public.assign_private_batch_coach('{self.workspace}','{batch}','{self.membership}','{assign_request}'); COMMIT;
""")
        query(f"""
BEGIN; SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
DO $$ BEGIN BEGIN PERFORM public.create_private_local_session('{self.workspace}','{batch}','2026-11-10 17:00',60,gen_random_uuid()); RAISE EXCEPTION 'removed coach retained access'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$; COMMIT;
""")
        out = query(f"SELECT (SELECT count(*) FROM public.schedule_sessions WHERE id='{session}' AND starts_at='2026-11-03 11:30+00') || ':' || (SELECT count(*) FROM public.batch_coach_assignments WHERE workspace_id='{self.workspace}' AND batch_id='{batch}');")
        self.assertEqual(out, '1:0')

    def run_authenticated_course_permission_race(self, target, revocation_first):
        manager = '22222222-2222-4222-8222-222222222222'
        request = str(uuid.uuid4())
        query(f"INSERT INTO public.workspace_memberships (workspace_id,user_id,role,status) VALUES ('{self.workspace}', '{manager}', 'owner', 'active');")
        update = (f"UPDATE public.workspaces SET status='suspended' WHERE id='{self.workspace}';\n" if target == 'workspace' else f"UPDATE public.workspace_memberships SET status='suspended' WHERE workspace_id='{self.workspace}' AND user_id='{manager}';\n")
        create = f"SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{manager}',true); SELECT public.create_course('{self.workspace}','Dance','{request}');\n"
        first_name, second_name = 'course_first_' + uuid.uuid4().hex, 'course_second_' + uuid.uuid4().hex
        first, second = start_psql_session(), start_psql_session()
        try:
            first.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{first_name}',false);\n")
            first.stdin.write(update if revocation_first else create)
            first.stdin.write("SELECT 'FIRST_LOCKED';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_LOCKED'))
            second.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{second_name}',false);\n")
            second.stdin.write(create if revocation_first else update)
            second.stdin.write("COMMIT; SELECT 'SECOND_COMMITTED';\n")
            second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name, first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_COMMITTED'))
            if revocation_first:
                second.stdin.close(); second.stdin = None
                _, errors = second.communicate(timeout=15)
                self.assertNotEqual(second.returncode, 0)
                self.assertIn('Workspace access denied', errors)
            else:
                self.assertTrue(wait_for_session_marker(second, 'SECOND_COMMITTED'))
            self.assertEqual(query(f"SELECT count(*) FROM public.courses WHERE workspace_id='{self.workspace}' AND creation_request_id='{request}';"), '0' if revocation_first else '1')
        finally:
            close_psql_session(second); close_psql_session(first)

    def run_authenticated_course_retry_race(self, changed):
        manager = '22222222-2222-4222-8222-222222222222'
        request = str(uuid.uuid4())
        query(f"INSERT INTO public.workspace_memberships (workspace_id,user_id,role,status) VALUES ('{self.workspace}', '{manager}', 'owner', 'active');")
        first_name, second_name = 'course_retry_first_' + uuid.uuid4().hex, 'course_retry_second_' + uuid.uuid4().hex
        first, second = start_psql_session(), start_psql_session()
        try:
            for process, name in ((first, first_name), (second, second_name)):
                process.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{name}',false); SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{manager}',true);\n")
            first.stdin.write(f"SELECT public.create_course('{self.workspace}','Dance','{request}'); SELECT 'FIRST_LOCKED';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_LOCKED'))
            second.stdin.write(f"SELECT 'RESULT:' || public.create_course('{self.workspace}','{'Painting' if changed else 'Dance'}','{request}')::text; COMMIT; SELECT 'SECOND_COMMITTED';\n")
            second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name, first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_COMMITTED'))
            if changed:
                second.stdin.close(); second.stdin = None
                _, errors = second.communicate(timeout=15)
                self.assertNotEqual(second.returncode, 0)
                self.assertIn('Course request conflicts', errors)
            else:
                course_id = query(f"SELECT id FROM public.courses WHERE workspace_id='{self.workspace}' AND creation_request_id='{request}';")
                self.assertTrue(wait_for_session_marker(second, 'RESULT:' + course_id))
                self.assertTrue(wait_for_session_marker(second, 'SECOND_COMMITTED'))
            self.assertEqual(query(f"SELECT count(*) FROM public.courses WHERE workspace_id='{self.workspace}' AND creation_request_id='{request}' AND name='Dance';"), '1')
        finally:
            close_psql_session(second); close_psql_session(first)

    def test_authenticated_course_workspace_suspended_before_write(self):
        self.run_authenticated_course_permission_race('workspace', True)

    def test_authenticated_course_workspace_suspended_after_write(self):
        self.run_authenticated_course_permission_race('workspace', False)

    def test_authenticated_course_manager_suspended_before_write(self):
        self.run_authenticated_course_permission_race('membership', True)

    def test_authenticated_course_manager_suspended_after_write(self):
        self.run_authenticated_course_permission_race('membership', False)

    def test_authenticated_course_concurrent_identical_retry(self):
        self.run_authenticated_course_retry_race(False)

    def test_authenticated_course_concurrent_changed_retry(self):
        self.run_authenticated_course_retry_race(True)

    def run_authenticated_batch_permission_race(self, target, change_first):
        manager = '22222222-2222-4222-8222-222222222222'
        request = str(uuid.uuid4())
        course = self.course if target != 'course' else str(uuid.uuid4())
        query(f"INSERT INTO public.workspace_memberships (workspace_id,user_id,role,status) VALUES ('{self.workspace}', '{manager}', 'owner', 'active');")
        if target == 'course':
            query(f"INSERT INTO public.courses (id,workspace_id,name) VALUES ('{course}','{self.workspace}','Temporary');")
        change = {
            'workspace': f"UPDATE public.workspaces SET status='suspended' WHERE id='{self.workspace}';\n",
            'membership': f"UPDATE public.workspace_memberships SET status='suspended' WHERE workspace_id='{self.workspace}' AND user_id='{manager}';\n",
            'course': f"DELETE FROM public.courses WHERE id='{course}';\n",
        }[target]
        create = f"SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{manager}',true); SELECT public.create_batch('{self.workspace}','{course}','Beginners','{request}');\n"
        first_name, second_name = 'batch_first_' + uuid.uuid4().hex, 'batch_second_' + uuid.uuid4().hex
        first, second = start_psql_session(), start_psql_session()
        try:
            first.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{first_name}',false);\n")
            first.stdin.write(change if change_first else create)
            first.stdin.write("SELECT 'FIRST_LOCKED';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_LOCKED'))
            second.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{second_name}',false);\n")
            second.stdin.write(create if change_first else change)
            second.stdin.write("COMMIT; SELECT 'SECOND_COMMITTED';\n"); second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name, first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_COMMITTED'))
            if change_first or target == 'course':
                second.stdin.close(); second.stdin = None
                _, errors = second.communicate(timeout=15)
                self.assertNotEqual(second.returncode, 0)
                self.assertIn(('Invalid batch details' if target == 'course' else 'Workspace access denied') if change_first else 'foreign key constraint', errors)
            else:
                self.assertTrue(wait_for_session_marker(second, 'SECOND_COMMITTED'))
            self.assertEqual(query(f"SELECT count(*) FROM public.batches WHERE workspace_id='{self.workspace}' AND creation_request_id='{request}';"), '0' if change_first else '1')
        finally:
            close_psql_session(second); close_psql_session(first)

    def run_authenticated_batch_retry_race(self, changed):
        manager = '22222222-2222-4222-8222-222222222222'
        request = str(uuid.uuid4())
        query(f"INSERT INTO public.workspace_memberships (workspace_id,user_id,role,status) VALUES ('{self.workspace}', '{manager}', 'owner', 'active');")
        first_name, second_name = 'batch_retry_first_' + uuid.uuid4().hex, 'batch_retry_second_' + uuid.uuid4().hex
        first, second = start_psql_session(), start_psql_session()
        try:
            for process, name in ((first, first_name), (second, second_name)):
                process.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{name}',false); SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{manager}',true);\n")
            first.stdin.write(f"SELECT public.create_batch('{self.workspace}','{self.course}','Beginners','{request}'); SELECT 'FIRST_LOCKED';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_LOCKED'))
            second.stdin.write(f"SELECT 'RESULT:' || public.create_batch('{self.workspace}','{self.course}','{'Advanced' if changed else 'Beginners'}','{request}')::text; COMMIT; SELECT 'SECOND_COMMITTED';\n"); second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name, first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_COMMITTED'))
            if changed:
                second.stdin.close(); second.stdin = None
                _, errors = second.communicate(timeout=15)
                self.assertNotEqual(second.returncode, 0)
                self.assertIn('Batch request conflicts', errors)
            else:
                batch_id = query(f"SELECT id FROM public.batches WHERE workspace_id='{self.workspace}' AND creation_request_id='{request}';")
                self.assertTrue(wait_for_session_marker(second, 'RESULT:' + batch_id))
                self.assertTrue(wait_for_session_marker(second, 'SECOND_COMMITTED'))
            self.assertEqual(query(f"SELECT count(*) FROM public.batches WHERE workspace_id='{self.workspace}' AND creation_request_id='{request}' AND name='Beginners';"), '1')
        finally:
            close_psql_session(second); close_psql_session(first)

    def test_authenticated_batch_workspace_suspended_before_write(self):
        self.run_authenticated_batch_permission_race('workspace', True)

    def test_authenticated_batch_workspace_suspended_after_write(self):
        self.run_authenticated_batch_permission_race('workspace', False)

    def test_authenticated_batch_manager_suspended_before_write(self):
        self.run_authenticated_batch_permission_race('membership', True)

    def test_authenticated_batch_manager_suspended_after_write(self):
        self.run_authenticated_batch_permission_race('membership', False)

    def test_authenticated_batch_course_deleted_before_write(self):
        self.run_authenticated_batch_permission_race('course', True)

    def test_authenticated_batch_course_deleted_after_write(self):
        self.run_authenticated_batch_permission_race('course', False)

    def test_authenticated_batch_concurrent_identical_retry(self):
        self.run_authenticated_batch_retry_race(False)

    def test_authenticated_batch_concurrent_changed_retry(self):
        self.run_authenticated_batch_retry_race(True)

    def run_atomic_setup_permission_race(self, target, revocation_first):
        manager = '22222222-2222-4222-8222-222222222222'
        request = str(uuid.uuid4())
        query(f"INSERT INTO public.workspace_memberships (workspace_id,user_id,role,status) VALUES ('{self.workspace}','{manager}','owner','active');")
        revoke = (f"UPDATE public.workspaces SET status='suspended' WHERE id='{self.workspace}';\n" if target == 'workspace' else f"UPDATE public.workspace_memberships SET status='suspended' WHERE workspace_id='{self.workspace}' AND user_id='{manager}';\n")
        create = f"SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{manager}',true); SELECT * FROM public.create_course_and_batch('{self.workspace}','Dance','Beginners','{request}');\n"
        first_name,second_name='setup_first_'+uuid.uuid4().hex,'setup_second_'+uuid.uuid4().hex
        first,second=start_psql_session(),start_psql_session()
        try:
            first.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{first_name}',false);\n")
            first.stdin.write(revoke if revocation_first else create); first.stdin.write("SELECT 'FIRST_LOCKED';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'FIRST_LOCKED'))
            second.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{second_name}',false);\n")
            second.stdin.write(create if revocation_first else revoke); second.stdin.write("COMMIT; SELECT 'SECOND_COMMITTED';\n"); second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name,first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'FIRST_COMMITTED'))
            if revocation_first:
                second.stdin.close(); second.stdin=None
                _,errors=second.communicate(timeout=15)
                self.assertNotEqual(second.returncode,0); self.assertIn('Workspace access denied',errors)
            else:
                self.assertTrue(wait_for_session_marker(second,'SECOND_COMMITTED'))
            self.assertEqual(query(f"SELECT (SELECT count(*) FROM public.class_setup_requests WHERE actor_id='{manager}' AND request_id='{request}') || ':' || (SELECT count(*) FROM public.courses WHERE workspace_id='{self.workspace}' AND name='Dance') || ':' || (SELECT count(*) FROM public.batches WHERE workspace_id='{self.workspace}' AND name='Beginners');"), '0:0:0' if revocation_first else '1:1:1')
        finally:
            close_psql_session(second); close_psql_session(first)

    def run_atomic_setup_retry_race(self, changed):
        manager='22222222-2222-4222-8222-222222222222'; request=str(uuid.uuid4())
        query(f"INSERT INTO public.workspace_memberships (workspace_id,user_id,role,status) VALUES ('{self.workspace}','{manager}','owner','active');")
        first_name,second_name='setup_retry_first_'+uuid.uuid4().hex,'setup_retry_second_'+uuid.uuid4().hex
        first,second=start_psql_session(),start_psql_session()
        try:
            for process,name in ((first,first_name),(second,second_name)):
                process.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{name}',false); SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{manager}',true);\n")
            first.stdin.write(f"SELECT * FROM public.create_course_and_batch('{self.workspace}','Dance','Beginners','{request}'); SELECT 'FIRST_LOCKED';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'FIRST_LOCKED'))
            second.stdin.write(f"SELECT 'RESULT:' || course_id::text || ':' || batch_id::text FROM public.create_course_and_batch('{self.workspace}','Dance','{'Advanced' if changed else 'Beginners'}','{request}'); COMMIT; SELECT 'SECOND_COMMITTED';\n"); second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name,first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'FIRST_COMMITTED'))
            if changed:
                second.stdin.close(); second.stdin=None
                _,errors=second.communicate(timeout=15)
                self.assertNotEqual(second.returncode,0); self.assertIn('Class setup request conflicts',errors)
            else:
                ids=query(f"SELECT course_id::text || ':' || batch_id::text FROM public.class_setup_requests WHERE actor_id='{manager}' AND request_id='{request}';")
                self.assertTrue(wait_for_session_marker(second,'RESULT:'+ids)); self.assertTrue(wait_for_session_marker(second,'SECOND_COMMITTED'))
            self.assertEqual(query(f"SELECT (SELECT count(*) FROM public.class_setup_requests WHERE actor_id='{manager}' AND request_id='{request}') || ':' || (SELECT count(*) FROM public.courses WHERE workspace_id='{self.workspace}' AND name='Dance') || ':' || (SELECT count(*) FROM public.batches WHERE workspace_id='{self.workspace}' AND name='Beginners');"),'1:1:1')
        finally:
            close_psql_session(second); close_psql_session(first)

    def test_atomic_setup_workspace_suspended_before_write(self):
        self.run_atomic_setup_permission_race('workspace',True)

    def test_atomic_setup_workspace_suspended_after_write(self):
        self.run_atomic_setup_permission_race('workspace',False)

    def test_atomic_setup_manager_suspended_before_write(self):
        self.run_atomic_setup_permission_race('membership',True)

    def test_atomic_setup_manager_suspended_after_write(self):
        self.run_atomic_setup_permission_race('membership',False)

    def test_atomic_setup_concurrent_identical_retry(self):
        self.run_atomic_setup_retry_race(False)

    def test_atomic_setup_concurrent_changed_retry(self):
        self.run_atomic_setup_retry_race(True)

    def run_atomic_setup_switch_race(self, disable_first):
        manager='22222222-2222-4222-8222-222222222222'; request=str(uuid.uuid4())
        query(f"INSERT INTO public.workspace_memberships (workspace_id,user_id,role,status) VALUES ('{self.workspace}','{manager}','owner','active');")
        first_name,second_name='gate_first_'+uuid.uuid4().hex,'gate_second_'+uuid.uuid4().hex
        first,second=start_psql_session(),start_psql_session()
        disable="UPDATE public.class_setup_controls SET enabled=false WHERE id=true;\n"
        create=f"SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{manager}',true); SELECT * FROM public.create_course_and_batch('{self.workspace}','Dance','Beginners','{request}');\n"
        try:
            first.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{first_name}',false);\n")
            first.stdin.write(disable if disable_first else create); first.stdin.write("SELECT 'FIRST_LOCKED';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'FIRST_LOCKED'))
            second.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{second_name}',false);\n")
            second.stdin.write(create if disable_first else disable); second.stdin.write("COMMIT; SELECT 'SECOND_COMMITTED';\n"); second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name,first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'FIRST_COMMITTED'))
            if disable_first:
                second.stdin.close(); second.stdin=None
                _,errors=second.communicate(timeout=15)
                self.assertNotEqual(second.returncode,0); self.assertIn('Class setup unavailable',errors)
            else:
                self.assertTrue(wait_for_session_marker(second,'SECOND_COMMITTED'))
            self.assertEqual(query(f"SELECT count(*) FROM public.class_setup_requests WHERE actor_id='{manager}' AND request_id='{request}';"), '0' if disable_first else '1')
            self.assertEqual(query('SELECT enabled FROM public.class_setup_controls WHERE id=true;'), 'f')
        finally:
            close_psql_session(second); close_psql_session(first)

    def test_atomic_setup_database_disabled_before_write(self):
        self.run_atomic_setup_switch_race(True)

    def test_atomic_setup_database_disabled_after_write(self):
        self.run_atomic_setup_switch_race(False)

    def run_reservation_race(self, changed):
        query(f"UPDATE public.workspace_memberships SET role='owner' WHERE id='{self.membership}';")
        first_name, second_name = 'reserve_first_'+uuid.uuid4().hex, 'reserve_second_'+uuid.uuid4().hex
        first, second = start_psql_session(), start_psql_session()
        try:
            for process, name in ((first,first_name),(second,second_name)):
                process.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{name}',false); SELECT set_config('request.jwt.claim.sub','{MEERA}',true);\n")
            first.stdin.write(f"SELECT 'INTENT:' || public.reserve_private_class_setup('{self.workspace}','Dance','Beginners'); SELECT 'FIRST_LOCKED';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_LOCKED'))
            second_batch = 'Advanced' if changed else 'Beginners'
            second.stdin.write(f"SELECT 'INTENT:' || public.reserve_private_class_setup('{self.workspace}','Dance','{second_batch}'); COMMIT; SELECT 'SECOND_COMMITTED';\n"); second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name,first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'FIRST_COMMITTED'))
            if changed:
                second.stdin.close(); second.stdin=None
                _, errors=second.communicate(timeout=15)
                self.assertNotEqual(second.returncode,0)
                self.assertIn('Resolve the existing class setup first', errors)
            else:
                intent=query(f"SELECT id FROM public.class_setup_intents WHERE workspace_id='{self.workspace}';")
                self.assertTrue(wait_for_session_marker(second,'INTENT:'+intent))
                self.assertTrue(wait_for_session_marker(second,'SECOND_COMMITTED'))
            self.assertEqual(query(f"SELECT count(*) FROM public.class_setup_intents WHERE workspace_id='{self.workspace}';"),'1')
        finally:
            close_psql_session(second); close_psql_session(first)

    def test_class_setup_reservation_concurrent_matching_requests(self):
        self.run_reservation_race(False)

    def test_class_setup_reservation_concurrent_changed_requests(self):
        self.run_reservation_race(True)

    def test_reserved_setup_concurrent_completion_returns_same_records(self):
        query(f"UPDATE public.workspace_memberships SET role='owner' WHERE id='{self.membership}';")
        intent_output=query(f"BEGIN; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT 'INTENT:' || public.reserve_private_class_setup('{self.workspace}','Dance','Beginners'); COMMIT;")
        intent=next(line.removeprefix('INTENT:') for line in intent_output.splitlines() if line.startswith('INTENT:'))
        first_name, second_name='complete_first_'+uuid.uuid4().hex,'complete_second_'+uuid.uuid4().hex
        first, second=start_psql_session(),start_psql_session()
        try:
            for process,name in ((first,first_name),(second,second_name)):
                process.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{name}',false); SELECT set_config('request.jwt.claim.sub','{MEERA}',true);\n")
            first.stdin.write(f"SELECT 'RESULT:' || course_id || ':' || batch_id FROM public.complete_private_class_setup('{self.workspace}','{intent}'); SELECT 'FIRST_LOCKED';\n"); first.stdin.flush()
            ready = wait_for_session_marker(first,'FIRST_LOCKED')
            if not ready and first.poll() is not None:
                self.fail(first.stderr.read())
            self.assertTrue(ready)
            second.stdin.write(f"SELECT 'RESULT:' || course_id || ':' || batch_id FROM public.complete_private_class_setup('{self.workspace}','{intent}'); COMMIT; SELECT 'SECOND_COMMITTED';\n"); second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name,first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'FIRST_COMMITTED'))
            ids=query(f"SELECT completed_course_id || ':' || completed_batch_id FROM public.class_setup_intents WHERE id='{intent}';")
            self.assertTrue(wait_for_session_marker(second,'RESULT:'+ids))
            self.assertTrue(wait_for_session_marker(second,'SECOND_COMMITTED'))
            self.assertEqual(query(f"SELECT (SELECT count(*) FROM public.courses WHERE workspace_id='{self.workspace}' AND name='Dance') || ':' || (SELECT count(*) FROM public.batches WHERE workspace_id='{self.workspace}' AND name='Beginners') || ':' || (SELECT count(*) FROM public.class_setup_intents WHERE id='{intent}' AND completed_course_id IS NOT NULL);"),'1:1:1')
        finally:
            close_psql_session(second); close_psql_session(first)

    def test_class_setup_status_waits_for_inflight_completion(self):
        query(f"UPDATE public.workspace_memberships SET role='owner' WHERE id='{self.membership}';")
        output=query(f"BEGIN; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT 'INTENT:' || public.reserve_private_class_setup('{self.workspace}','Dance','Beginners'); COMMIT;")
        intent=next(line.removeprefix('INTENT:') for line in output.splitlines() if line.startswith('INTENT:'))
        first_name,second_name='status_complete_'+uuid.uuid4().hex,'status_read_'+uuid.uuid4().hex
        first,second=start_psql_session(),start_psql_session()
        try:
            for proc,name in ((first,first_name),(second,second_name)):
                proc.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{name}',false); SELECT set_config('request.jwt.claim.sub','{MEERA}',true);\n")
            first.stdin.write(f"SELECT * FROM public.complete_private_class_setup('{self.workspace}','{intent}'); SELECT 'FIRST_LOCKED';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'FIRST_LOCKED'))
            second.stdin.write(f"SELECT 'STATUS:' || state FROM public.private_class_setup_status('{self.workspace}'); COMMIT; SELECT 'SECOND_COMMITTED';\n"); second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name,first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'FIRST_COMMITTED'))
            self.assertTrue(wait_for_session_marker(second,'STATUS:completed'))
            self.assertTrue(wait_for_session_marker(second,'SECOND_COMMITTED'))
        finally:
            close_psql_session(second); close_psql_session(first)

    def test_class_setup_status_missing_row_is_unknown_during_inflight_reservation(self):
        query(f"UPDATE public.workspace_memberships SET role='owner' WHERE id='{self.membership}';")
        first=start_psql_session()
        try:
            first.stdin.write(f"BEGIN; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT public.reserve_private_class_setup('{self.workspace}','Dance','Beginners'); SELECT 'FIRST_LOCKED';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'FIRST_LOCKED'))
            status=query(f"BEGIN; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT 'STATUS:' || state FROM public.private_class_setup_status('{self.workspace}'); COMMIT;")
            self.assertIn('STATUS:unknown',status.splitlines())
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'FIRST_COMMITTED'))
            status=query(f"BEGIN; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT 'STATUS:' || state FROM public.private_class_setup_status('{self.workspace}'); COMMIT;")
            self.assertIn('STATUS:pending',status.splitlines())
        finally:
            close_psql_session(first)

    def test_class_setup_acknowledgement_waits_for_completion(self):
        query(f"UPDATE public.workspace_memberships SET role='owner' WHERE id='{self.membership}';")
        output=query(f"BEGIN; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT 'INTENT:' || public.reserve_private_class_setup('{self.workspace}','Dance','Beginners'); COMMIT;")
        intent=next(line.removeprefix('INTENT:') for line in output.splitlines() if line.startswith('INTENT:'))
        first_name,second_name='ack_create_'+uuid.uuid4().hex,'ack_wait_'+uuid.uuid4().hex
        first,second=start_psql_session(),start_psql_session()
        try:
            for proc,name in ((first,first_name),(second,second_name)):
                proc.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{name}',false); SELECT set_config('request.jwt.claim.sub','{MEERA}',true);\n")
            first.stdin.write(f"SELECT * FROM public.complete_private_class_setup('{self.workspace}','{intent}'); SELECT 'FIRST_LOCKED';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'FIRST_LOCKED'))
            second.stdin.write(f"SELECT 'ACK:' || public.acknowledge_private_class_setup('{self.workspace}','{intent}'); COMMIT; SELECT 'SECOND_COMMITTED';\n"); second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name,first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'FIRST_COMMITTED'))
            self.assertTrue(wait_for_session_marker(second,'ACK:true'))
            self.assertTrue(wait_for_session_marker(second,'SECOND_COMMITTED'))
            self.assertEqual(query(f"SELECT acknowledged AND completed_course_id IS NOT NULL FROM public.class_setup_intents WHERE id='{intent}';"),'t')
        finally:
            close_psql_session(second); close_psql_session(first)

    def run_ack_permission_race(self, target, revoke_first):
        query(f"UPDATE public.workspace_memberships SET role='owner' WHERE id='{self.membership}';")
        output=query(f"BEGIN; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT 'INTENT:' || public.reserve_private_class_setup('{self.workspace}','Dance','Beginners'); COMMIT;")
        intent=next(line.removeprefix('INTENT:') for line in output.splitlines() if line.startswith('INTENT:'))
        query(f"BEGIN; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT * FROM public.complete_private_class_setup('{self.workspace}','{intent}'); COMMIT;")
        changes={
            'workspace': f"UPDATE public.workspaces SET status='suspended' WHERE id='{self.workspace}';\n",
            'membership': f"UPDATE public.workspace_memberships SET status='suspended' WHERE id='{self.membership}';\n",
            'control': "UPDATE public.class_setup_controls SET enabled=false WHERE id=true;\n",
        }
        revoke=changes[target]
        acknowledge=f"SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT public.acknowledge_private_class_setup('{self.workspace}','{intent}');\n"
        first_name,second_name='ack_first_'+uuid.uuid4().hex,'ack_second_'+uuid.uuid4().hex
        first,second=start_psql_session(),start_psql_session()
        try:
            first.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{first_name}',false);\n")
            first.stdin.write(revoke if revoke_first else acknowledge); first.stdin.write("SELECT 'FIRST_LOCKED';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'FIRST_LOCKED'))
            second.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{second_name}',false);\n")
            second.stdin.write(acknowledge if revoke_first else revoke); second.stdin.write("COMMIT; SELECT 'SECOND_COMMITTED';\n"); second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name,first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'FIRST_COMMITTED'))
            if revoke_first:
                second.stdin.close(); second.stdin=None
                _,errors=second.communicate(timeout=15)
                self.assertNotEqual(second.returncode,0)
                self.assertIn('Class setup unavailable' if target=='control' else 'Workspace access denied',errors)
            else:
                self.assertTrue(wait_for_session_marker(second,'SECOND_COMMITTED'))
            self.assertEqual(query(f"SELECT acknowledged FROM public.class_setup_intents WHERE id='{intent}';"),'f' if revoke_first else 't')
        finally:
            close_psql_session(second); close_psql_session(first)

    def test_ack_workspace_suspended_before_acknowledgement(self):
        self.run_ack_permission_race('workspace',True)

    def test_ack_workspace_suspended_after_acknowledgement(self):
        self.run_ack_permission_race('workspace',False)

    def test_ack_membership_suspended_before_acknowledgement(self):
        self.run_ack_permission_race('membership',True)

    def test_ack_membership_suspended_after_acknowledgement(self):
        self.run_ack_permission_race('membership',False)

    def test_ack_control_disabled_before_acknowledgement(self):
        self.run_ack_permission_race('control',True)

    def test_ack_control_disabled_after_acknowledgement(self):
        self.run_ack_permission_race('control',False)

    def run_next_class_race(self, mode):
        query(f"UPDATE public.workspace_memberships SET role='owner' WHERE id='{self.membership}';")
        output=query(f"BEGIN; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT 'INTENT:' || public.reserve_private_class_setup('{self.workspace}','Dance','Beginners'); COMMIT;")
        prior=next(line.removeprefix('INTENT:') for line in output.splitlines() if line.startswith('INTENT:'))
        query(f"BEGIN; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT * FROM public.complete_private_class_setup('{self.workspace}','{prior}'); SELECT public.acknowledge_private_class_setup('{self.workspace}','{prior}'); COMMIT;")
        first_name,second_name='next_first_'+uuid.uuid4().hex,'next_second_'+uuid.uuid4().hex
        token,other_token=str(uuid.uuid4()),str(uuid.uuid4())
        first,second=start_psql_session(),start_psql_session()
        try:
            for proc,name in ((first,first_name),(second,second_name)):
                proc.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{name}',false); SELECT set_config('request.jwt.claim.sub','{MEERA}',true);\n")
            first.stdin.write(f"SELECT public.advance_private_class_setup('{self.workspace}','{prior}','{token}','Dance','Beginners'); SELECT 'FIRST_LOCKED';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'FIRST_LOCKED'))
            if mode=='legacy':
                operation=f"SELECT public.reserve_private_class_setup('{self.workspace}','Dance','Beginners');"
            else:
                second_token=token if mode=='same' else other_token
                operation=f"SELECT 'NEXT:' || public.advance_private_class_setup('{self.workspace}','{prior}','{second_token}','Dance','Beginners');"
            second.stdin.write(operation+" COMMIT; SELECT 'SECOND_COMMITTED';\n"); second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name,first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'FIRST_COMMITTED'))
            if mode=='same':
                next_id=query(f"SELECT next_intent_id FROM public.class_setup_next_requests WHERE request_id='{token}';")
                self.assertTrue(wait_for_session_marker(second,'NEXT:'+next_id)); self.assertTrue(wait_for_session_marker(second,'SECOND_COMMITTED'))
            else:
                second.stdin.close(); second.stdin=None
                _,errors=second.communicate(timeout=15)
                self.assertNotEqual(second.returncode,0)
                self.assertIn('Use the next class setup request' if mode=='legacy' else 'Resolve the existing class setup first',errors)
            self.assertEqual(query(f"SELECT (SELECT count(*) FROM public.class_setup_intent_history WHERE workspace_id='{self.workspace}') || ':' || (SELECT count(*) FROM public.class_setup_next_requests WHERE workspace_id='{self.workspace}') || ':' || (SELECT count(*) FROM public.class_setup_intents WHERE workspace_id='{self.workspace}');"),'1:1:1')
        finally:
            close_psql_session(second); close_psql_session(first)

    def test_next_class_concurrent_same_token_returns_same_intent(self):
        self.run_next_class_race('same')

    def test_next_class_concurrent_different_tokens_cannot_fork_prior(self):
        self.run_next_class_race('different')

    def test_next_class_delayed_legacy_reservation_cannot_rebind(self):
        self.run_next_class_race('legacy')

    def run_current_recovery_advance_race(self, advance_first):
        query(f"UPDATE public.workspace_memberships SET role='owner' WHERE id='{self.membership}';")
        output=query(f"BEGIN; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT 'INTENT:' || public.reserve_private_class_setup('{self.workspace}','Dance','Beginners'); COMMIT;")
        prior=next(line.removeprefix('INTENT:') for line in output.splitlines() if line.startswith('INTENT:'))
        query(f"BEGIN; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT * FROM public.complete_private_class_setup('{self.workspace}','{prior}'); SELECT public.acknowledge_private_class_setup('{self.workspace}','{prior}'); COMMIT;")
        first_name,second_name='recover_first_'+uuid.uuid4().hex,'recover_second_'+uuid.uuid4().hex
        token=str(uuid.uuid4());first,second=start_psql_session(),start_psql_session()
        advance=f"SELECT 'NEXT:' || public.advance_private_class_setup('{self.workspace}','{prior}','{token}','Art','Morning');\n"
        recover=f"SELECT 'CURRENT:' || intent_id FROM public.recover_private_current_class_setup('{self.workspace}');\n"
        try:
            for proc,name in ((first,first_name),(second,second_name)):
                proc.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{name}',false); SELECT set_config('request.jwt.claim.sub','{MEERA}',true);\n")
            first.stdin.write(advance if advance_first else recover);first.stdin.write("SELECT 'FIRST_LOCKED';\n");first.stdin.flush()
            if not advance_first:
                self.assertTrue(wait_for_session_marker(first,'CURRENT:'+prior))
            self.assertTrue(wait_for_session_marker(first,'FIRST_LOCKED'))
            second.stdin.write(recover if advance_first else advance);second.stdin.write("COMMIT; SELECT 'SECOND_COMMITTED';\n");second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name,first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n");first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'FIRST_COMMITTED'))
            next_id=query(f"SELECT next_intent_id FROM public.class_setup_next_requests WHERE request_id='{token}';") if advance_first else None
            if advance_first:
                self.assertTrue(wait_for_session_marker(second,'CURRENT:'+next_id))
            self.assertTrue(wait_for_session_marker(second,'SECOND_COMMITTED'))
            self.assertEqual(query(f"SELECT count(*) FROM public.class_setup_next_requests WHERE workspace_id='{self.workspace}' AND request_id='{token}';"),'1')
        finally:
            close_psql_session(second);close_psql_session(first)

    def test_current_recovery_waits_for_advance(self):
        self.run_current_recovery_advance_race(True)

    def test_advance_waits_for_current_recovery(self):
        self.run_current_recovery_advance_race(False)

    def run_archived_recovery_advance_race(self, advance_first):
        query(f"UPDATE public.workspace_memberships SET role='owner' WHERE id='{self.membership}';")
        output=query(f"BEGIN; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT 'INTENT:' || public.reserve_private_class_setup('{self.workspace}','Dance','Beginners'); COMMIT;")
        prior=next(line.removeprefix('INTENT:') for line in output.splitlines() if line.startswith('INTENT:'))
        query(f"BEGIN; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT * FROM public.complete_private_class_setup('{self.workspace}','{prior}'); SELECT public.acknowledge_private_class_setup('{self.workspace}','{prior}'); COMMIT;")
        first_name,second_name='archive_first_'+uuid.uuid4().hex,'archive_second_'+uuid.uuid4().hex
        token=str(uuid.uuid4());first,second=start_psql_session(),start_psql_session()
        advance=f"SELECT public.advance_private_class_setup('{self.workspace}','{prior}','{token}','Art','Morning');\n"
        recover=f"SELECT 'STATUS:' || state FROM public.recover_private_archived_class_setup('{self.workspace}','{prior}');\n"
        try:
            for proc,name in ((first,first_name),(second,second_name)):
                proc.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{name}',false); SELECT set_config('request.jwt.claim.sub','{MEERA}',true);\n")
            first.stdin.write(advance if advance_first else recover);first.stdin.write("SELECT 'FIRST_LOCKED';\n");first.stdin.flush()
            if not advance_first: self.assertTrue(wait_for_session_marker(first,'STATUS:unknown'))
            self.assertTrue(wait_for_session_marker(first,'FIRST_LOCKED'))
            second.stdin.write(recover if advance_first else advance);second.stdin.write("COMMIT; SELECT 'SECOND_COMMITTED';\n");second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name,first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n");first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'FIRST_COMMITTED'))
            if advance_first: self.assertTrue(wait_for_session_marker(second,'STATUS:archived'))
            self.assertTrue(wait_for_session_marker(second,'SECOND_COMMITTED'))
            self.assertEqual(query(f"SELECT count(*) FROM public.class_setup_intent_history WHERE id='{prior}';"),'1')
        finally:
            close_psql_session(second);close_psql_session(first)

    def test_archived_recovery_waits_for_advance(self):
        self.run_archived_recovery_advance_race(True)

    def test_advance_waits_for_archived_recovery(self):
        self.run_archived_recovery_advance_race(False)

    def run_archived_discovery_advance_race(self, advance_first):
        query(f"UPDATE public.workspace_memberships SET role='owner' WHERE id='{self.membership}';")
        output=query(f"BEGIN; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT 'INTENT:' || public.reserve_private_class_setup('{self.workspace}','Dance','Beginners'); COMMIT;")
        prior=next(line.removeprefix('INTENT:') for line in output.splitlines() if line.startswith('INTENT:'))
        query(f"BEGIN; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT * FROM public.complete_private_class_setup('{self.workspace}','{prior}'); SELECT public.acknowledge_private_class_setup('{self.workspace}','{prior}'); COMMIT;")
        first_name,second_name='discover_first_'+uuid.uuid4().hex,'discover_second_'+uuid.uuid4().hex
        token=str(uuid.uuid4());first,second=start_psql_session(),start_psql_session()
        advance=f"SELECT public.advance_private_class_setup('{self.workspace}','{prior}','{token}','Art','Morning');\n"
        discover=f"SELECT 'COUNT:' || count(*) FROM public.list_private_archived_class_setups('{self.workspace}',NULL,50);\n"
        try:
            for proc,name in ((first,first_name),(second,second_name)):
                proc.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{name}',false); SELECT set_config('request.jwt.claim.sub','{MEERA}',true);\n")
            first.stdin.write(advance if advance_first else discover);first.stdin.write("SELECT 'FIRST_LOCKED';\n");first.stdin.flush()
            if not advance_first: self.assertTrue(wait_for_session_marker(first,'COUNT:0'))
            self.assertTrue(wait_for_session_marker(first,'FIRST_LOCKED'))
            second.stdin.write(discover if advance_first else advance);second.stdin.write("COMMIT; SELECT 'SECOND_COMMITTED';\n");second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name,first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n");first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'FIRST_COMMITTED'))
            if advance_first: self.assertTrue(wait_for_session_marker(second,'COUNT:1'))
            self.assertTrue(wait_for_session_marker(second,'SECOND_COMMITTED'))
            self.assertEqual(query(f"SELECT count(*) FROM public.class_setup_intent_history WHERE id='{prior}';"),'1')
        finally:
            close_psql_session(second);close_psql_session(first)

    def test_archived_discovery_waits_for_advance(self):
        self.run_archived_discovery_advance_race(True)

    def test_advance_waits_for_archived_discovery(self):
        self.run_archived_discovery_advance_race(False)

    def run_next_or_discovery_permission_race(self, operation, target, revoke_first):
        query(f"UPDATE public.workspace_memberships SET role='owner' WHERE id='{self.membership}';")
        output=query(f"BEGIN; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT 'INTENT:' || public.reserve_private_class_setup('{self.workspace}','Dance','Beginners'); COMMIT;")
        prior=next(line.removeprefix('INTENT:') for line in output.splitlines() if line.startswith('INTENT:'))
        query(f"BEGIN; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT * FROM public.complete_private_class_setup('{self.workspace}','{prior}'); SELECT public.acknowledge_private_class_setup('{self.workspace}','{prior}'); COMMIT;")
        token=str(uuid.uuid4())
        if operation=='discovery':
            query(f"BEGIN; SELECT set_config('request.jwt.claim.sub','{MEERA}',true); SELECT public.advance_private_class_setup('{self.workspace}','{prior}','{token}','Art','Morning'); COMMIT;")
        change={
            'workspace': f"UPDATE public.workspaces SET status='suspended' WHERE id='{self.workspace}';\n",
            'membership': f"UPDATE public.workspace_memberships SET status='suspended' WHERE id='{self.membership}';\n",
            'control': "UPDATE public.class_setup_controls SET enabled=false WHERE id=true;\n",
        }[target]
        call=(f"SELECT public.advance_private_class_setup('{self.workspace}','{prior}','{token}','Art','Morning');\n" if operation=='advance' else f"SELECT 'COUNT:' || count(*) FROM public.list_private_archived_class_setups('{self.workspace}',NULL,50);\n")
        first_name,second_name='access_first_'+uuid.uuid4().hex,'access_second_'+uuid.uuid4().hex
        first,second=start_psql_session(),start_psql_session()
        try:
            for proc,name in ((first,first_name),(second,second_name)):
                proc.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{name}',false); SELECT set_config('request.jwt.claim.sub','{MEERA}',true);\n")
            first.stdin.write(change if revoke_first else call);first.stdin.write("SELECT 'FIRST_LOCKED';\n");first.stdin.flush()
            if not revoke_first and operation=='discovery': self.assertTrue(wait_for_session_marker(first,'COUNT:1'))
            self.assertTrue(wait_for_session_marker(first,'FIRST_LOCKED'))
            second.stdin.write(call if revoke_first else change);second.stdin.write("COMMIT; SELECT 'SECOND_COMMITTED';\n");second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name,first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_COMMITTED';\n");first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first,'FIRST_COMMITTED'))
            if revoke_first:
                second.stdin.close();second.stdin=None
                _,errors=second.communicate(timeout=15)
                self.assertNotEqual(second.returncode,0)
                self.assertIn('Class setup unavailable' if target=='control' else 'Workspace access denied',errors)
            else:
                self.assertTrue(wait_for_session_marker(second,'SECOND_COMMITTED'))
            expected='0' if operation=='advance' and revoke_first else '1'
            self.assertEqual(query(f"SELECT count(*) FROM public.class_setup_next_requests WHERE workspace_id='{self.workspace}' AND request_id='{token}';"),expected)
        finally:
            close_psql_session(second);close_psql_session(first)

    def test_next_class_workspace_suspended_before_advance(self):
        self.run_next_or_discovery_permission_race('advance','workspace',True)
    def test_next_class_workspace_suspended_after_advance(self):
        self.run_next_or_discovery_permission_race('advance','workspace',False)
    def test_next_class_membership_suspended_before_advance(self):
        self.run_next_or_discovery_permission_race('advance','membership',True)
    def test_next_class_membership_suspended_after_advance(self):
        self.run_next_or_discovery_permission_race('advance','membership',False)
    def test_next_class_control_disabled_before_advance(self):
        self.run_next_or_discovery_permission_race('advance','control',True)
    def test_next_class_control_disabled_after_advance(self):
        self.run_next_or_discovery_permission_race('advance','control',False)
    def test_archive_discovery_workspace_suspended_before_read(self):
        self.run_next_or_discovery_permission_race('discovery','workspace',True)
    def test_archive_discovery_workspace_suspended_after_read(self):
        self.run_next_or_discovery_permission_race('discovery','workspace',False)
    def test_archive_discovery_membership_suspended_before_read(self):
        self.run_next_or_discovery_permission_race('discovery','membership',True)
    def test_archive_discovery_membership_suspended_after_read(self):
        self.run_next_or_discovery_permission_race('discovery','membership',False)
    def test_archive_discovery_control_disabled_before_read(self):
        self.run_next_or_discovery_permission_race('discovery','control',True)
    def test_archive_discovery_control_disabled_after_read(self):
        self.run_next_or_discovery_permission_race('discovery','control',False)
