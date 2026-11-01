"""Repeatable ParentPlus workspace concurrency test.

Requires the disposable parentplus-pg-test PostgreSQL container.
Uses fictional data only.
"""

import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor

CONTAINER = "parentplus-pg-test"
USER_ID = "11111111-1111-4111-8111-111111111111"


def query(sql):
    result = subprocess.run(
        [
            "docker", "exec", "-i", CONTAINER,
            "psql", "-X", "-A", "-t", "-q",
            "-v", "ON_ERROR_STOP=1",
            "-U", "parentplus_test",
            "-d", "parentplus_test",
        ],
        input=sql,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    return result.stdout.strip()


def create_workspace(request_id):
    sql = f"""
BEGIN;
SET LOCAL ROLE authenticated;
SELECT set_config(
  'request.jwt.claim.sub',
  '{USER_ID}',
  true
);
SELECT public.create_workspace(
  'Meera Concurrent Test',
  'academy',
  '{request_id}'
);
COMMIT;
"""
    result = query(sql)

    ids = [
        line.strip()
        for line in result.splitlines()
        if line.strip() != USER_ID
    ]

    if len(ids) != 1:
        raise RuntimeError(f"Unexpected workspace response: {result}")

    return str(uuid.UUID(ids[0]))


def cleanup(request_id):
    sql = f"""
BEGIN;

DELETE FROM public.workspace_memberships
WHERE workspace_id IN (
  SELECT id FROM public.workspaces
  WHERE created_by = '{USER_ID}'
    AND creation_request_id = '{request_id}'
    AND name = 'Meera Concurrent Test'
);

DELETE FROM public.workspaces
WHERE created_by = '{USER_ID}'
  AND creation_request_id = '{request_id}'
  AND name = 'Meera Concurrent Test';

COMMIT;
"""
    query(sql)


def main():
    request_id = str(uuid.uuid4())
    print("Test request ID:", request_id)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(create_workspace, request_id)
                for _ in range(2)
            ]
            results = [future.result() for future in futures]

        workspace_count = query(f"""
SELECT count(*) FROM public.workspaces
WHERE created_by = '{USER_ID}'
AND creation_request_id = '{request_id}';
""")

        owner_count = query(f"""
SELECT count(*)
FROM public.workspace_memberships m
JOIN public.workspaces w ON w.id = m.workspace_id
WHERE w.created_by = '{USER_ID}'
AND w.creation_request_id = '{request_id}'
AND m.role = 'owner';
""")

        print("Returned workspace IDs:", results)
        print("Workspace records:", workspace_count)
        print("Owner memberships:", owner_count)

        assert len(set(results)) == 1, "Different workspace IDs returned"
        assert workspace_count == "1", "Duplicate workspace detected"
        assert owner_count == "1", "Incorrect Owner membership count"

        print("PASS: Concurrent workspace creation")

    finally:
        cleanup(request_id)
        print("PASS: Test cleanup completed")


if __name__ == "__main__":
    main()
