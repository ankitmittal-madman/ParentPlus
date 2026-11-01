"""ParentPlus M3 concurrent approval test. Local PostgreSQL only."""

import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor

CONTAINER = "parentplus-pg-test"
MEERA = "11111111-1111-4111-8111-111111111111"
RAHUL = "22222222-2222-4222-8222-222222222222"

PSQL = [
    "docker", "exec", "-i", CONTAINER,
    "psql", "-X", "-A", "-t", "-q",
    "-v", "ON_ERROR_STOP=1",
    "-U", "parentplus_test", "-d", "parentplus_test",
]


def query(sql):
    result = subprocess.run(
        PSQL, input=sql, text=True,
        capture_output=True, timeout=30,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def as_user(user_id, statement):
    output = query(f"""
BEGIN;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{user_id}', true);
{statement}
COMMIT;
""")
    return output.splitlines()[-1]


def main():
    workspace_id = None
    child_id = None

    try:
        workspace_id = as_user(RAHUL, f"""
SELECT public.create_workspace(
  'M3 Concurrent Approval Academy',
  'academy',
  '{uuid.uuid4()}'
);
""")

        child_id = as_user(MEERA, f"""
SELECT public.create_child(
  'M3 Concurrent Approval Child',
  '{uuid.uuid4()}'
);
""")

        request_id = as_user(MEERA, f"""
SELECT public.request_workspace_connection(
  '{workspace_id}',
  '{child_id}',
  '{uuid.uuid4()}'
);
""")

        def approve():
            return as_user(RAHUL, f"""
SELECT public.approve_guardian_connection(
  '{request_id}'
);
""")

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(approve) for _ in range(2)]
            results = [future.result(timeout=30) for future in futures]

        if results[0] != results[1]:
            raise AssertionError("Concurrent approvals returned different IDs")

        counts = query(f"""
SELECT
  (SELECT count(*) FROM public.connection_requests
   WHERE id = '{request_id}' AND status = 'approved'),
  (SELECT count(*) FROM public.workspace_children
   WHERE workspace_id = '{workspace_id}'
     AND child_id = '{child_id}'
     AND status = 'active'),
  (SELECT count(*) FROM public.connection_events
   WHERE connection_request_id = '{request_id}'
     AND event_type = 'approved');
""").split("|")

        if counts != ["1", "1", "1"]:
            raise AssertionError(f"Unexpected counts: {counts}")

        print("PASS: Both approvals returned same relationship")
        print("PASS: One approved request")
        print("PASS: One active relationship")
        print("PASS: One approval audit event")

    finally:
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

        print("PASS: Test cleanup completed")


if __name__ == "__main__":
    main()
