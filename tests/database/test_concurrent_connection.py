"""ParentPlus guardian connection concurrency regression test.

Requires disposable parentplus-pg-test PostgreSQL container.
Uses fictional test users only.
"""

import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor

CONTAINER = "parentplus-pg-test"
MEERA = "11111111-1111-4111-8111-111111111111"
RAHUL = "22222222-2222-4222-8222-222222222222"


def query(sql):
    result = subprocess.run(
        [
            "docker", "exec", "-i", CONTAINER,
            "psql", "-X", "-A", "-t", "-q",
            "-v", "ON_ERROR_STOP=1",
            "-U", "parentplus_test", "-d", "parentplus_test",
        ],
        input=sql,
        text=True,
        capture_output=True,
        timeout=30,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def as_user(user_id, statement):
    return query(f"""
BEGIN;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{user_id}', true);
{statement}
COMMIT;
""")


def create_workspace(request_id):
    output = as_user(RAHUL, f"""
SELECT public.create_workspace(
  'Concurrent Connection Academy',
  'academy',
  '{request_id}'
);
""")
    return output.splitlines()[-1]


def create_child(request_id):
    output = as_user(MEERA, f"""
SELECT public.create_child(
  'Riya Concurrent Connection Test',
  '{request_id}'
);
""")
    return output.splitlines()[-1]


def request_connection(workspace_id, child_id, request_id):
    output = as_user(MEERA, f"""
SELECT public.request_workspace_connection(
  '{workspace_id}', '{child_id}', '{request_id}'
);
""")
    return output.splitlines()[-1]


def main():
    workspace_request_id = str(uuid.uuid4())
    child_request_id = str(uuid.uuid4())
    request_ids = [str(uuid.uuid4()), str(uuid.uuid4())]

    workspace_id = None
    child_id = None

    try:
        workspace_id = create_workspace(workspace_request_id)
        child_id = create_child(child_request_id)

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(
                    request_connection,
                    workspace_id,
                    child_id,
                    request_id,
                )
                for request_id in request_ids
            ]
            results = [future.result() for future in futures]

        counts = query(f"""
SELECT
  (SELECT count(*) FROM public.connection_requests
   WHERE workspace_id = '{workspace_id}'
     AND child_id = '{child_id}'),
  (SELECT count(*) FROM public.connection_events e
   JOIN public.connection_requests r
     ON r.id = e.connection_request_id
   WHERE r.workspace_id = '{workspace_id}'
     AND r.child_id = '{child_id}'
     AND e.event_type = 'requested');
""").split("|")

        print("Returned request IDs:", results)
        print("Connection requests:", counts[0])
        print("Requested audit events:", counts[1])

        assert len(set(results)) == 1
        assert counts == ["1", "1"]

        print("PASS: Concurrent connection initiation")

    finally:
        if child_id:
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
            print("PASS: Child test records cleaned up")

        if workspace_id:
            query(f"""
BEGIN;
DELETE FROM public.workspace_memberships
WHERE workspace_id = '{workspace_id}';
DELETE FROM public.workspaces
WHERE id = '{workspace_id}';
COMMIT;
""")
            print("PASS: Workspace test records cleaned up")


if __name__ == "__main__":
    main()
