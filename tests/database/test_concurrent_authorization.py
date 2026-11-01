"""ParentPlus concurrent authorization regression tests.

Requires disposable PostgreSQL with migrations 001-011.
Uses fictional test identities and isolated database sessions.
"""

import subprocess
import select
import time
import uuid
import unittest

CONTAINER = "parentplus-pg-test"
MEERA = "11111111-1111-4111-8111-111111111111"
RAHUL = "22222222-2222-4222-8222-222222222222"

PSQL = [
    "docker", "exec", "-i", CONTAINER,
    "psql", "-X", "-A", "-t",
    "-v", "ON_ERROR_STOP=1",
    "-U", "parentplus_test", "-d", "parentplus_test",
]


def query(sql, timeout=15):
    result = subprocess.run(
        PSQL,
        input=sql,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    if result.returncode:
        raise AssertionError(result.stderr.strip())
    return result.stdout.strip()


def extract_labeled_id(output, label):
    matches = [
        line.split(label, 1)[1].strip()
        for line in output.splitlines()
        if line.startswith(label)
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"Expected exactly one {label} value"
        )
    return str(uuid.UUID(matches[0]))


def create_test_workspace():
    request_id = str(uuid.uuid4())

    output = query(f"""
BEGIN;
SET LOCAL ROLE authenticated;
SELECT set_config(
  'request.jwt.claim.sub',
  '{RAHUL}', true
);
SELECT 'WORKSPACE_ID:' || public.create_workspace(
  'Authorization Race Test Academy',
  'academy',
  '{request_id}'
)::text;
COMMIT;
""")

    return extract_labeled_id(output, "WORKSPACE_ID:")


def create_test_child():
    request_id = str(uuid.uuid4())

    output = query(f"""
BEGIN;
SET LOCAL ROLE authenticated;
SELECT set_config(
  'request.jwt.claim.sub',
  '{MEERA}', true
);
SELECT 'CHILD_ID:' || public.create_child(
  'Riya Authorization Race Test',
  '{request_id}'
)::text;
COMMIT;
""")

    return extract_labeled_id(output, "CHILD_ID:")


def cleanup_test_records(workspace_id=None, child_id=None):
    """Remove only records created by this test."""

    if child_id is not None:
        child_id = str(uuid.UUID(child_id))

        query(f"""
BEGIN;
DELETE FROM public.connection_events
WHERE connection_request_id IN (
  SELECT id FROM public.connection_requests
  WHERE child_id = '{child_id}'
);
DELETE FROM public.connection_requests
WHERE child_id = '{child_id}';
DELETE FROM public.guardianships
WHERE child_id = '{child_id}';
DELETE FROM public.children
WHERE id = '{child_id}';
COMMIT;
""")

        remaining = query(f"""
SELECT count(*) FROM public.children
WHERE id = '{child_id}';
""")

        if remaining != "0":
            raise AssertionError("Child cleanup incomplete")

    if workspace_id is not None:
        workspace_id = str(uuid.UUID(workspace_id))

        query(f"""
BEGIN;
DELETE FROM public.workspace_memberships
WHERE workspace_id = '{workspace_id}';
DELETE FROM public.workspaces
WHERE id = '{workspace_id}';
COMMIT;
""")

        remaining = query(f"""
SELECT count(*) FROM public.workspaces
WHERE id = '{workspace_id}';
""")

        if remaining != "0":
            raise AssertionError("Workspace cleanup incomplete")

    print("PASS: Authorization test cleanup verified")



def wait_for_blocking_relationship(waiter_name, blocker_name, timeout=5):
    """Confirm one named PostgreSQL session is blocked by another."""

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        result = query(f"""
SELECT count(*)
FROM pg_stat_activity waiter
JOIN pg_stat_activity blocker
  ON blocker.pid = ANY(
    pg_blocking_pids(waiter.pid)
  )
WHERE waiter.datname = 'parentplus_test'
  AND waiter.application_name = '{waiter_name}'
  AND waiter.state = 'active'
  AND blocker.application_name = '{blocker_name}';
""")

        if result.splitlines()[-1] == "1":
            return True

        time.sleep(0.1)

    return False


def start_psql_session():
    """Start a persistent PostgreSQL test session."""

    return subprocess.Popen(
        PSQL,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )


def wait_for_session_marker(process, marker, timeout=5):
    """Read PostgreSQL output without losing buffered lines."""

    import queue
    import threading

    if not hasattr(process, "_marker_queue"):
        process._marker_queue = queue.Queue()

        def read_output():
            try:
                for line in process.stdout:
                    process._marker_queue.put(line.strip())
            finally:
                process._marker_queue.put(None)

        process._marker_reader = threading.Thread(
            target=read_output,
            daemon=True,
        )
        process._marker_reader.start()

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()

        try:
            line = process._marker_queue.get(
                timeout=max(0.01, remaining)
            )
        except queue.Empty:
            return False

        if line is None:
            return False

        if line == marker:
            return True

    return False


def close_psql_session(process):
    """Close PostgreSQL process and all associated pipes."""

    if process is None:
        return

    try:
        if process.poll() is None:
            if process.stdin is not None:
                try:
                    process.stdin.write("ROLLBACK;\n\\q\n")
                    process.stdin.flush()
                except (BrokenPipeError, OSError):
                    pass

            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

        if hasattr(process, "_marker_reader"):
            process._marker_reader.join(timeout=2)

    finally:
        for stream in (
            process.stdin,
            process.stdout,
            process.stderr,
        ):
            if stream is not None and not stream.closed:
                stream.close()


class ConcurrentAuthorizationTests(unittest.TestCase):

    def test_revocation_commits_before_authorization(self):
        workspace_id = None
        child_id = None
        revoker = None
        requester = None

        try:
            workspace_id = create_test_workspace()
            child_id = create_test_child()

            revoker = subprocess.Popen(
                PSQL,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            revoker_name = 'parentplus_revoker_' + uuid.uuid4().hex

            revoker.stdin.write(f"""
BEGIN;
SELECT set_config(
  'application_name',
  '{revoker_name}',
  false
);
WITH changed AS (
  UPDATE public.guardianships
  SET status = 'revoked'
  WHERE child_id = '{child_id}'
  RETURNING id
)
SELECT 'REVOCATION_LOCKED:' || count(*)::text
FROM changed;
""")
            revoker.stdin.flush()

            found = False
            deadline = time.monotonic() + 5

            while time.monotonic() < deadline:
                ready, _, _ = select.select(
                    [revoker.stdout], [], [], 0.5
                )
                if ready:
                    line = revoker.stdout.readline().strip()
                    if line == "REVOCATION_LOCKED:1":
                        found = True
                        break

            self.assertTrue(found, "Revocation lock not confirmed")

            session_name = 'parentplus_race_' + uuid.uuid4().hex

            requester_sql = f"""
BEGIN;
SELECT set_config(
  'application_name',
  '{session_name}',
  false
);
SET LOCAL ROLE authenticated;
SELECT set_config(
  'request.jwt.claim.sub',
  '{MEERA}', true
);
SELECT public.request_workspace_connection(
  '{workspace_id}',
  '{child_id}',
  '{uuid.uuid4()}'
);
COMMIT;
"""

            requester = subprocess.Popen(
                PSQL,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            requester.stdin.write(requester_sql)
            requester.stdin.close()
            requester.stdin = None

            blocked = False
            deadline = time.monotonic() + 5

            while time.monotonic() < deadline:
                result = query(f"""
SELECT count(*)
FROM pg_stat_activity requester
JOIN pg_stat_activity revoker
  ON revoker.pid = ANY(
    pg_blocking_pids(requester.pid)
  )
WHERE requester.datname = 'parentplus_test'
  AND requester.application_name = '{session_name}'
  AND requester.state = 'active'
  AND revoker.application_name = '{revoker_name}';
""")

                if int(result.splitlines()[-1]) > 0:
                    blocked = True
                    break

                time.sleep(0.1)

            self.assertTrue(
                blocked,
                "Connection request was not observed waiting"
            )

            revoker.stdin.write("COMMIT;\n")
            revoker.stdin.flush()

            # Confirm revocation became visible to other sessions.
            deadline = time.monotonic() + 5
            committed = False
            while time.monotonic() < deadline:
                status = query(f"""
SELECT status FROM public.guardianships
WHERE child_id = '{child_id}';
""")
                if status.splitlines()[-1] == "revoked":
                    committed = True
                    break
                time.sleep(0.1)

            self.assertTrue(
                committed,
                "Revocation commit not confirmed"
            )

            # Close revoker after committed status is visible.
            revoker.stdin.write("\\q\n")
            revoker.stdin.flush()
            revoker_output, revoker_errors = revoker.communicate(
                timeout=5
            )

            self.assertEqual(
                revoker.returncode, 0,
                f"Revoker process failed: {revoker_errors}"
            )

            output, errors = requester.communicate(timeout=10)

            self.assertNotEqual(
                requester.returncode, 0,
                "Requester unexpectedly succeeded"
            )
            self.assertIn(
                "Guardian not authorized",
                errors
            )

            remaining = query(f"""
SELECT count(*) FROM public.connection_requests
WHERE workspace_id = '{workspace_id}'
  AND child_id = '{child_id}';
""")

            self.assertEqual(remaining.splitlines()[-1], "0")

            print("PASS: Revocation-first authorization race")

        finally:
            def finish_cleanup():
                cleanup_errors = []

                for process in (requester, revoker):
                    if process is not None:
                        try:
                            if process.poll() is None:
                                if process.stdin is not None:
                                    process.stdin.write(
                                        "ROLLBACK;\n\\q\n"
                                    )
                                    process.stdin.flush()
                                process.communicate(timeout=5)
                        except Exception as exc:
                            cleanup_errors.append(
                                f"Process cleanup: {exc}"
                            )
                            process.kill()
                            process.communicate()

                if child_id:
                    try:
                        cleanup_test_records(child_id=child_id)
                    except Exception as exc:
                        cleanup_errors.append(
                            f"Child cleanup: {exc}"
                        )

                if workspace_id:
                    try:
                        cleanup_test_records(workspace_id=workspace_id)
                    except Exception as exc:
                        cleanup_errors.append(
                            f"Workspace cleanup: {exc}"
                        )

                if cleanup_errors:
                    raise AssertionError(
                        "Cleanup failures: " + "; ".join(cleanup_errors)
                    )

            self.addCleanup(finish_cleanup)



    def test_suspension_commits_before_authorization(self):
        workspace_id = None
        child_id = None
        revoker = None
        requester = None

        try:
            workspace_id = create_test_workspace()
            child_id = create_test_child()

            revoker = subprocess.Popen(
                PSQL,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            revoker_name = 'parentplus_revoker_' + uuid.uuid4().hex

            revoker.stdin.write(f"""
BEGIN;
SELECT set_config(
  'application_name',
  '{revoker_name}',
  false
);
WITH changed AS (
  UPDATE public.workspaces
  SET status = 'suspended'
  WHERE id = '{workspace_id}'
  RETURNING id
)
SELECT 'SUSPENSION_LOCKED:' || count(*)::text
FROM changed;
""")
            revoker.stdin.flush()

            found = False
            deadline = time.monotonic() + 5

            while time.monotonic() < deadline:
                ready, _, _ = select.select(
                    [revoker.stdout], [], [], 0.5
                )
                if ready:
                    line = revoker.stdout.readline().strip()
                    if line == "SUSPENSION_LOCKED:1":
                        found = True
                        break

            self.assertTrue(found, "Revocation lock not confirmed")

            session_name = 'parentplus_race_' + uuid.uuid4().hex

            requester_sql = f"""
BEGIN;
SELECT set_config(
  'application_name',
  '{session_name}',
  false
);
SET LOCAL ROLE authenticated;
SELECT set_config(
  'request.jwt.claim.sub',
  '{MEERA}', true
);
SELECT public.request_workspace_connection(
  '{workspace_id}',
  '{child_id}',
  '{uuid.uuid4()}'
);
COMMIT;
"""

            requester = subprocess.Popen(
                PSQL,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            requester.stdin.write(requester_sql)
            requester.stdin.close()
            requester.stdin = None

            blocked = False
            deadline = time.monotonic() + 5

            while time.monotonic() < deadline:
                result = query(f"""
SELECT count(*)
FROM pg_stat_activity requester
JOIN pg_stat_activity revoker
  ON revoker.pid = ANY(
    pg_blocking_pids(requester.pid)
  )
WHERE requester.datname = 'parentplus_test'
  AND requester.application_name = '{session_name}'
  AND requester.state = 'active'
  AND revoker.application_name = '{revoker_name}';
""")

                if int(result.splitlines()[-1]) > 0:
                    blocked = True
                    break

                time.sleep(0.1)

            self.assertTrue(
                blocked,
                "Connection request was not observed waiting"
            )

            revoker.stdin.write("COMMIT;\n")
            revoker.stdin.flush()

            # Confirm revocation became visible to other sessions.
            deadline = time.monotonic() + 5
            committed = False
            while time.monotonic() < deadline:
                status = query(f"""
SELECT status FROM public.workspaces
WHERE id = '{workspace_id}';
""")
                if status.splitlines()[-1] == "suspended":
                    committed = True
                    break
                time.sleep(0.1)

            self.assertTrue(
                committed,
                "Suspension commit not confirmed"
            )

            # Close revoker after committed status is visible.
            revoker.stdin.write("\\q\n")
            revoker.stdin.flush()
            revoker_output, revoker_errors = revoker.communicate(
                timeout=5
            )

            self.assertEqual(
                revoker.returncode, 0,
                f"Revoker process failed: {revoker_errors}"
            )

            output, errors = requester.communicate(timeout=10)

            self.assertNotEqual(
                requester.returncode, 0,
                "Requester unexpectedly succeeded"
            )
            self.assertIn(
                "Workspace unavailable",
                errors
            )

            remaining = query(f"""
SELECT count(*) FROM public.connection_requests
WHERE workspace_id = '{workspace_id}'
  AND child_id = '{child_id}';
""")

            self.assertEqual(remaining.splitlines()[-1], "0")

            print("PASS: Suspension-first authorization race")

        finally:
            def finish_cleanup():
                cleanup_errors = []

                for process in (requester, revoker):
                    if process is not None:
                        try:
                            if process.poll() is None:
                                if process.stdin is not None:
                                    process.stdin.write(
                                        "ROLLBACK;\n\\q\n"
                                    )
                                    process.stdin.flush()
                                process.communicate(timeout=5)
                        except Exception as exc:
                            cleanup_errors.append(
                                f"Process cleanup: {exc}"
                            )
                            process.kill()
                            process.communicate()

                if child_id:
                    try:
                        cleanup_test_records(child_id=child_id)
                    except Exception as exc:
                        cleanup_errors.append(
                            f"Child cleanup: {exc}"
                        )

                if workspace_id:
                    try:
                        cleanup_test_records(workspace_id=workspace_id)
                    except Exception as exc:
                        cleanup_errors.append(
                            f"Workspace cleanup: {exc}"
                        )

                if cleanup_errors:
                    raise AssertionError(
                        "Cleanup failures: " + "; ".join(cleanup_errors)
                    )

            self.addCleanup(finish_cleanup)



    def run_connection_first_race(self, target):
        self.assertIn(target, ("guardian", "workspace"))

        workspace_id = None
        child_id = None
        connector = None
        changer = None

        try:
            workspace_id = create_test_workspace()
            child_id = create_test_child()

            connector_name = "parentplus_connector_" + uuid.uuid4().hex
            changer_name = "parentplus_changer_" + uuid.uuid4().hex
            request_id = str(uuid.uuid4())

            connector = start_psql_session()
            connector.stdin.write(f"""
BEGIN;
SELECT set_config(
  'application_name', '{connector_name}', false
);
SET LOCAL ROLE authenticated;
SELECT set_config(
  'request.jwt.claim.sub', '{MEERA}', true
);
SELECT 'CONNECTION_ID:' ||
  public.request_workspace_connection(
    '{workspace_id}', '{child_id}', '{request_id}'
  )::text;
SELECT 'CONNECTION_READY';
""")
            connector.stdin.flush()

            self.assertTrue(
                wait_for_session_marker(
                    connector, "CONNECTION_READY"
                ),
                "Connection transaction not ready"
            )

            if target == "guardian":
                update_sql = f"""
WITH changed AS (
  UPDATE public.guardianships
  SET status = 'revoked'
  WHERE child_id = '{child_id}'
  RETURNING id
)
SELECT 'UPDATED_ROWS:' || count(*)::text FROM changed;
"""
                expected_status = "revoked"
                status_table = "public.guardianships"
                status_where = f"child_id = '{child_id}'"
            else:
                update_sql = f"""
WITH changed AS (
  UPDATE public.workspaces
  SET status = 'suspended'
  WHERE id = '{workspace_id}'
  RETURNING id
)
SELECT 'UPDATED_ROWS:' || count(*)::text FROM changed;
"""
                expected_status = "suspended"
                status_table = "public.workspaces"
                status_where = f"id = '{workspace_id}'"

            changer = start_psql_session()
            changer.stdin.write(f"""
BEGIN;
SELECT set_config(
  'application_name', '{changer_name}', false
);
{update_sql}
COMMIT;
SELECT 'CHANGE_COMPLETE';
""")
            changer.stdin.flush()

            self.assertTrue(
                wait_for_blocking_relationship(
                    changer_name, connector_name
                ),
                "Permission change was not blocked"
            )

            connector.stdin.write("COMMIT;\n")
            connector.stdin.flush()

            # Wait until the committed request is visible.
            deadline = time.monotonic() + 5
            committed = False
            while time.monotonic() < deadline:
                count = query(f"""
SELECT
  (SELECT count(*)
   FROM public.connection_requests
   WHERE workspace_id = '{workspace_id}'
     AND child_id = '{child_id}'
     AND guardian_user_id = '{MEERA}'
     AND initiated_by = '{MEERA}'
     AND creation_request_id = '{request_id}'
     AND status = 'pending'),
  (SELECT count(*)
   FROM public.connection_events e
   JOIN public.connection_requests r
     ON r.id = e.connection_request_id
   WHERE r.creation_request_id = '{request_id}'
     AND r.initiated_by = '{MEERA}'
     AND e.event_type = 'requested');
""")
                if count.splitlines()[-1] == "1|1":
                    committed = True
                    break
                time.sleep(0.1)

            self.assertTrue(
                committed, "Connection commit not confirmed"
            )

            self.assertTrue(
                wait_for_session_marker(
                    changer, "CHANGE_COMPLETE"
                ),
                "Permission change did not finish"
            )

            # Close the completed changer session and verify exit.
            changer.stdin.write("\\q\n")
            changer.stdin.flush()
            changer.wait(timeout=5)
            if hasattr(changer, "_marker_reader"):
                changer._marker_reader.join(timeout=2)

            self.assertEqual(
                changer.returncode, 0,
                "Permission changer process failed"
            )

            status = query(f"""
SELECT count(*) FROM {status_table}
WHERE {status_where}
  AND status = '{expected_status}';
""")
            self.assertEqual(
                status.splitlines()[-1], "1",
                "Expected exactly one updated permission record"
            )

            print(
                f"PASS: Connection-first {target} authorization race"
            )

        finally:
            def cleanup():
                errors = []

                for process in (changer, connector):
                    try:
                        close_psql_session(process)
                    except Exception as exc:
                        errors.append(str(exc))

                if child_id:
                    try:
                        cleanup_test_records(child_id=child_id)
                    except Exception as exc:
                        errors.append(str(exc))

                if workspace_id:
                    try:
                        cleanup_test_records(workspace_id=workspace_id)
                    except Exception as exc:
                        errors.append(str(exc))

                if errors:
                    raise AssertionError(
                        "Cleanup failures: " + "; ".join(errors)
                    )

            self.addCleanup(cleanup)

    def test_connection_first_guardian_revocation(self):
        self.run_connection_first_race("guardian")

    def test_connection_first_workspace_suspension(self):
        self.run_connection_first_race("workspace")


if __name__ == "__main__":
    unittest.main(verbosity=2)
