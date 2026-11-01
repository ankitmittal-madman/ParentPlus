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
WHERE connection_request_id = '{self.request_id}'
OR workspace_child_id IN (
  SELECT id FROM public.workspace_children
  WHERE child_id = '{self.child_id}'
);
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
            # Keep the request initially valid for approximately two seconds.
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
