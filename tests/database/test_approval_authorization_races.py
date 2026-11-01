"""ParentPlus M3 deterministic approval authorization races.

LOCAL TEST ONLY.
Requires isolated parentplus-pg-test PostgreSQL.
"""

import unittest

from tests.database.test_concurrent_authorization import (
    MEERA,
    RAHUL,
    query,
    create_test_workspace,
    create_test_child,
    wait_for_blocking_relationship,
    start_psql_session,
    wait_for_session_marker,
    close_psql_session,
)


class ApprovalAuthorizationRaceTests(unittest.TestCase):
    """Deterministic approval-versus-permission-change tests."""

    def test_guardian_revocation_first(self):
        import uuid

        workspace_id = None
        child_id = None
        revoker = None
        approver = None

        try:
            workspace_id = create_test_workspace()
            child_id = create_test_child()

            request_output = query(f"""
BEGIN;
SET LOCAL ROLE authenticated;
SELECT set_config(
  'request.jwt.claim.sub', '{MEERA}', true
);
SELECT 'REQUEST_ID:' ||
  public.request_workspace_connection(
    '{workspace_id}', '{child_id}', '{uuid.uuid4()}'
  )::text;
COMMIT;
""")

            from tests.database.test_concurrent_authorization import extract_labeled_id
            request_id = extract_labeled_id(
                request_output, "REQUEST_ID:"
            )

            revoker_name = "m3_revoker_" + uuid.uuid4().hex
            approver_name = "m3_approver_" + uuid.uuid4().hex

            revoker = start_psql_session()
            revoker.stdin.write(f"""
BEGIN;
SET LOCAL lock_timeout = '5s';
SELECT set_config(
  'application_name', '{revoker_name}', false
);
UPDATE public.guardianships
SET status = 'revoked'
WHERE child_id = '{child_id}'
  AND guardian_user_id = '{MEERA}';
SELECT 'REVOCATION_LOCKED';
""")
            revoker.stdin.flush()

            self.assertTrue(
                wait_for_session_marker(
                    revoker, "REVOCATION_LOCKED"
                ),
                "Revocation lock not acquired"
            )

            approver = start_psql_session()
            approver.stdin.write(f"""
BEGIN;
SET LOCAL lock_timeout = '10s';
SELECT set_config(
  'application_name', '{approver_name}', false
);
SET LOCAL ROLE authenticated;
SELECT set_config(
  'request.jwt.claim.sub', '{RAHUL}', true
);
SELECT public.approve_guardian_connection(
  '{request_id}'
);
COMMIT;
""")
            approver.stdin.flush()

            self.assertTrue(
                wait_for_blocking_relationship(
                    approver_name, revoker_name
                ),
                "Approval was not observed waiting for revocation"
            )

            revoker.stdin.write(
                "COMMIT;\nSELECT 'REVOCATION_COMMITTED';\n"
            )
            revoker.stdin.flush()

            self.assertTrue(
                wait_for_session_marker(
                    revoker, "REVOCATION_COMMITTED"
                ),
                "Revocation commit not confirmed"
            )

            # The approval must fail after revocation commits.
            approver.stdin.close()
            approver.stdin = None
            output, errors = approver.communicate(timeout=15)

            self.assertNotEqual(
                approver.returncode, 0,
                "Approval unexpectedly succeeded"
            )
            self.assertIn(
                "Guardian no longer eligible", errors
            )

            counts = query(f"""
SELECT
  (SELECT count(*) FROM public.connection_requests
   WHERE id = '{request_id}' AND status = 'pending'),
  (SELECT count(*) FROM public.workspace_children
   WHERE workspace_id = '{workspace_id}'
     AND child_id = '{child_id}'),
  (SELECT count(*) FROM public.connection_events
   WHERE connection_request_id = '{request_id}'
     AND event_type = 'approved');
""").splitlines()[-1]

            self.assertEqual(counts, "1|0|0")
            print("PASS: Revocation-first approval race")

        finally:
            for process in (approver, revoker):
                if process is not None:
                    close_psql_session(process)

            if child_id:
                query(f"""
BEGIN;
DELETE FROM public.connection_events
WHERE connection_request_id IN (
  SELECT id FROM public.connection_requests
  WHERE child_id = '{child_id}'
)
OR workspace_child_id IN (
  SELECT id FROM public.workspace_children
  WHERE child_id = '{child_id}'
);
DELETE FROM public.connection_requests
WHERE child_id = '{child_id}';
DELETE FROM public.workspace_children
WHERE child_id = '{child_id}';
DELETE FROM public.guardianships
WHERE child_id = '{child_id}';
DELETE FROM public.children
WHERE id = '{child_id}';
COMMIT;
""")

            if workspace_id:
                query(f"""
BEGIN;
DELETE FROM public.workspace_memberships
WHERE workspace_id = '{workspace_id}';
DELETE FROM public.workspaces
WHERE id = '{workspace_id}';
COMMIT;
""")


    def test_approval_first_guardian_revocation(self):
        import time
        import uuid
        from tests.database.test_concurrent_authorization import extract_labeled_id

        workspace_id = None
        child_id = None
        approver = None
        revoker = None

        try:
            workspace_id = create_test_workspace()
            child_id = create_test_child()

            request_output = query(f"""
BEGIN;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{MEERA}', true);
SELECT 'REQUEST_ID:' ||
  public.request_workspace_connection(
    '{workspace_id}', '{child_id}', '{uuid.uuid4()}'
  )::text;
COMMIT;
""")
            request_id = extract_labeled_id(request_output, "REQUEST_ID:")

            approver_name = "m3_approval_first_" + uuid.uuid4().hex
            revoker_name = "m3_revocation_second_" + uuid.uuid4().hex

            approver = start_psql_session()
            approver.stdin.write(f"""
BEGIN;
SET LOCAL lock_timeout = '10s';
SELECT set_config('application_name', '{approver_name}', false);
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{RAHUL}', true);
SELECT 'RELATIONSHIP_ID:' ||
  public.approve_guardian_connection('{request_id}')::text;
SELECT 'APPROVAL_READY';
""")
            approver.stdin.flush()

            self.assertTrue(
                wait_for_session_marker(approver, "APPROVAL_READY"),
                "Approval did not reach ready marker"
            )

            revoker = start_psql_session()
            revoker.stdin.write(f"""
BEGIN;
SET LOCAL lock_timeout = '10s';
SELECT set_config('application_name', '{revoker_name}', false);
WITH changed AS (
  UPDATE public.guardianships
  SET status = 'revoked'
  WHERE child_id = '{child_id}'
    AND guardian_user_id = '{MEERA}'
  RETURNING id
)
SELECT 'UPDATED_ROWS:' || count(*)::text FROM changed;
COMMIT;
SELECT 'REVOCATION_COMPLETE';
""")
            revoker.stdin.flush()

            self.assertTrue(
                wait_for_blocking_relationship(revoker_name, approver_name),
                "Revocation was not observed waiting for approval"
            )

            approver.stdin.write("COMMIT;\nSELECT 'APPROVAL_COMMITTED';\n")
            approver.stdin.flush()

            self.assertTrue(
                wait_for_session_marker(approver, "APPROVAL_COMMITTED"),
                "Approval commit not confirmed"
            )

            self.assertTrue(
                wait_for_session_marker(revoker, "REVOCATION_COMPLETE"),
                "Revocation did not finish"
            )

            deadline = time.monotonic() + 5
            verified = False
            while time.monotonic() < deadline:
                result = query(f"""
SELECT
  (SELECT count(*) FROM public.connection_requests
   WHERE id = '{request_id}'
     AND status = 'approved'
     AND confirmed_by = '{RAHUL}'),
  (SELECT count(*) FROM public.workspace_children
   WHERE workspace_id = '{workspace_id}'
     AND child_id = '{child_id}'
     AND status = 'active'),
  (SELECT count(*) FROM public.connection_events
   WHERE connection_request_id = '{request_id}'
     AND event_type = 'approved'),
  (SELECT count(*) FROM public.guardianships
   WHERE child_id = '{child_id}'
     AND guardian_user_id = '{MEERA}'
     AND status = 'revoked');
""").splitlines()[-1]

                if result == "1|1|1|1":
                    verified = True
                    break
                time.sleep(0.1)

            self.assertTrue(
                verified,
                "Unexpected approval/revocation final state"
            )
            print("PASS: Approval-first guardian revocation race")

        finally:
            for process in (revoker, approver):
                if process is not None:
                    close_psql_session(process)

            if child_id:
                query(f"""
BEGIN;
DELETE FROM public.connection_events
WHERE connection_request_id IN (
  SELECT id FROM public.connection_requests
  WHERE child_id = '{child_id}'
)
OR workspace_child_id IN (
  SELECT id FROM public.workspace_children
  WHERE child_id = '{child_id}'
);
DELETE FROM public.connection_requests WHERE child_id = '{child_id}';
DELETE FROM public.workspace_children WHERE child_id = '{child_id}';
DELETE FROM public.guardianships WHERE child_id = '{child_id}';
DELETE FROM public.children WHERE id = '{child_id}';
COMMIT;
""")

            if workspace_id:
                query(f"""
BEGIN;
DELETE FROM public.workspace_memberships
WHERE workspace_id = '{workspace_id}';
DELETE FROM public.workspaces WHERE id = '{workspace_id}';
COMMIT;
""")


    def test_approval_first_workspace_suspension(self):
        import time
        import uuid
        from tests.database.test_concurrent_authorization import extract_labeled_id

        workspace_id = None
        child_id = None
        approver = None
        revoker = None

        try:
            workspace_id = create_test_workspace()
            child_id = create_test_child()

            request_output = query(f"""
BEGIN;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{MEERA}', true);
SELECT 'REQUEST_ID:' ||
  public.request_workspace_connection(
    '{workspace_id}', '{child_id}', '{uuid.uuid4()}'
  )::text;
COMMIT;
""")
            request_id = extract_labeled_id(request_output, "REQUEST_ID:")

            approver_name = "m3_approval_first_" + uuid.uuid4().hex
            revoker_name = "m3_workspace_second_" + uuid.uuid4().hex

            approver = start_psql_session()
            approver.stdin.write(f"""
BEGIN;
SET LOCAL lock_timeout = '10s';
SELECT set_config('application_name', '{approver_name}', false);
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{RAHUL}', true);
SELECT 'RELATIONSHIP_ID:' ||
  public.approve_guardian_connection('{request_id}')::text;
SELECT 'APPROVAL_READY';
""")
            approver.stdin.flush()

            self.assertTrue(
                wait_for_session_marker(approver, "APPROVAL_READY"),
                "Approval did not reach ready marker"
            )

            revoker = start_psql_session()
            revoker.stdin.write(f"""
BEGIN;
SET LOCAL lock_timeout = '10s';
SELECT set_config('application_name', '{revoker_name}', false);
WITH changed AS (
  UPDATE public.workspaces
  SET status = 'suspended'
  WHERE id = '{workspace_id}'
  RETURNING id
)
SELECT 'UPDATED_ROWS:' || count(*)::text FROM changed;
COMMIT;
SELECT 'SUSPENSION_COMPLETE';
""")
            revoker.stdin.flush()

            self.assertTrue(
                wait_for_blocking_relationship(revoker_name, approver_name),
                "Revocation was not observed waiting for approval"
            )

            approver.stdin.write("COMMIT;\nSELECT 'APPROVAL_COMMITTED';\n")
            approver.stdin.flush()

            self.assertTrue(
                wait_for_session_marker(approver, "APPROVAL_COMMITTED"),
                "Approval commit not confirmed"
            )

            self.assertTrue(
                wait_for_session_marker(revoker, "UPDATED_ROWS:1"),
                "Expected exactly one suspended workspace"
            )

            self.assertTrue(
                wait_for_session_marker(revoker, "SUSPENSION_COMPLETE"),
                "Workspace suspension did not finish"
            )

            deadline = time.monotonic() + 5
            verified = False
            while time.monotonic() < deadline:
                result = query(f"""
SELECT
  (SELECT count(*) FROM public.connection_requests
   WHERE id = '{request_id}'
     AND status = 'approved'
     AND confirmed_by = '{RAHUL}'),
  (SELECT count(*) FROM public.workspace_children
   WHERE workspace_id = '{workspace_id}'
     AND child_id = '{child_id}'
     AND status = 'active'),
  (SELECT count(*) FROM public.connection_events
   WHERE connection_request_id = '{request_id}'
     AND event_type = 'approved'),
  (SELECT count(*) FROM public.workspaces
   WHERE id = '{workspace_id}'
     AND status = 'suspended');
""").splitlines()[-1]

                if result == "1|1|1|1":
                    verified = True
                    break
                time.sleep(0.1)

            self.assertTrue(
                verified,
                "Unexpected approval/revocation final state"
            )
            print("PASS: Approval-first workspace suspension race")

        finally:
            for process in (revoker, approver):
                if process is not None:
                    close_psql_session(process)

            if child_id:
                query(f"""
BEGIN;
DELETE FROM public.connection_events
WHERE connection_request_id IN (
  SELECT id FROM public.connection_requests
  WHERE child_id = '{child_id}'
)
OR workspace_child_id IN (
  SELECT id FROM public.workspace_children
  WHERE child_id = '{child_id}'
);
DELETE FROM public.connection_requests WHERE child_id = '{child_id}';
DELETE FROM public.workspace_children WHERE child_id = '{child_id}';
DELETE FROM public.guardianships WHERE child_id = '{child_id}';
DELETE FROM public.children WHERE id = '{child_id}';
COMMIT;
""")

            if workspace_id:
                query(f"""
BEGIN;
DELETE FROM public.workspace_memberships
WHERE workspace_id = '{workspace_id}';
DELETE FROM public.workspaces WHERE id = '{workspace_id}';
COMMIT;
""")


    def test_workspace_suspension_first(self):
        import uuid
        from tests.database.test_concurrent_authorization import extract_labeled_id

        workspace_id = None
        child_id = None
        suspender = None
        approver = None

        try:
            workspace_id = create_test_workspace()
            child_id = create_test_child()

            request_output = query(f"""
BEGIN;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{MEERA}', true);
SELECT 'REQUEST_ID:' ||
  public.request_workspace_connection(
    '{workspace_id}', '{child_id}', '{uuid.uuid4()}'
  )::text;
COMMIT;
""")
            request_id = extract_labeled_id(request_output, "REQUEST_ID:")

            suspender_name = "m3_workspace_suspender_" + uuid.uuid4().hex
            approver_name = "m3_workspace_approver_" + uuid.uuid4().hex

            suspender = start_psql_session()
            suspender.stdin.write(f"""
BEGIN;
SET LOCAL lock_timeout = '10s';
SELECT set_config('application_name', '{suspender_name}', false);
WITH changed AS (
  UPDATE public.workspaces
  SET status = 'suspended'
  WHERE id = '{workspace_id}'
  RETURNING id
)
SELECT 'SUSPENSION_LOCKED:' || count(*)::text FROM changed;
""")
            suspender.stdin.flush()

            self.assertTrue(
                wait_for_session_marker(
                    suspender, "SUSPENSION_LOCKED:1"
                ),
                "Workspace suspension lock not acquired"
            )

            approver = start_psql_session()
            approver.stdin.write(f"""
BEGIN;
SET LOCAL lock_timeout = '10s';
SELECT set_config('application_name', '{approver_name}', false);
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{RAHUL}', true);
SELECT public.approve_guardian_connection('{request_id}');
COMMIT;
""")
            approver.stdin.flush()

            self.assertTrue(
                wait_for_blocking_relationship(
                    approver_name, suspender_name
                ),
                "Approval not observed waiting for suspension"
            )

            suspender.stdin.write(
                "COMMIT;\nSELECT 'SUSPENSION_COMMITTED';\n"
            )
            suspender.stdin.flush()

            self.assertTrue(
                wait_for_session_marker(
                    suspender, "SUSPENSION_COMMITTED"
                ),
                "Suspension commit not confirmed"
            )

            approver.stdin.close()
            approver.stdin = None
            output, errors = approver.communicate(timeout=15)

            self.assertNotEqual(
                approver.returncode, 0,
                "Approval unexpectedly succeeded"
            )
            self.assertIn("Workspace unavailable", errors)

            counts = query(f"""
SELECT
  (SELECT count(*) FROM public.connection_requests
   WHERE id = '{request_id}' AND status = 'pending'),
  (SELECT count(*) FROM public.workspace_children
   WHERE workspace_id = '{workspace_id}'
     AND child_id = '{child_id}'),
  (SELECT count(*) FROM public.connection_events
   WHERE connection_request_id = '{request_id}'
     AND event_type = 'approved'),
  (SELECT count(*) FROM public.workspaces
   WHERE id = '{workspace_id}' AND status = 'suspended');
""").splitlines()[-1]

            self.assertEqual(counts, "1|0|0|1")
            print("PASS: Workspace suspension-first approval race")

        finally:
            for process in (approver, suspender):
                if process is not None:
                    close_psql_session(process)

            if child_id:
                query(f"""
BEGIN;
DELETE FROM public.connection_events
WHERE connection_request_id IN (
  SELECT id FROM public.connection_requests
  WHERE child_id = '{child_id}'
)
OR workspace_child_id IN (
  SELECT id FROM public.workspace_children
  WHERE child_id = '{child_id}'
);
DELETE FROM public.connection_requests WHERE child_id = '{child_id}';
DELETE FROM public.workspace_children WHERE child_id = '{child_id}';
DELETE FROM public.guardianships WHERE child_id = '{child_id}';
DELETE FROM public.children WHERE id = '{child_id}';
COMMIT;
""")

            if workspace_id:
                query(f"""
BEGIN;
DELETE FROM public.workspace_memberships
WHERE workspace_id = '{workspace_id}';
DELETE FROM public.workspaces WHERE id = '{workspace_id}';
COMMIT;
""")


    def test_membership_suspension_first(self):
        import uuid
        from tests.database.test_concurrent_authorization import extract_labeled_id

        workspace_id = None
        child_id = None
        suspender = None
        approver = None

        try:
            workspace_id = create_test_workspace()
            child_id = create_test_child()

            request_output = query(f"""
BEGIN;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{MEERA}', true);
SELECT 'REQUEST_ID:' ||
  public.request_workspace_connection(
    '{workspace_id}', '{child_id}', '{uuid.uuid4()}'
  )::text;
COMMIT;
""")
            request_id = extract_labeled_id(request_output, "REQUEST_ID:")

            suspender_name = "m3_membership_suspender_" + uuid.uuid4().hex
            approver_name = "m3_membership_approver_" + uuid.uuid4().hex

            suspender = start_psql_session()
            suspender.stdin.write(f"""
BEGIN;
SET LOCAL lock_timeout = '10s';
SELECT set_config('application_name', '{suspender_name}', false);
WITH changed AS (
  UPDATE public.workspace_memberships
  SET status = 'suspended'
  WHERE workspace_id = '{workspace_id}'
    AND user_id = '{RAHUL}'
  RETURNING id
)
SELECT 'MEMBERSHIP_LOCKED:' || count(*)::text FROM changed;
""")
            suspender.stdin.flush()

            self.assertTrue(
                wait_for_session_marker(
                    suspender, "MEMBERSHIP_LOCKED:1"
                ),
                "Workspace suspension lock not acquired"
            )

            approver = start_psql_session()
            approver.stdin.write(f"""
BEGIN;
SET LOCAL lock_timeout = '10s';
SELECT set_config('application_name', '{approver_name}', false);
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{RAHUL}', true);
SELECT public.approve_guardian_connection('{request_id}');
COMMIT;
""")
            approver.stdin.flush()

            self.assertTrue(
                wait_for_blocking_relationship(
                    approver_name, suspender_name
                ),
                "Approval not observed waiting for suspension"
            )

            suspender.stdin.write(
                "COMMIT;\nSELECT 'MEMBERSHIP_COMMITTED';\n"
            )
            suspender.stdin.flush()

            self.assertTrue(
                wait_for_session_marker(
                    suspender, "MEMBERSHIP_COMMITTED"
                ),
                "Suspension commit not confirmed"
            )

            approver.stdin.close()
            approver.stdin = None
            output, errors = approver.communicate(timeout=15)

            self.assertNotEqual(
                approver.returncode, 0,
                "Approval unexpectedly succeeded"
            )
            self.assertIn("Workspace approval not authorized", errors)

            counts = query(f"""
SELECT
  (SELECT count(*) FROM public.connection_requests
   WHERE id = '{request_id}' AND status = 'pending'),
  (SELECT count(*) FROM public.workspace_children
   WHERE workspace_id = '{workspace_id}'
     AND child_id = '{child_id}'),
  (SELECT count(*) FROM public.connection_events
   WHERE connection_request_id = '{request_id}'
     AND event_type = 'approved'),
  (SELECT count(*) FROM public.workspace_memberships
   WHERE workspace_id = '{workspace_id}'
     AND user_id = '{RAHUL}' AND status = 'suspended');
""").splitlines()[-1]

            self.assertEqual(counts, "1|0|0|1")
            print("PASS: Workspace suspension-first approval race")

        finally:
            for process in (approver, suspender):
                if process is not None:
                    close_psql_session(process)

            if child_id:
                query(f"""
BEGIN;
DELETE FROM public.connection_events
WHERE connection_request_id IN (
  SELECT id FROM public.connection_requests
  WHERE child_id = '{child_id}'
)
OR workspace_child_id IN (
  SELECT id FROM public.workspace_children
  WHERE child_id = '{child_id}'
);
DELETE FROM public.connection_requests WHERE child_id = '{child_id}';
DELETE FROM public.workspace_children WHERE child_id = '{child_id}';
DELETE FROM public.guardianships WHERE child_id = '{child_id}';
DELETE FROM public.children WHERE id = '{child_id}';
COMMIT;
""")

            if workspace_id:
                query(f"""
BEGIN;
DELETE FROM public.workspace_memberships
WHERE workspace_id = '{workspace_id}';
DELETE FROM public.workspaces WHERE id = '{workspace_id}';
COMMIT;
""")


    def test_approval_first_membership_suspension(self):
        import time
        import uuid
        from tests.database.test_concurrent_authorization import extract_labeled_id

        workspace_id = None
        child_id = None
        approver = None
        revoker = None

        try:
            workspace_id = create_test_workspace()
            child_id = create_test_child()

            request_output = query(f"""
BEGIN;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{MEERA}', true);
SELECT 'REQUEST_ID:' ||
  public.request_workspace_connection(
    '{workspace_id}', '{child_id}', '{uuid.uuid4()}'
  )::text;
COMMIT;
""")
            request_id = extract_labeled_id(request_output, "REQUEST_ID:")

            approver_name = "m3_approval_first_" + uuid.uuid4().hex
            revoker_name = "m3_membership_second_" + uuid.uuid4().hex

            approver = start_psql_session()
            approver.stdin.write(f"""
BEGIN;
SET LOCAL lock_timeout = '10s';
SELECT set_config('application_name', '{approver_name}', false);
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{RAHUL}', true);
SELECT 'RELATIONSHIP_ID:' ||
  public.approve_guardian_connection('{request_id}')::text;
SELECT 'APPROVAL_READY';
""")
            approver.stdin.flush()

            self.assertTrue(
                wait_for_session_marker(approver, "APPROVAL_READY"),
                "Approval did not reach ready marker"
            )

            revoker = start_psql_session()
            revoker.stdin.write(f"""
BEGIN;
SET LOCAL lock_timeout = '10s';
SELECT set_config('application_name', '{revoker_name}', false);
WITH changed AS (
  UPDATE public.workspace_memberships
  SET status = 'suspended'
  WHERE workspace_id = '{workspace_id}'
    AND user_id = '{RAHUL}'
  RETURNING id
)
SELECT 'UPDATED_ROWS:' || count(*)::text FROM changed;
COMMIT;
SELECT 'MEMBERSHIP_COMPLETE';
""")
            revoker.stdin.flush()

            self.assertTrue(
                wait_for_blocking_relationship(revoker_name, approver_name),
                "Revocation was not observed waiting for approval"
            )

            approver.stdin.write("COMMIT;\nSELECT 'APPROVAL_COMMITTED';\n")
            approver.stdin.flush()

            self.assertTrue(
                wait_for_session_marker(approver, "APPROVAL_COMMITTED"),
                "Approval commit not confirmed"
            )

            self.assertTrue(
                wait_for_session_marker(revoker, "UPDATED_ROWS:1"),
                "Expected exactly one suspended membership"
            )

            self.assertTrue(
                wait_for_session_marker(revoker, "MEMBERSHIP_COMPLETE"),
                "Membership suspension did not finish"
            )

            deadline = time.monotonic() + 5
            verified = False
            while time.monotonic() < deadline:
                result = query(f"""
SELECT
  (SELECT count(*) FROM public.connection_requests
   WHERE id = '{request_id}'
     AND status = 'approved'
     AND confirmed_by = '{RAHUL}'),
  (SELECT count(*) FROM public.workspace_children
   WHERE workspace_id = '{workspace_id}'
     AND child_id = '{child_id}'
     AND status = 'active'),
  (SELECT count(*) FROM public.connection_events
   WHERE connection_request_id = '{request_id}'
     AND event_type = 'approved'),
  (SELECT count(*) FROM public.workspace_memberships
   WHERE workspace_id = '{workspace_id}'
     AND user_id = '{RAHUL}'
     AND status = 'suspended'),
  (SELECT count(*) FROM public.workspaces
   WHERE id = '{workspace_id}'
     AND status = 'active');
""").splitlines()[-1]

                if result == "1|1|1|1|1":
                    verified = True
                    break
                time.sleep(0.1)

            self.assertTrue(
                verified,
                "Unexpected approval/membership suspension final state"
            )
            print("PASS: Approval-first membership suspension race")

        finally:
            for process in (revoker, approver):
                if process is not None:
                    close_psql_session(process)

            if child_id:
                query(f"""
BEGIN;
DELETE FROM public.connection_events
WHERE connection_request_id IN (
  SELECT id FROM public.connection_requests
  WHERE child_id = '{child_id}'
)
OR workspace_child_id IN (
  SELECT id FROM public.workspace_children
  WHERE child_id = '{child_id}'
);
DELETE FROM public.connection_requests WHERE child_id = '{child_id}';
DELETE FROM public.workspace_children WHERE child_id = '{child_id}';
DELETE FROM public.guardianships WHERE child_id = '{child_id}';
DELETE FROM public.children WHERE id = '{child_id}';
COMMIT;
""")

            if workspace_id:
                query(f"""
BEGIN;
DELETE FROM public.workspace_memberships
WHERE workspace_id = '{workspace_id}';
DELETE FROM public.workspaces WHERE id = '{workspace_id}';
COMMIT;
""")


if __name__ == "__main__":
    unittest.main(verbosity=2)
