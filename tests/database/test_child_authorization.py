"""ParentPlus child authorization regression tests.

Requires disposable PostgreSQL database and migrations 001-007.
"""

import subprocess
import unittest


def run_sql(sql):
    result = subprocess.run(
        [
            "docker", "exec", "-i", "parentplus-pg-test",
            "psql", "-X", "-A", "-t", "-q",
            "-v", "ON_ERROR_STOP=1",
            "-U", "parentplus_test",
            "-d", "parentplus_test",
        ],
        input=sql,
        text=True,
        capture_output=True,
        timeout=30,
    )

    if result.returncode != 0:
        raise AssertionError(result.stderr.strip())

    return result.stdout.strip()


class ChildAuthorizationTests(unittest.TestCase):

    def test_anonymous_child_creation_denied(self):
        result = run_sql("""
SELECT has_function_privilege(
  'anon',
  'public.create_child(text,uuid)',
  'EXECUTE'
);
""")
        self.assertEqual(result, "f")

    def test_direct_child_insert_denied(self):
        result = run_sql("""
SELECT has_table_privilege(
  'authenticated',
  'public.children',
  'INSERT'
);
""")
        self.assertEqual(result, "f")

    def test_direct_guardianship_insert_denied(self):
        result = run_sql("""
SELECT has_table_privilege(
  'authenticated',
  'public.guardianships',
  'INSERT'
);
""")
        self.assertEqual(result, "f")


    def test_child_creation_idempotency(self):
        result = run_sql("""
BEGIN;
SET LOCAL ROLE authenticated;
SELECT set_config(
  'request.jwt.claim.sub',
  '11111111-1111-4111-8111-111111111111',
  true
);

CREATE TEMP TABLE child_test_results (
  attempt integer,
  child_id uuid
);

INSERT INTO child_test_results
SELECT 1, public.create_child(
  'Riya Regression Test',
  'eeeeeeee-5555-4555-8555-eeeeeeeeeeee'
);

INSERT INTO child_test_results
SELECT 2, public.create_child(
  'Riya Regression Test',
  'eeeeeeee-5555-4555-8555-eeeeeeeeeeee'
);

RESET ROLE;

SELECT
  count(*)::text || '|' ||
  count(DISTINCT child_id)::text
FROM child_test_results;

SELECT
  count(*)::text || '|' ||
  count(g.id)::text
FROM public.children c
JOIN public.guardianships g ON g.child_id = c.id
WHERE c.creation_request_id =
  'eeeeeeee-5555-4555-8555-eeeeeeeeeeee'
AND g.guardian_user_id =
  '11111111-1111-4111-8111-111111111111'
AND g.status = 'provisional'
AND g.verification_level = 'self_declared';

ROLLBACK;
""")

        lines = result.splitlines()
        self.assertEqual(lines[-2], "2|1")
        self.assertEqual(lines[-1], "1|1")


    def test_child_request_conflict(self):
        result = run_sql("""
BEGIN;
SET LOCAL ROLE authenticated;
SELECT set_config(
  'request.jwt.claim.sub',
  '11111111-1111-4111-8111-111111111111',
  true
);

SELECT public.create_child(
  'Riya',
  'ffffffff-5555-4555-8555-ffffffffffff'
);

DO $test$
BEGIN
  BEGIN
    PERFORM public.create_child(
      'Aarav',
      'ffffffff-5555-4555-8555-ffffffffffff'
    );
  EXCEPTION
    WHEN raise_exception THEN
      IF SQLERRM = 'Request ID reused with different child details' THEN
        RETURN;
      END IF;
      RAISE;
  END;
  RAISE EXCEPTION 'FAIL: Conflicting request accepted';
END
$test$;

RESET ROLE;

SELECT
  c.display_name || '|' ||
  count(DISTINCT c.id)::text || '|' ||
  count(g.id)::text
FROM public.children c
JOIN public.guardianships g ON g.child_id = c.id
WHERE c.creation_request_id =
  'ffffffff-5555-4555-8555-ffffffffffff'
GROUP BY c.display_name;

ROLLBACK;
""")

        self.assertEqual(result.splitlines()[-1], "Riya|1|1")


    def test_child_creation_atomic_failure(self):
        result = run_sql("""
BEGIN;

CREATE FUNCTION public.test_child_guardian_failure()
RETURNS trigger
LANGUAGE plpgsql
AS $test$
BEGIN
  RAISE EXCEPTION 'Simulated guardian failure';
END
$test$;

CREATE TRIGGER test_child_guardian_failure_trigger
BEFORE INSERT ON public.guardianships
FOR EACH ROW
EXECUTE FUNCTION public.test_child_guardian_failure();

SET LOCAL ROLE authenticated;
SELECT set_config(
  'request.jwt.claim.sub',
  '11111111-1111-4111-8111-111111111111',
  true
);

DO $test$
BEGIN
  BEGIN
    PERFORM public.create_child(
      'Riya Atomic Regression',
      'aaaaaaaa-6666-4666-8666-aaaaaaaaaaaa'
    );
  EXCEPTION
    WHEN raise_exception THEN
      IF SQLERRM = 'Simulated guardian failure' THEN
        RETURN;
      END IF;
      RAISE;
  END;

  RAISE EXCEPTION 'FAIL: Expected guardianship failure';
END
$test$;

RESET ROLE;

SELECT
  count(*)::text || '|' ||
  (SELECT count(*) FROM public.guardianships g
   JOIN public.children c ON c.id = g.child_id
   WHERE c.creation_request_id =
     'aaaaaaaa-6666-4666-8666-aaaaaaaaaaaa')::text
FROM public.children
WHERE creation_request_id =
  'aaaaaaaa-6666-4666-8666-aaaaaaaaaaaa';

ROLLBACK;
""")
        self.assertEqual(result.splitlines()[-1], "0|0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
