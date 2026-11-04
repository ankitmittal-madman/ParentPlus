"""ParentPlus child authorization regression tests.

Requires disposable PostgreSQL database and migrations 001-007.
"""

import subprocess
from tests.database.container_config import get_test_container
import unittest
import uuid
from tests.database.test_concurrent_authorization import query, start_psql_session, wait_for_session_marker, wait_for_blocking_relationship, close_psql_session


def run_sql(sql, *, enable_creation=False):
    # Enable only inside the rolled-back transaction for existing behaviour tests.
    if enable_creation and 'public.create_child(' in sql and 'BEGIN;' in sql:
        sql = sql.replace('BEGIN;', 'BEGIN; GRANT EXECUTE ON FUNCTION public.create_child(text,uuid) TO authenticated; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;', 1)
    result = subprocess.run(
        [
            "docker", "exec", "-i", get_test_container(),
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


def run_sql_enabled(sql):
    """Enable creation explicitly inside this synthetic transaction only."""
    return run_sql(sql, enable_creation=True)


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
        result = run_sql_enabled("""
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
        result = run_sql_enabled("""
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
        result = run_sql_enabled("""
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

    def test_created_child_list_is_default_off_and_private(self):
        result = run_sql("""
BEGIN; SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM * FROM public.app_list_created_children(); RAISE EXCEPTION 'disabled read allowed'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
RESET ROLE; SET LOCAL ROLE anon;
DO $$ BEGIN BEGIN PERFORM * FROM public.app_list_created_children(); RAISE EXCEPTION 'anon read allowed'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
RESET ROLE;
SELECT NOT has_function_privilege('anon','public.app_list_created_children()','EXECUTE')
 AND has_function_privilege('authenticated','public.app_list_created_children()','EXECUTE')
 AND NOT has_table_privilege('authenticated','public.parent_child_read_controls','SELECT')
 AND NOT has_table_privilege('authenticated','public.parent_child_read_controls','UPDATE')
 AND NOT has_table_privilege('authenticated','public.children','SELECT')
 AND (SELECT p.prosecdef AND p.proconfig @> ARRAY['search_path=""'] AND pg_catalog.pg_get_userbyid(p.proowner)=current_user
      FROM pg_catalog.pg_proc p WHERE p.oid='public.app_list_created_children()'::regprocedure);
ROLLBACK;
""")
        self.assertEqual(result.splitlines()[-1], "t")

    def test_created_child_list_filters_ownership_and_guardian_status(self):
        result = run_sql_enabled("""
BEGIN; UPDATE public.parent_child_read_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE my_child AS SELECT public.create_child('Own child','aaaaaaaa-7777-4777-8777-aaaaaaaaaaaa') AS id;
CREATE TEMP TABLE revoked_child AS SELECT public.create_child('Revoked child','aaaaaaaa-8888-4888-8888-aaaaaaaaaaaa') AS id;
CREATE TEMP TABLE disputed_child AS SELECT public.create_child('Disputed child','aaaaaaaa-9999-4999-8999-aaaaaaaaaaaa') AS id;
CREATE TEMP TABLE missing_child AS SELECT public.create_child('Missing guardian','aaaaaaaa-0000-4000-8000-aaaaaaaaaaaa') AS id;
CREATE TEMP TABLE active_child AS SELECT public.create_child('Active child','aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa') AS id;
RESET ROLE; UPDATE public.guardianships SET status='revoked' WHERE child_id=(SELECT id FROM revoked_child);
UPDATE public.guardianships SET status='disputed' WHERE child_id=(SELECT id FROM disputed_child);
DELETE FROM public.guardianships WHERE child_id=(SELECT id FROM missing_child);
UPDATE public.guardianships SET status='active' WHERE child_id=(SELECT id FROM active_child);
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','22222222-2222-4222-8222-222222222222',true);
CREATE TEMP TABLE other_child AS SELECT public.create_child('Other child','bbbbbbbb-7777-4777-8777-bbbbbbbbbbbb') AS id;
RESET ROLE; INSERT INTO public.guardianships (child_id,guardian_user_id,status,verification_level)
VALUES ((SELECT id FROM other_child),'11111111-1111-4111-8111-111111111111','active','self_declared');
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
SELECT count(*) || ':' || string_agg(display_name,',' ORDER BY display_name) FROM public.app_list_created_children();
ROLLBACK;
""")
        self.assertEqual(result.splitlines()[-1], "2:Active child,Own child")

    def test_created_child_list_rejects_missing_identity(self):
        result = run_sql("""
BEGIN; UPDATE public.parent_child_read_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','',true);
DO $$ BEGIN BEGIN PERFORM * FROM public.app_list_created_children(); RAISE EXCEPTION 'missing identity allowed'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
SELECT 'denied'; ROLLBACK;
""")
        self.assertEqual(result.splitlines()[-1], "denied")

    def test_created_child_list_refuses_silent_truncation(self):
        result = run_sql("""
BEGIN; UPDATE public.parent_child_read_controls SET enabled=true WHERE id=true;
INSERT INTO public.children (id,display_name,created_by)
SELECT gen_random_uuid(),'Synthetic child','11111111-1111-4111-8111-111111111111' FROM generate_series(1,101);
INSERT INTO public.guardianships (child_id,guardian_user_id,status,verification_level)
SELECT id,created_by,'provisional','self_declared' FROM public.children WHERE display_name='Synthetic child';
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM * FROM public.app_list_created_children(); RAISE EXCEPTION 'silent truncation'; EXCEPTION WHEN program_limit_exceeded THEN NULL; END; END $$;
RESET ROLE;
DELETE FROM public.guardianships WHERE child_id=(SELECT id FROM public.children WHERE display_name='Synthetic child' ORDER BY id LIMIT 1);
DELETE FROM public.children WHERE display_name='Synthetic child' AND NOT EXISTS (SELECT 1 FROM public.guardianships g WHERE g.child_id=children.id);
SET LOCAL ROLE authenticated; SELECT count(*) FROM public.app_list_created_children(); ROLLBACK;
""")
        self.assertEqual(result.splitlines()[-1], "100")

    def run_created_child_read_race(self, change_first, target):
        child = str(uuid.uuid4())
        first_name = "child_read_first_" + uuid.uuid4().hex
        second_name = "child_read_second_" + uuid.uuid4().hex
        self.addCleanup(query, f"BEGIN; DELETE FROM public.guardianships WHERE child_id='{child}'; DELETE FROM public.children WHERE id='{child}'; UPDATE public.parent_child_read_controls SET enabled=false WHERE id=true; COMMIT;")
        query(f"""BEGIN; UPDATE public.parent_child_read_controls SET enabled=true WHERE id=true;
INSERT INTO public.children (id,display_name,created_by) VALUES ('{child}','Synthetic race child','11111111-1111-4111-8111-111111111111');
INSERT INTO public.guardianships (child_id,guardian_user_id,status,verification_level) VALUES ('{child}','11111111-1111-4111-8111-111111111111','provisional','self_declared'); COMMIT;""")
        first = second = None
        read = "SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true); SELECT 'ROWS:' || count(*) FROM public.app_list_created_children();\n"
        change = (f"UPDATE public.guardianships SET status='revoked' WHERE child_id='{child}';\n" if target == "guardian" else "UPDATE public.parent_child_read_controls SET enabled=false WHERE id=true;\n")
        try:
            first = start_psql_session()
            second = start_psql_session()
            for process, name in ((first, first_name), (second, second_name)):
                process.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{name}',false);\n")
            first.stdin.write(change if change_first else read); first.stdin.write("SELECT 'FIRST_READY';\n"); first.stdin.flush()
            if not change_first: self.assertTrue(wait_for_session_marker(first, "ROWS:1"))
            self.assertTrue(wait_for_session_marker(first, "FIRST_READY"))
            second.stdin.write(read if change_first else change); second.stdin.write("COMMIT; SELECT 'SECOND_DONE';\n"); second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name, first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_DONE';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, "FIRST_DONE"))
            if change_first and target == "control":
                second.stdin.close(); second.stdin = None
                _, errors = second.communicate(timeout=15)
                self.assertNotEqual(second.returncode, 0); self.assertIn("Child profiles unavailable", errors)
            else:
                if change_first: self.assertTrue(wait_for_session_marker(second, "ROWS:0"))
                self.assertTrue(wait_for_session_marker(second, "SECOND_DONE"))
        finally:
            if second is not None: close_psql_session(second)
            if first is not None: close_psql_session(first)

    def test_created_child_read_after_guardian_revocation(self):
        self.run_created_child_read_race(True, "guardian")

    def test_created_child_read_before_guardian_revocation(self):
        self.run_created_child_read_race(False, "guardian")

    def test_created_child_read_after_control_disabled(self):
        self.run_created_child_read_race(True, "control")

    def test_created_child_read_before_control_disabled(self):
        self.run_created_child_read_race(False, "control")

    def test_child_creation_retry_does_not_restore_deleted_guardianship(self):
        result = run_sql_enabled("""
BEGIN; SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE saved_child AS SELECT public.create_child('Synthetic child','cccccccc-1111-4111-8111-cccccccccccc') AS id;
RESET ROLE; DELETE FROM public.guardianships WHERE child_id=(SELECT id FROM saved_child);
SET LOCAL ROLE authenticated;
DO $$ BEGIN BEGIN PERFORM public.create_child('Synthetic child','cccccccc-1111-4111-8111-cccccccccccc'); RAISE EXCEPTION 'deleted guardian retry accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
RESET ROLE; SELECT count(*) FROM public.guardianships WHERE child_id=(SELECT id FROM saved_child); ROLLBACK;
""")
        self.assertEqual(result.splitlines()[-1], "0")

    def test_child_creation_retry_denies_revoked_and_disputed_guardianship(self):
        result = run_sql_enabled("""
BEGIN; SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
CREATE TEMP TABLE saved_child AS SELECT public.create_child('Synthetic child','cccccccc-2222-4222-8222-cccccccccccc') AS id;
RESET ROLE; UPDATE public.guardianships SET status='revoked' WHERE child_id=(SELECT id FROM saved_child);
SET LOCAL ROLE authenticated;
DO $$ BEGIN BEGIN PERFORM public.create_child('Synthetic child','cccccccc-2222-4222-8222-cccccccccccc'); RAISE EXCEPTION 'revoked guardian retry accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
DO $$ BEGIN BEGIN PERFORM public.create_child('Changed child','cccccccc-2222-4222-8222-cccccccccccc'); RAISE EXCEPTION 'revoked guardian learned details'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
RESET ROLE; UPDATE public.guardianships SET status='disputed' WHERE child_id=(SELECT id FROM saved_child);
SET LOCAL ROLE authenticated;
DO $$ BEGIN BEGIN PERFORM public.create_child('Synthetic child','cccccccc-2222-4222-8222-cccccccccccc'); RAISE EXCEPTION 'disputed guardian retry accepted'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
RESET ROLE; SELECT status FROM public.guardianships WHERE child_id=(SELECT id FROM saved_child); ROLLBACK;
""")
        self.assertEqual(result.splitlines()[-1], "disputed")

    def run_child_retry_guardian_delete_race(self, delete_first):
        child, request = str(uuid.uuid4()), str(uuid.uuid4())
        first_name, second_name = "child_retry_first_"+uuid.uuid4().hex, "child_retry_second_"+uuid.uuid4().hex
        self.addCleanup(query, f"BEGIN; DELETE FROM public.guardianships WHERE child_id='{child}'; DELETE FROM public.children WHERE id='{child}'; UPDATE public.child_creation_controls SET enabled=false WHERE id=true; REVOKE EXECUTE ON FUNCTION public.create_child(text,uuid) FROM authenticated; COMMIT;")
        query(f"""BEGIN; GRANT EXECUTE ON FUNCTION public.create_child(text,uuid) TO authenticated; UPDATE public.child_creation_controls SET enabled=true WHERE id=true; INSERT INTO public.children (id,display_name,created_by,creation_request_id)
VALUES ('{child}','Synthetic race child','11111111-1111-4111-8111-111111111111','{request}');
INSERT INTO public.guardianships (child_id,guardian_user_id,status,verification_level)
VALUES ('{child}','11111111-1111-4111-8111-111111111111','provisional','self_declared'); COMMIT;""")
        first = second = None
        retry = f"SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true); SELECT 'CHILD:' || public.create_child('Synthetic race child','{request}')::text;\n"
        delete = f"DELETE FROM public.guardianships WHERE child_id='{child}';\n"
        try:
            first = start_psql_session(); second = start_psql_session()
            for process, name in ((first, first_name), (second, second_name)):
                process.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{name}',false);\n")
            first.stdin.write(delete if delete_first else retry); first.stdin.write("SELECT 'FIRST_READY';\n"); first.stdin.flush()
            if not delete_first: self.assertTrue(wait_for_session_marker(first, 'CHILD:'+child))
            self.assertTrue(wait_for_session_marker(first, 'FIRST_READY'))
            second.stdin.write(retry if delete_first else delete); second.stdin.write("COMMIT; SELECT 'SECOND_DONE';\n"); second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name, first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_DONE';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, 'FIRST_DONE'))
            if delete_first:
                second.stdin.close(); second.stdin = None
                _, errors = second.communicate(timeout=15)
                self.assertNotEqual(second.returncode, 0); self.assertIn('Child creation unavailable', errors)
            else:
                self.assertTrue(wait_for_session_marker(second, 'SECOND_DONE'))
            self.assertEqual(query(f"SELECT count(*) FROM public.guardianships WHERE child_id='{child}';"), '0')
        finally:
            if second is not None: close_psql_session(second)
            if first is not None: close_psql_session(first)

    def test_child_retry_after_guardianship_deletion_is_denied(self):
        self.run_child_retry_guardian_delete_race(True)

    def test_guardianship_deletion_waits_for_child_retry(self):
        self.run_child_retry_guardian_delete_race(False)

    def test_child_creation_replay_guard_privileges_and_owner(self):
        result = run_sql("""
SELECT p.prosecdef AND p.proconfig @> ARRAY['search_path=""']
 AND pg_catalog.pg_get_userbyid(p.proowner)=current_user
 AND NOT has_function_privilege('authenticated',p.oid,'EXECUTE')
 AND NOT has_function_privilege('anon',p.oid,'EXECUTE')
FROM pg_catalog.pg_proc p WHERE p.oid='public.create_child(text,uuid)'::regprocedure;
""")
        self.assertEqual(result, "t")

    def test_child_creation_database_control_denies_authenticated_creation(self):
        result = run_sql("""
BEGIN; GRANT EXECUTE ON FUNCTION public.create_child(text,uuid) TO authenticated; SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM public.create_child('Synthetic child','dddddddd-1111-4111-8111-dddddddddddd'); RAISE EXCEPTION 'disabled creation allowed'; EXCEPTION WHEN insufficient_privilege THEN IF SQLERRM <> 'Child creation unavailable' THEN RAISE; END IF; END; END $$;
RESET ROLE; SELECT count(*) FROM public.children WHERE creation_request_id='dddddddd-1111-4111-8111-dddddddddddd'; ROLLBACK;
""", enable_creation=False)
        self.assertEqual(result.splitlines()[-1], "0")

    def test_child_creation_control_is_private_and_default_off(self):
        result = run_sql("""
BEGIN; SET LOCAL ROLE authenticated;
DO $$ BEGIN BEGIN UPDATE public.child_creation_controls SET enabled=true WHERE id=true; RAISE EXCEPTION 'control update allowed'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
RESET ROLE; ROLLBACK;
SELECT (SELECT count(*)=1 AND bool_and(id AND NOT enabled) FROM public.child_creation_controls)
 AND NOT has_table_privilege('authenticated','public.child_creation_controls','SELECT')
 AND NOT has_table_privilege('authenticated','public.child_creation_controls','UPDATE')
 AND NOT has_table_privilege('anon','public.child_creation_controls','UPDATE');
""")
        self.assertEqual(result, "t")

    def test_child_creation_control_missing_fails_closed(self):
        result = run_sql("""
BEGIN; GRANT EXECUTE ON FUNCTION public.create_child(text,uuid) TO authenticated; DELETE FROM public.child_creation_controls WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
DO $$ BEGIN BEGIN PERFORM public.create_child('Synthetic child','dddddddd-2222-4222-8222-dddddddddddd'); RAISE EXCEPTION 'missing control allowed'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
RESET ROLE; SELECT count(*) FROM public.children WHERE creation_request_id='dddddddd-2222-4222-8222-dddddddddddd'; ROLLBACK;
""", enable_creation=False)
        self.assertEqual(result.splitlines()[-1], "0")

    def test_child_creation_control_disabled_blocks_existing_retry(self):
        result = run_sql("""
BEGIN; GRANT EXECUTE ON FUNCTION public.create_child(text,uuid) TO authenticated; UPDATE public.child_creation_controls SET enabled=true WHERE id=true;
SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true);
SELECT public.create_child('Synthetic child','dddddddd-3333-4333-8333-dddddddddddd');
RESET ROLE; UPDATE public.child_creation_controls SET enabled=false WHERE id=true;
SET LOCAL ROLE authenticated;
DO $$ BEGIN BEGIN PERFORM public.create_child('Synthetic child','dddddddd-3333-4333-8333-dddddddddddd'); RAISE EXCEPTION 'disabled retry allowed'; EXCEPTION WHEN insufficient_privilege THEN NULL; END; END $$;
RESET ROLE; SELECT count(*) FROM public.children WHERE creation_request_id='dddddddd-3333-4333-8333-dddddddddddd'; ROLLBACK;
""", enable_creation=False)
        self.assertEqual(result.splitlines()[-1], "1")

    def run_child_creation_control_race(self, disable_first):
        request = str(uuid.uuid4())
        first_name, second_name = "child_gate_first_"+uuid.uuid4().hex, "child_gate_second_"+uuid.uuid4().hex
        self.addCleanup(query, f"BEGIN; DELETE FROM public.guardianships WHERE child_id IN (SELECT id FROM public.children WHERE creation_request_id='{request}'); DELETE FROM public.children WHERE creation_request_id='{request}'; UPDATE public.child_creation_controls SET enabled=false WHERE id=true; REVOKE EXECUTE ON FUNCTION public.create_child(text,uuid) FROM authenticated; COMMIT;")
        query("BEGIN; GRANT EXECUTE ON FUNCTION public.create_child(text,uuid) TO authenticated; UPDATE public.child_creation_controls SET enabled=true WHERE id=true; COMMIT;")
        first = second = None
        create = f"SET LOCAL ROLE authenticated; SELECT set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',true); SELECT public.create_child('Synthetic race child','{request}');\n"
        disable = "UPDATE public.child_creation_controls SET enabled=false WHERE id=true;\n"
        try:
            first = start_psql_session(); second = start_psql_session()
            for process, name in ((first, first_name), (second, second_name)):
                process.stdin.write(f"BEGIN; SET LOCAL lock_timeout='10s'; SELECT set_config('application_name','{name}',false);\n")
            first.stdin.write(disable if disable_first else create); first.stdin.write("SELECT 'FIRST_READY';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, "FIRST_READY"))
            second.stdin.write(create if disable_first else disable); second.stdin.write("COMMIT; SELECT 'SECOND_DONE';\n"); second.stdin.flush()
            self.assertTrue(wait_for_blocking_relationship(second_name, first_name))
            first.stdin.write("COMMIT; SELECT 'FIRST_DONE';\n"); first.stdin.flush()
            self.assertTrue(wait_for_session_marker(first, "FIRST_DONE"))
            if disable_first:
                second.stdin.close(); second.stdin = None
                _, errors = second.communicate(timeout=15)
                self.assertNotEqual(second.returncode, 0); self.assertIn("Child creation unavailable", errors)
            else:
                self.assertTrue(wait_for_session_marker(second, "SECOND_DONE"))
            self.assertEqual(query(f"SELECT count(*) FROM public.children WHERE creation_request_id='{request}';"), '0' if disable_first else '1')
        finally:
            if second is not None: close_psql_session(second)
            if first is not None: close_psql_session(first)

    def test_child_creation_control_disabled_before_write(self):
        self.run_child_creation_control_race(True)

    def test_child_creation_completes_before_control_disabled(self):
        self.run_child_creation_control_race(False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
