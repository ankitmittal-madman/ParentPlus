"""ParentPlus authorization regression tests."""

import subprocess
from tests.database.container_config import get_test_container
import unittest

MEERA = "11111111-1111-4111-8111-111111111111"
RAHUL = "22222222-2222-4222-8222-222222222222"


def run_sql(sql):
    result = subprocess.run(
        [
            "docker", "exec", "-i", get_test_container(),
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
        raise AssertionError(result.stderr)
    return result.stdout.strip()


def run_sql_with_notices(sql):
    result = subprocess.run(
        [
            "docker", "exec", "-i", get_test_container(),
            "psql", "-X", "-A", "-t", "-q",
            "-v", "ON_ERROR_STOP=1",
            "-U", "parentplus_test", "-d", "parentplus_test",
        ],
        input=sql,
        text=True,
        capture_output=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return result.stderr


class AuthorizationTests(unittest.TestCase):
    def test_workspace_receipt_failure_rolls_back_workspace_and_owner(self):
        notice = run_sql_with_notices(f"""
BEGIN;
CREATE FUNCTION pg_temp.fail_workspace_receipt() RETURNS trigger LANGUAGE plpgsql AS $body$
BEGIN RAISE EXCEPTION 'synthetic workspace receipt failure'; END $body$;
CREATE TRIGGER fail_workspace_receipt BEFORE INSERT ON public.workspace_creation_receipts
FOR EACH ROW EXECUTE FUNCTION pg_temp.fail_workspace_receipt();
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub','{MEERA}',true);
DO $test$
DECLARE failed boolean := false;
BEGIN
  BEGIN
    PERFORM public.create_workspace('Atomic Academy','academy','eeeeeeee-2222-4222-8222-eeeeeeeeeeee');
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM='synthetic workspace receipt failure' THEN failed:=true; ELSE RAISE; END IF;
  END;
  IF NOT failed THEN RAISE EXCEPTION 'FAIL: receipt failure not observed'; END IF;
END $test$;
RESET ROLE;
DO $test$ BEGIN
  IF EXISTS(SELECT 1 FROM public.workspaces) OR EXISTS(SELECT 1 FROM public.workspace_memberships)
     OR EXISTS(SELECT 1 FROM public.workspace_creation_receipts) THEN
    RAISE EXCEPTION 'FAIL: workspace creation did not roll back';
  END IF;
  RAISE NOTICE 'PASS: workspace creation rolls back';
END $test$;
ROLLBACK;
""")
        self.assertIn("PASS: workspace creation rolls back", notice)

    def test_workspace_creation_receipts_are_private(self):
        result = run_sql("""
SELECT role_name,
       has_table_privilege(role_name, 'public.workspace_creation_receipts', 'SELECT'),
       has_table_privilege(role_name, 'public.workspace_creation_receipts', 'INSERT'),
       has_table_privilege(role_name, 'public.workspace_creation_receipts', 'UPDATE'),
       has_table_privilege(role_name, 'public.workspace_creation_receipts', 'DELETE')
FROM (VALUES ('anon'),('authenticated')) AS roles(role_name) ORDER BY role_name;
""")
        self.assertEqual(result.splitlines(), ['anon|f|f|f|f', 'authenticated|f|f|f|f'])

    def test_workspace_retry_fails_closed_after_workspace_deletion(self):
        notice = run_sql_with_notices(f"""
BEGIN;
CREATE TEMP TABLE original_workspace(id uuid);
GRANT SELECT, INSERT ON original_workspace TO authenticated;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{MEERA}', true);
INSERT INTO original_workspace SELECT public.create_workspace('Deleted Academy','academy','cccccccc-2222-4222-8222-cccccccccccc');
RESET ROLE;
DELETE FROM public.workspace_memberships WHERE workspace_id=(SELECT id FROM original_workspace);
DELETE FROM public.workspaces WHERE id=(SELECT id FROM original_workspace);
SET LOCAL ROLE authenticated;
DO $test$
DECLARE denied boolean := false;
BEGIN
  BEGIN
    PERFORM public.create_workspace('Deleted Academy','academy','cccccccc-2222-4222-8222-cccccccccccc');
  EXCEPTION WHEN OTHERS THEN
    IF SQLSTATE='42501' AND SQLERRM='Workspace unavailable' THEN denied:=true; ELSE RAISE; END IF;
  END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: deleted workspace recreated'; END IF;
  RAISE NOTICE 'PASS: deleted workspace retry fails closed';
END $test$;
ROLLBACK;
""")
        self.assertIn("PASS: deleted workspace retry fails closed", notice)

    def test_legacy_workspace_receipt_unknown_fails_closed(self):
        notice = run_sql_with_notices(f"""
BEGIN;
CREATE TEMP TABLE original_workspace(id uuid);
GRANT SELECT, INSERT ON original_workspace TO authenticated;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{MEERA}', true);
INSERT INTO original_workspace SELECT public.create_workspace('Legacy Academy','academy','dddddddd-2222-4222-8222-dddddddddddd');
RESET ROLE;
UPDATE public.workspace_creation_receipts SET original_name=NULL, original_type=NULL WHERE workspace_id=(SELECT id FROM original_workspace);
SET LOCAL ROLE authenticated;
DO $test$
DECLARE denied boolean := false;
BEGIN
  BEGIN
    PERFORM public.create_workspace('Legacy Academy','academy','dddddddd-2222-4222-8222-dddddddddddd');
  EXCEPTION WHEN OTHERS THEN
    IF SQLSTATE='42501' AND SQLERRM='Workspace creation recovery unavailable' THEN denied:=true; ELSE RAISE; END IF;
  END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: unknown legacy payload accepted'; END IF;
  RAISE NOTICE 'PASS: unknown legacy payload fails closed';
END $test$;
ROLLBACK;
""")
        self.assertIn("PASS: unknown legacy payload fails closed", notice)
    def test_new_workspace_retry_uses_original_details_after_rename(self):
        notice = run_sql_with_notices(f"""
BEGIN;
CREATE TEMP TABLE original_workspace(id uuid);
GRANT SELECT, INSERT ON original_workspace TO authenticated;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{MEERA}', true);
INSERT INTO original_workspace SELECT public.create_workspace('First Academy','academy','bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb');
RESET ROLE;
UPDATE public.workspaces SET name='Renamed Academy' WHERE id=(SELECT id FROM original_workspace);
SET LOCAL ROLE authenticated;
DO $test$
DECLARE original_id uuid; denied boolean := false;
BEGIN
  SELECT id INTO original_id FROM original_workspace;
  IF public.create_workspace('First Academy','academy','bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb') IS DISTINCT FROM original_id THEN
    RAISE EXCEPTION 'FAIL: original retry returned a different workspace';
  END IF;
  BEGIN
    PERFORM public.create_workspace('Renamed Academy','academy','bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb');
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM='Request ID reused with different workspace details' THEN denied:=true; ELSE RAISE; END IF;
  END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: changed payload accepted'; END IF;
  RAISE NOTICE 'PASS: original payload retry survives rename';
END $test$;
ROLLBACK;
""")
        self.assertIn("PASS: original payload retry survives rename", notice)

    def test_workspace_replay_requires_current_access_before_payload_comparison(self):
        changes = {
            "workspace suspended": "UPDATE public.workspaces SET status='suspended' WHERE id=(SELECT id FROM replay_workspace)",
            "workspace archived": "UPDATE public.workspaces SET status='archived' WHERE id=(SELECT id FROM replay_workspace)",
            "membership suspended": "UPDATE public.workspace_memberships SET status='suspended' WHERE workspace_id=(SELECT id FROM replay_workspace) AND user_id='{actor}'",
            "membership removed": "UPDATE public.workspace_memberships SET status='removed' WHERE workspace_id=(SELECT id FROM replay_workspace) AND user_id='{actor}'",
            "membership deleted": "DELETE FROM public.workspace_memberships WHERE workspace_id=(SELECT id FROM replay_workspace) AND user_id='{actor}'",
        }
        for name, change in changes.items():
            with self.subTest(name=name):
                notice = run_sql_with_notices(f"""
BEGIN;
CREATE TEMP TABLE replay_workspace(id uuid);
GRANT SELECT, INSERT ON replay_workspace TO authenticated;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{MEERA}', true);
INSERT INTO replay_workspace SELECT public.create_workspace('Example Academy','academy','aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
DO $test$ BEGIN
  IF public.create_workspace('Example Academy','academy','aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa') IS DISTINCT FROM (SELECT id FROM replay_workspace) THEN
    RAISE EXCEPTION 'FAIL: valid retry changed ID';
  END IF;
END $test$;
RESET ROLE;
{change.format(actor=MEERA)};
SET LOCAL ROLE authenticated;
DO $test$
DECLARE denied boolean;
BEGIN
  FOR attempt IN 1..2 LOOP
    denied := false;
    BEGIN
      PERFORM public.create_workspace(CASE WHEN attempt=1 THEN 'Example Academy' ELSE 'Changed Academy' END,'academy','aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
    EXCEPTION WHEN OTHERS THEN
      IF SQLSTATE='42501' AND SQLERRM='Workspace unavailable' THEN denied:=true; ELSE RAISE; END IF;
    END;
    IF NOT denied THEN RAISE EXCEPTION 'FAIL: unauthorized replay returned success'; END IF;
  END LOOP;
  RAISE NOTICE 'PASS: access denial precedes payload comparison';
END $test$;
ROLLBACK;
""")
                self.assertIn("PASS: access denial precedes payload comparison", notice)

    def test_own_profile_visible(self):
        result = run_sql(f"""
BEGIN;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{MEERA}', true);
SELECT count(*) FROM public.profiles WHERE id = '{MEERA}';
ROLLBACK;
""")
        self.assertEqual(result.splitlines()[-1], "1")

    def test_other_profile_hidden(self):
        result = run_sql(f"""
BEGIN;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{MEERA}', true);
SELECT count(*) FROM public.profiles WHERE id = '{RAHUL}';
ROLLBACK;
""")
        self.assertEqual(result.splitlines()[-1], "0")

    def test_anonymous_workspace_execution_denied(self):
        result = run_sql("""
SELECT has_function_privilege(
  'anon',
  'public.create_workspace(text,text,uuid)',
  'EXECUTE'
);
""")
        self.assertEqual(result, "f")


    def test_own_profile_update(self):
        result = run_sql(f"""
BEGIN;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{MEERA}', true);
WITH changed AS (
  UPDATE public.profiles
  SET display_name = 'Meera Test'
  WHERE id = '{MEERA}'
  RETURNING id
)
SELECT count(*) FROM changed;
ROLLBACK;
""")
        self.assertEqual(result.splitlines()[-1], "1")

    def test_other_profile_update_blocked(self):
        result = run_sql(f"""
BEGIN;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{MEERA}', true);
WITH changed AS (
  UPDATE public.profiles
  SET display_name = 'Unauthorized'
  WHERE id = '{RAHUL}'
  RETURNING id
)
SELECT count(*) FROM changed;
ROLLBACK;
""")
        self.assertEqual(result.splitlines()[-1], "0")


    def test_direct_workspace_insert_denied(self):
        result = run_sql_with_notices(f"""
BEGIN;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{MEERA}', true);
DO $test$
BEGIN
  INSERT INTO public.workspaces
    (name, type, created_by, creation_request_id)
  VALUES
    ('Unauthorized Workspace', 'academy',
     '{MEERA}', 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa');
  RAISE EXCEPTION 'FAIL: Direct workspace insert succeeded';
EXCEPTION
  WHEN insufficient_privilege THEN
    RAISE NOTICE 'PASS: Direct workspace insert denied';
END
$test$;
ROLLBACK;
""")
        self.assertIn("PASS: Direct workspace insert denied", result)

    def test_direct_owner_membership_insert_denied(self):
        result = run_sql_with_notices(f"""
BEGIN;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{MEERA}', true);
DO $test$
BEGIN
  INSERT INTO public.workspace_memberships
    (workspace_id, user_id, role, status)
  VALUES
    ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
     '{MEERA}', 'owner', 'active');
  RAISE EXCEPTION 'FAIL: Direct Owner insertion succeeded';
EXCEPTION
  WHEN insufficient_privilege THEN
    RAISE NOTICE 'PASS: Direct Owner insertion denied';
END
$test$;
ROLLBACK;
""")
        self.assertIn("PASS: Direct Owner insertion denied", result)


    def test_cross_workspace_isolation(self):
        result = run_sql_with_notices(f"""
BEGIN;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{MEERA}', true);
SELECT public.create_workspace(
  'Meera Regression Academy', 'academy',
  'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'
);
RESET ROLE;

SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{RAHUL}', true);
SELECT public.create_workspace(
  'Rahul Regression Academy', 'academy',
  'bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb'
);
RESET ROLE;

SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{MEERA}', true);

DO $test$
DECLARE n integer;
BEGIN
  SELECT count(*) INTO n FROM public.workspaces;
  IF n != 1 THEN
    RAISE EXCEPTION 'FAIL: Cross-workspace isolation';
  END IF;
  RAISE NOTICE 'PASS: Cross-workspace isolation';
END
$test$;

ROLLBACK;
""")
        self.assertIn("PASS: Cross-workspace isolation", result)

    def test_suspended_membership_access(self):
        result = run_sql_with_notices(f"""
BEGIN;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{MEERA}', true);
SELECT public.create_workspace(
  'Suspension Regression Academy', 'academy',
  'cccccccc-3333-4333-8333-cccccccccccc'
);
RESET ROLE;

UPDATE public.workspace_memberships
SET status = 'suspended'
WHERE user_id = '{MEERA}'
AND workspace_id IN (
  SELECT id FROM public.workspaces
  WHERE name = 'Suspension Regression Academy'
);

SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '{MEERA}', true);

DO $test$
DECLARE n integer;
BEGIN
  SELECT count(*) INTO n
  FROM public.workspaces
  WHERE name = 'Suspension Regression Academy';

  IF n != 0 THEN
    RAISE EXCEPTION 'FAIL: Suspended membership access';
  END IF;

  RAISE NOTICE 'PASS: Suspended membership denied';
END
$test$;

ROLLBACK;
""")
        self.assertIn("PASS: Suspended membership denied", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
