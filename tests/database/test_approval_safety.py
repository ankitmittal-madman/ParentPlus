"""ParentPlus M3 approval safety tests. Local isolated PostgreSQL only."""

import subprocess
import time
import unittest
import uuid

from tests.database.test_concurrent_authorization import (
    MEERA, RAHUL, query, extract_labeled_id,
    create_test_workspace, create_test_child,
    wait_for_blocking_relationship, start_psql_session,
    wait_for_session_marker, close_psql_session,
)


def as_user(user_id, statement):
    return query(f"""
BEGIN;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{user_id}', true);
{statement}
COMMIT;
""")


class ApprovalSafetyTests(unittest.TestCase):

    def setUp(self):
        from tests.database.connection_test_access import grant_connection_test_access, revoke_connection_test_access
        grant_connection_test_access()
        self.addCleanup(revoke_connection_test_access)
        self.workspace_id = create_test_workspace()
        self.child_id = create_test_child()

        output = as_user(MEERA, f"""
SELECT 'REQUEST_ID:' ||
public.request_workspace_connection(
  '{self.workspace_id}', '{self.child_id}', '{uuid.uuid4()}'
)::text;
""")
        self.request_id = extract_labeled_id(output, "REQUEST_ID:")

    def tearDown(self):
        query(f"""
BEGIN;
DELETE FROM public.connection_events
WHERE connection_request_id IN (SELECT id FROM public.connection_requests WHERE child_id = '{self.child_id}')
OR workspace_child_id IN (
  SELECT id FROM public.workspace_children
  WHERE child_id = '{self.child_id}'
);
DELETE FROM public.connection_request_receipts WHERE child_id = '{self.child_id}';
DELETE FROM public.connection_requests
WHERE child_id = '{self.child_id}';
DELETE FROM public.workspace_children
WHERE child_id = '{self.child_id}';
DELETE FROM public.guardianships
WHERE child_id = '{self.child_id}';
DELETE FROM public.children
WHERE id = '{self.child_id}';
DELETE FROM public.workspace_memberships
WHERE workspace_id = '{self.workspace_id}';
DELETE FROM public.workspace_creation_receipts WHERE workspace_id = '{self.workspace_id}';
DELETE FROM public.workspaces
WHERE id = '{self.workspace_id}';
COMMIT;
""")

    def approve(self):
        return as_user(RAHUL, f"""
SELECT 'RELATIONSHIP_ID:' ||
public.approve_guardian_connection('{self.request_id}')::text;
""")

    def assert_rejected(self, expected_error):
        with self.assertRaisesRegex(AssertionError, expected_error):
            self.approve()

    def test_restricted_relationship(self):
        query(f"""
INSERT INTO public.workspace_children
(workspace_id, child_id, status)
VALUES ('{self.workspace_id}', '{self.child_id}', 'restricted');
""")
        self.assert_rejected("Existing relationship cannot be reactivated")
        self.assert_pending_without_approval()

    def test_archived_relationship(self):
        query(f"""
INSERT INTO public.workspace_children
(workspace_id, child_id, status)
VALUES ('{self.workspace_id}', '{self.child_id}', 'archived');
""")
        self.assert_rejected("Existing relationship cannot be reactivated")
        self.assert_pending_without_approval()

    def test_approved_retry_missing_relationship(self):
        self.approve()
        query(f"""
DELETE FROM public.connection_events
WHERE connection_request_id = '{self.request_id}';
DELETE FROM public.workspace_children
WHERE workspace_id = '{self.workspace_id}'
AND child_id = '{self.child_id}';
""")
        self.assert_rejected("Approved relationship missing")
        state = query(f"""
SELECT count(*) FROM public.connection_requests
WHERE id = '{self.request_id}' AND status = 'approved';
""")
        self.assertEqual(state, "1")

    def test_existing_active_relationship(self):
        first = self.approve()
        second = self.approve()
        self.assertEqual(
            extract_labeled_id(first, "RELATIONSHIP_ID:"),
            extract_labeled_id(second, "RELATIONSHIP_ID:")
        )
        query(f"""
UPDATE public.connection_requests
SET expires_at = pg_catalog.clock_timestamp() - interval '1 second'
WHERE id = '{self.request_id}';
""")
        after_expiry = self.approve()
        self.assertEqual(
            extract_labeled_id(first, "RELATIONSHIP_ID:"),
            extract_labeled_id(after_expiry, "RELATIONSHIP_ID:")
        )
        state = query(f"""
SELECT
 (SELECT count(*) FROM public.workspace_children
  WHERE workspace_id = '{self.workspace_id}'
    AND child_id = '{self.child_id}'),
 (SELECT count(*) FROM public.connection_events
  WHERE connection_request_id = '{self.request_id}'
    AND event_type = 'approved');
""")
        self.assertEqual(state, "1|1")

    def assert_pending_without_approval(self):
        state = query(f"""
SELECT
 (SELECT count(*) FROM public.connection_requests
  WHERE id = '{self.request_id}' AND status = 'pending'),
 (SELECT count(*) FROM public.connection_events
  WHERE connection_request_id = '{self.request_id}'
    AND event_type = 'approved');
""")
        self.assertEqual(state, "1|0")

    def test_expiry_during_lock_wait(self):
        blocker = None
        approver = None
        try:
            # Keep the request initially valid for approximately eight seconds.
            query(f"""
UPDATE public.connection_requests
SET expires_at = pg_catalog.clock_timestamp() + interval '8 seconds'
WHERE id = '{self.request_id}';
""")

            blocker_name = "m3_expiry_blocker_" + uuid.uuid4().hex
            approver_name = "m3_expiry_approver_" + uuid.uuid4().hex

            blocker = start_psql_session()
            blocker.stdin.write(f"""
BEGIN;
SET LOCAL lock_timeout = '10s';
SELECT set_config('application_name', '{blocker_name}', false);
SELECT id FROM public.connection_requests
WHERE id = '{self.request_id}' FOR UPDATE;
SELECT 'REQUEST_LOCKED';
""")
            blocker.stdin.flush()

            self.assertTrue(
                wait_for_session_marker(blocker, "REQUEST_LOCKED"),
                "Request row lock not acquired"
            )

            approver = start_psql_session()
            approver.stdin.write(f"""
BEGIN;
SET LOCAL lock_timeout = '20s';
SELECT set_config('application_name', '{approver_name}', false);
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{RAHUL}', true);
SELECT public.approve_guardian_connection('{self.request_id}');
COMMIT;
""")
            approver.stdin.flush()

            self.assertTrue(
                wait_for_blocking_relationship(approver_name, blocker_name),
                "Approval not observed waiting for request lock"
            )

            # Confirm approval is blocked while the request is still valid.
            remaining = query(f"""
SELECT pg_catalog.date_part(
  'epoch',
  expires_at - pg_catalog.clock_timestamp()
)
FROM public.connection_requests
WHERE id = '{self.request_id}';
""")
            self.assertGreater(
                float(remaining), 0,
                "Request expired before blocking was verified"
            )

            # Wait until the actual database expiry deadline has passed.
            deadline = time.monotonic() + float(remaining) + 0.3
            while time.monotonic() < deadline:
                time.sleep(0.1)

            expired = query(f"""
SELECT expires_at <= pg_catalog.clock_timestamp()
FROM public.connection_requests
WHERE id = '{self.request_id}';
""")
            self.assertEqual(expired, "t")

            blocker.stdin.write(
                "COMMIT;\nSELECT 'BLOCKER_COMMITTED';\n"
            )
            blocker.stdin.flush()

            self.assertTrue(
                wait_for_session_marker(blocker, "BLOCKER_COMMITTED"),
                "Blocker commit not confirmed"
            )

            approver.stdin.close()
            approver.stdin = None
            _, errors = approver.communicate(timeout=15)

            self.assertNotEqual(
                approver.returncode, 0,
                "Expired approval unexpectedly succeeded"
            )
            self.assertIn("Connection request expired", errors)
            self.assert_pending_without_approval()

        finally:
            for process in (approver, blocker):
                if process is not None:
                    close_psql_session(process)


    def test_expiry_while_waiting_for_workspace_lock(self):
        blocker = None
        approver = None
        try:
            # Keep the request initially valid for approximately eight seconds.
            query(f"""
UPDATE public.connection_requests
SET expires_at = pg_catalog.clock_timestamp() + interval '8 seconds'
WHERE id = '{self.request_id}';
""")

            blocker_name = "m3_workspace_expiry_blocker_" + uuid.uuid4().hex
            approver_name = "m3_workspace_expiry_approver_" + uuid.uuid4().hex

            blocker = start_psql_session()
            blocker.stdin.write(f"""
BEGIN;
SET LOCAL lock_timeout = '10s';
SELECT set_config('application_name', '{blocker_name}', false);
SELECT id FROM public.workspaces
WHERE id = '{self.workspace_id}' FOR UPDATE;
SELECT 'WORKSPACE_LOCKED';
""")
            blocker.stdin.flush()

            self.assertTrue(
                wait_for_session_marker(blocker, "WORKSPACE_LOCKED"),
                "Workspace row lock not acquired"
            )

            approver = start_psql_session()
            approver.stdin.write(f"""
BEGIN;
SET LOCAL lock_timeout = '20s';
SELECT set_config('application_name', '{approver_name}', false);
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{RAHUL}', true);
SELECT public.approve_guardian_connection('{self.request_id}');
COMMIT;
""")
            approver.stdin.flush()

            self.assertTrue(
                wait_for_blocking_relationship(approver_name, blocker_name),
                "Approval not observed waiting for workspace lock"
            )

            # Confirm approval is blocked while the request is still valid.
            remaining = query(f"""
SELECT pg_catalog.date_part(
  'epoch',
  expires_at - pg_catalog.clock_timestamp()
)
FROM public.connection_requests
WHERE id = '{self.request_id}';
""")
            self.assertGreater(
                float(remaining), 0,
                "Request expired before blocking was verified"
            )

            # Wait until the actual database expiry deadline has passed.
            deadline = time.monotonic() + float(remaining) + 0.3
            while time.monotonic() < deadline:
                time.sleep(0.1)

            expired = query(f"""
SELECT expires_at <= pg_catalog.clock_timestamp()
FROM public.connection_requests
WHERE id = '{self.request_id}';
""")
            self.assertEqual(expired, "t")

            blocker.stdin.write(
                "COMMIT;\nSELECT 'BLOCKER_COMMITTED';\n"
            )
            blocker.stdin.flush()

            self.assertTrue(
                wait_for_session_marker(blocker, "BLOCKER_COMMITTED"),
                "Blocker commit not confirmed"
            )

            approver.stdin.close()
            approver.stdin = None
            _, errors = approver.communicate(timeout=15)

            self.assertNotEqual(
                approver.returncode, 0,
                "Expired approval unexpectedly succeeded"
            )
            self.assertIn("Connection request expired", errors)
            self.assert_pending_without_approval()
            self.assertEqual(query(f"""
SELECT count(*) FROM public.workspace_children
WHERE workspace_id = '{self.workspace_id}' AND child_id = '{self.child_id}';
"""), "0")

        finally:
            for process in (approver, blocker):
                if process is not None:
                    close_psql_session(process)


    def test_request_waiting_for_tuple_lock_does_not_reuse_expired_pending(self):
        blocker = approver = None
        try:
            query(f"""
UPDATE public.connection_requests SET expires_at=pg_catalog.clock_timestamp()+interval '8 seconds'
WHERE id='{self.request_id}';
""")
            blocker_name = "request_expiry_blocker_" + uuid.uuid4().hex
            requester_name = "request_expiry_requester_" + uuid.uuid4().hex
            new_key = str(uuid.uuid4())
            blocker = start_psql_session()
            blocker.stdin.write(f"""
BEGIN;
SELECT set_config('application_name','{blocker_name}',false);
SELECT pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('{MEERA}' || ':' || '{self.child_id}' || ':' || '{self.workspace_id}',0));
SELECT 'TUPLE_LOCKED';
""")
            blocker.stdin.flush()
            self.assertTrue(wait_for_session_marker(blocker, "TUPLE_LOCKED"))
            approver = start_psql_session()
            approver.stdin.write(f"""
BEGIN;
SET LOCAL lock_timeout='20s';
SELECT set_config('application_name','{requester_name}',false);
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
SELECT 'RESULT:' || public.request_workspace_connection('{self.workspace_id}','{self.child_id}','{new_key}')::text;
COMMIT;
""")
            approver.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(requester_name, blocker_name))
            remaining = float(query(f"SELECT pg_catalog.date_part('epoch',expires_at-pg_catalog.clock_timestamp()) FROM public.connection_requests WHERE id='{self.request_id}';"))
            self.assertGreater(remaining, 0, "Request expired before blocking was verified")
            deadline = time.monotonic() + remaining + 0.3
            while time.monotonic() < deadline:
                time.sleep(0.1)
            blocker.stdin.write("COMMIT;\nSELECT 'BLOCKER_COMMITTED';\n")
            blocker.stdin.flush()
            self.assertTrue(wait_for_session_marker(blocker, "BLOCKER_COMMITTED"))
            approver.stdin.close()
            approver.stdin = None
            output, errors = approver.communicate(timeout=15)
            self.assertEqual(approver.returncode, 0, errors)
            result = extract_labeled_id(output, "RESULT:")
            self.assertNotEqual(result, self.request_id, "Expired request was reused")
            state = query(f"""
SELECT (SELECT status FROM public.connection_requests WHERE id='{self.request_id}'),
       (SELECT status FROM public.connection_requests WHERE id='{result}'),
       (SELECT count(*) FROM public.connection_events WHERE connection_request_id='{self.request_id}' AND event_type='expired'),
       (SELECT count(*) FROM public.connection_request_receipts WHERE request_key='{new_key}' AND connection_request_id='{result}');
""")
            self.assertEqual(state, "expired|pending|1|1")
        finally:
            for process in (approver, blocker):
                if process is not None:
                    close_psql_session(process)


    def exercise_same_key_different_children(self, first_commits):
        from tests.database.test_concurrent_authorization import cleanup_test_records
        other_child = create_test_child()
        first = second = None
        key = str(uuid.uuid4())
        first_name = 'receipt_first_' + uuid.uuid4().hex
        second_name = 'receipt_second_' + uuid.uuid4().hex
        try:
            first, second = start_psql_session(), start_psql_session()
            first.stdin.write(f"""
BEGIN; SET LOCAL lock_timeout='10s';
SELECT set_config('application_name','{first_name}',false);
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
SELECT public.request_workspace_connection('{self.workspace_id}','{self.child_id}','{key}');
SELECT 'FIRST_BOUND';
""")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_BOUND'))
            second.stdin.write(f"""
BEGIN; SET LOCAL lock_timeout='10s';
SELECT set_config('application_name','{second_name}',false);
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
SELECT public.request_workspace_connection('{self.workspace_id}','{other_child}','{key}');
COMMIT; SELECT 'SECOND_COMMITTED';
""")
            second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name, first_name))
            first.stdin.write(('COMMIT' if first_commits else 'ROLLBACK') + "; SELECT 'FIRST_DONE';\n")
            first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_DONE'))
            second.stdin.close()
            second.stdin = None
            output, errors = second.communicate(timeout=15)
            if first_commits:
                self.assertNotEqual(second.returncode, 0, 'different payload reused committed key')
                self.assertIn('Request ID reused with different details', errors)
                expected_child = self.child_id
                self.assertEqual(query(f"SELECT count(*) FROM public.connection_requests WHERE child_id='{other_child}';"), '0')
            else:
                self.assertEqual(second.returncode, 0, errors)
                self.assertIn('SECOND_COMMITTED', output)
                expected_child = other_child
            self.assertEqual(query(f"SELECT child_id::text FROM public.connection_request_receipts WHERE actor_id='{MEERA}' AND request_key='{key}';"), expected_child)
        finally:
            for process in (second, first):
                if process is not None:
                    close_psql_session(process)
            cleanup_test_records(child_id=other_child)

    def test_same_key_different_children_first_commits(self):
        self.exercise_same_key_different_children(True)

    def test_same_key_different_children_first_rolls_back(self):
        self.exercise_same_key_different_children(False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
