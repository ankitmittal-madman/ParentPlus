"""Workspace replay races in a disposable database with synthetic identities."""

import unittest
import uuid

from tests.database.test_concurrent_authorization import (
    RAHUL, cleanup_test_records, close_psql_session, create_test_workspace,
    query, start_psql_session, wait_for_blocking_relationship, wait_for_session_marker,
)


class WorkspaceReplayRaceTests(unittest.TestCase):
    def exercise_race(self, target, commits):
        workspace = create_test_workspace()
        first = second = None
        key = query(f"SELECT creation_request_id FROM public.workspaces WHERE id='{workspace}';")
        first_name = 'workspace_first_' + uuid.uuid4().hex
        second_name = 'workspace_second_' + uuid.uuid4().hex
        change = (
            f"UPDATE public.workspaces SET status='suspended' WHERE id='{workspace}'"
            if target == 'workspace' else
            f"UPDATE public.workspace_memberships SET status='suspended' WHERE workspace_id='{workspace}' AND user_id='{RAHUL}'"
        )
        try:
            first, second = start_psql_session(), start_psql_session()
            first.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{first_name}',false); {change}; SELECT 'FIRST_LOCKED';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_LOCKED'))
            second.stdin.write(f"""
BEGIN; SET LOCAL lock_timeout='10s';
SELECT set_config('application_name','{second_name}',false);
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{RAHUL}',true);
SELECT 'RESULT:' || public.create_workspace('Authorization Race Test Academy','academy','{key}')::text;
COMMIT; SELECT 'SECOND_COMMITTED';
""")
            second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name, first_name))
            first.stdin.write(('COMMIT' if commits else 'ROLLBACK') + "; SELECT 'FIRST_DONE';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_DONE'))
            second.stdin.close()
            second.stdin = None
            output, errors = second.communicate(timeout=15)
            if commits:
                self.assertNotEqual(second.returncode, 0, 'replay succeeded after access was suspended')
                self.assertIn('Workspace unavailable', errors)
            else:
                self.assertEqual(second.returncode, 0, errors)
                self.assertIn('RESULT:' + workspace, output)
                self.assertIn('SECOND_COMMITTED', output)
        finally:
            for process in (second, first):
                if process is not None:
                    close_psql_session(process)
            cleanup_test_records(workspace_id=workspace)

    def test_workspace_suspension_commits_before_replay(self):
        self.exercise_race('workspace', True)

    def test_workspace_suspension_rolls_back_before_replay(self):
        self.exercise_race('workspace', False)

    def test_membership_suspension_commits_before_replay(self):
        self.exercise_race('membership', True)

    def test_membership_suspension_rolls_back_before_replay(self):
        self.exercise_race('membership', False)

    def exercise_replay_first(self, target):
        workspace = create_test_workspace()
        first = second = None
        key = query(f"SELECT creation_request_id FROM public.workspaces WHERE id='{workspace}';")
        first_name = 'workspace_replay_' + uuid.uuid4().hex
        second_name = 'workspace_change_' + uuid.uuid4().hex
        change = (
            f"UPDATE public.workspaces SET status='suspended' WHERE id='{workspace}'"
            if target == 'workspace' else
            f"UPDATE public.workspace_memberships SET status='suspended' WHERE workspace_id='{workspace}' AND user_id='{RAHUL}'"
        )
        try:
            first, second = start_psql_session(), start_psql_session()
            first.stdin.write(f"""
BEGIN; SET LOCAL lock_timeout='10s';
SELECT set_config('application_name','{first_name}',false);
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{RAHUL}',true);
SELECT 'RESULT:' || public.create_workspace('Authorization Race Test Academy','academy','{key}')::text;
SELECT 'REPLAYED';
""")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'REPLAYED'))
            second.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{second_name}',false); {change}; COMMIT; SELECT 'CHANGED';\n")
            second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name, first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_DONE';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_DONE'))
            self.assertTrue(wait_for_session_marker(second, 'CHANGED'))
            column = 'public.workspaces' if target == 'workspace' else 'public.workspace_memberships'
            where = f"id='{workspace}'" if target == 'workspace' else f"workspace_id='{workspace}' AND user_id='{RAHUL}'"
            self.assertEqual(query(f"SELECT status FROM {column} WHERE {where};"), 'suspended')
        finally:
            for process in (second, first):
                if process is not None:
                    close_psql_session(process)
            cleanup_test_records(workspace_id=workspace)

    def test_workspace_suspension_waits_for_replay(self):
        self.exercise_replay_first('workspace')

    def test_membership_suspension_waits_for_replay(self):
        self.exercise_replay_first('membership')
