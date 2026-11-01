"""Concurrent child creation test for disposable ParentPlus PostgreSQL."""

import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor

CONTAINER = "parentplus-pg-test"
USER_ID = "11111111-1111-4111-8111-111111111111"
CHILD_NAME = "Riya Concurrent Test"


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


def create_child(request_id):
    sql = f"""
BEGIN;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{USER_ID}', true);
SELECT public.create_child('{CHILD_NAME}', '{request_id}');
COMMIT;
"""
    output = query(sql)
    ids = [
        line.strip()
        for line in output.splitlines()
        if line.strip() != USER_ID
    ]
    if len(ids) != 1:
        raise RuntimeError(f"Unexpected child response: {output}")
    return str(uuid.UUID(ids[0]))


def cleanup(request_id):
    sql = f"""
BEGIN;
DELETE FROM public.guardianships
WHERE child_id IN (
  SELECT id FROM public.children
  WHERE created_by = '{USER_ID}'
    AND creation_request_id = '{request_id}'
    AND display_name = '{CHILD_NAME}'
);
DELETE FROM public.children
WHERE created_by = '{USER_ID}'
  AND creation_request_id = '{request_id}'
  AND display_name = '{CHILD_NAME}';
COMMIT;
"""
    query(sql)


def main():
    request_id = str(uuid.uuid4())
    print("Test request ID:", request_id)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(create_child, request_id)
                for _ in range(2)
            ]
            results = [future.result() for future in futures]

        counts = query(f"""
SELECT
  (SELECT count(*) FROM public.children
   WHERE created_by = '{USER_ID}'
     AND creation_request_id = '{request_id}'),
  (SELECT count(*)
   FROM public.guardianships g
   JOIN public.children c ON c.id = g.child_id
   WHERE c.created_by = '{USER_ID}'
     AND c.creation_request_id = '{request_id}'
     AND g.guardian_user_id = '{USER_ID}'
     AND g.status = 'provisional'
     AND g.verification_level = 'self_declared');
""")

        child_count, guardian_count = counts.split("|")

        print("Returned child IDs:", results)
        print("Child records:", child_count)
        print("Provisional guardianships:", guardian_count)

        assert len(set(results)) == 1, "Different child IDs returned"
        assert child_count == "1", "Duplicate child identity"
        assert guardian_count == "1", "Incorrect guardianship count"

        print("PASS: Concurrent child creation")

    finally:
        cleanup(request_id)
        print("PASS: Test cleanup completed")


if __name__ == "__main__":
    main()
