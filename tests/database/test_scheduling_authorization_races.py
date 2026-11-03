"""Deterministic scheduling authorization races on a disposable database."""
import unittest
import uuid

from tests.database.test_concurrent_authorization import (
    MEERA, query, start_psql_session, wait_for_session_marker,
    wait_for_blocking_relationship, close_psql_session,
)


class SchedulingAuthorizationRaceTests(unittest.TestCase):
    def setUp(self):
        self.workspace, self.membership, self.course, self.batch, request = (str(uuid.uuid4()) for _ in range(5))
        query(f"""
BEGIN;
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

    def tearDown(self):
        query(f"""
BEGIN;
DELETE FROM public.schedule_sessions WHERE workspace_id = '{self.workspace}';
DELETE FROM public.batch_coach_assignments WHERE workspace_id = '{self.workspace}';
DELETE FROM public.batches WHERE workspace_id = '{self.workspace}';
DELETE FROM public.courses WHERE workspace_id = '{self.workspace}';
DELETE FROM public.workspace_memberships WHERE workspace_id = '{self.workspace}';
DELETE FROM public.workspaces WHERE id = '{self.workspace}';
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
        assign = f"SELECT public.assign_private_batch_coach('{self.workspace}', '{self.batch}', '{self.membership}');\n"
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
