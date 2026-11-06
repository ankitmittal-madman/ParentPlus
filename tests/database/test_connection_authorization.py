"""ParentPlus connection authorization regression tests.

Requires disposable PostgreSQL container and migrations 001-011.
Uses fictional test identities only.
"""

import subprocess
from tests.database.container_config import get_test_container
import unittest
import uuid

MEERA = "11111111-1111-4111-8111-111111111111"
RAHUL = "22222222-2222-4222-8222-222222222222"


def run_sql(sql):
    result = subprocess.run(
        [
            "docker", "exec", "-i", get_test_container(),
            "psql", "-X", "-v", "ON_ERROR_STOP=1",
            "-U", "parentplus_test", "-d", "parentplus_test",
        ],
        input=sql,
        text=True,
        capture_output=True,
        timeout=30,
    )

    if result.returncode != 0:
        raise AssertionError(result.stderr.strip())

    return result.stdout, result.stderr


def scenario_sql(test_body):
    workspace_request = str(uuid.uuid4())
    child_request = str(uuid.uuid4())

    return f"""
BEGIN;
-- Synthetic fixture only; rollback restores the default-off control.
GRANT EXECUTE ON FUNCTION public.create_child(text,uuid) TO authenticated;
UPDATE public.child_creation_controls SET enabled=true WHERE id=true;

CREATE TEMP TABLE test_ids (
  workspace_id uuid,
  child_id uuid,
  request_id uuid,
  second_child_id uuid
);

GRANT SELECT, INSERT, UPDATE ON TABLE test_ids TO authenticated;

SET LOCAL ROLE authenticated;
SELECT set_config(
  'request.jwt.claim.sub',
  '{RAHUL}',
  true
);

INSERT INTO test_ids (workspace_id)
SELECT public.create_workspace(
  'Connection Regression Academy',
  'academy',
  '{workspace_request}'
);

RESET ROLE;

SET LOCAL ROLE authenticated;
SELECT set_config(
  'request.jwt.claim.sub',
  '{MEERA}',
  true
);

UPDATE test_ids
SET child_id = public.create_child(
  'Riya Regression Test',
  '{child_request}'
);

RESET ROLE;

{test_body}

ROLLBACK;
"""


class ConnectionAuthorizationTests(unittest.TestCase):

    def test_receipt_failure_rolls_back_request_and_event(self):
        sql = scenario_sql("""
CREATE FUNCTION pg_temp.fail_connection_receipt() RETURNS trigger LANGUAGE plpgsql AS $body$
BEGIN RAISE EXCEPTION 'synthetic receipt failure'; END $body$;
CREATE TRIGGER fail_connection_receipt BEFORE INSERT ON public.connection_request_receipts
FOR EACH ROW EXECUTE FUNCTION pg_temp.fail_connection_receipt();
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);
DO $test$
DECLARE ids record; failed boolean := false;
BEGIN
  SELECT * INTO ids FROM test_ids;
  BEGIN
    PERFORM public.request_workspace_connection(ids.workspace_id, ids.child_id, 'dddddddd-1111-4111-8111-dddddddddddd');
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM = 'synthetic receipt failure' THEN failed := true; ELSE RAISE; END IF;
  END;
  IF NOT failed THEN RAISE EXCEPTION 'FAIL: receipt failure not observed'; END IF;
END $test$;
RESET ROLE;
DO $test$ BEGIN
  IF EXISTS (SELECT 1 FROM public.connection_requests) OR EXISTS (SELECT 1 FROM public.connection_events)
     OR EXISTS (SELECT 1 FROM public.connection_request_receipts) THEN
    RAISE EXCEPTION 'FAIL: partial connection after receipt failure';
  END IF;
  RAISE NOTICE 'PASS: receipt failure rolls back connection';
END $test$;
""")
        stdout, stderr = run_sql(sql)
        self.assertIn("PASS: receipt failure rolls back connection", stderr)
        self.assertIn("ROLLBACK", stdout)

    def test_reused_key_rejects_changed_child_and_revoked_guardian(self):
        sql = scenario_sql("""
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);
UPDATE test_ids SET second_child_id = public.create_child('Second example', 'cccccccc-1111-4111-8111-cccccccccccc');
UPDATE test_ids SET request_id = public.request_workspace_connection(workspace_id, child_id, 'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT public.request_workspace_connection(workspace_id, child_id, 'bbbbbbbb-1111-4111-8111-bbbbbbbbbbbb') FROM test_ids;
DO $test$
DECLARE ids record; denied boolean := false;
BEGIN
  SELECT * INTO ids FROM test_ids;
  BEGIN
    PERFORM public.request_workspace_connection(ids.workspace_id, ids.second_child_id, 'bbbbbbbb-1111-4111-8111-bbbbbbbbbbbb');
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM = 'Request ID reused with different details' THEN denied := true; ELSE RAISE; END IF;
  END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: changed payload accepted'; END IF;
END $test$;
RESET ROLE;
UPDATE public.guardianships SET status='revoked' WHERE child_id=(SELECT child_id FROM test_ids) AND guardian_user_id='11111111-1111-4111-8111-111111111111';
SET LOCAL ROLE authenticated;
DO $test$
DECLARE ids record; denied boolean := false;
BEGIN
  SELECT * INTO ids FROM test_ids;
  BEGIN
    PERFORM public.request_workspace_connection(ids.workspace_id, ids.child_id, 'bbbbbbbb-1111-4111-8111-bbbbbbbbbbbb');
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM = 'Guardian not authorized' THEN denied := true; ELSE RAISE; END IF;
  END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: revoked guardian received retry result'; END IF;
END $test$;
RESET ROLE;
DO $test$ BEGIN
  IF has_table_privilege('authenticated', 'public.connection_request_receipts', 'SELECT,INSERT,UPDATE,DELETE')
     OR has_table_privilege('anon', 'public.connection_request_receipts', 'SELECT,INSERT,UPDATE,DELETE') THEN
    RAISE EXCEPTION 'FAIL: receipt table exposed to app roles';
  END IF;
  RAISE NOTICE 'PASS: changed payload and revoked guardian denied';
END $test$;
""")
        stdout, stderr = run_sql(sql)
        self.assertIn("PASS: changed payload and revoked guardian denied", stderr)
        self.assertIn("ROLLBACK", stdout)

    def test_deleted_request_receipt_fails_closed(self):
        sql = scenario_sql("""
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);
UPDATE test_ids SET request_id = public.request_workspace_connection(workspace_id, child_id, 'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
SELECT public.request_workspace_connection(workspace_id, child_id, 'bbbbbbbb-1111-4111-8111-bbbbbbbbbbbb') FROM test_ids;
RESET ROLE;
DELETE FROM public.connection_events WHERE connection_request_id=(SELECT request_id FROM test_ids);
DELETE FROM public.connection_requests WHERE id=(SELECT request_id FROM test_ids);
SET LOCAL ROLE authenticated;
DO $test$
DECLARE ids record; denied boolean := false;
BEGIN
  SELECT * INTO ids FROM test_ids;
  BEGIN
    PERFORM public.request_workspace_connection(ids.workspace_id, ids.child_id, 'bbbbbbbb-1111-4111-8111-bbbbbbbbbbbb');
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM = 'Connection request unavailable' THEN denied := true; ELSE RAISE; END IF;
  END;
  IF NOT denied THEN RAISE EXCEPTION 'FAIL: deleted request created again'; END IF;
END $test$;
RESET ROLE;
DO $test$ BEGIN
  IF EXISTS (SELECT 1 FROM public.connection_requests) OR EXISTS (SELECT 1 FROM public.connection_events) THEN
    RAISE EXCEPTION 'FAIL: deleted request recreated';
  END IF;
  RAISE NOTICE 'PASS: missing request fails closed';
END $test$;
""")
        stdout, stderr = run_sql(sql)
        self.assertIn("PASS: missing request fails closed", stderr)
        self.assertIn("ROLLBACK", stdout)

    def test_reused_pending_key_replays_original_after_approval(self):
        sql = scenario_sql("""
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);
UPDATE test_ids SET request_id = public.request_workspace_connection(
  workspace_id, child_id, 'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa');
DO $test$
DECLARE ids record; reused uuid;
BEGIN
  SELECT * INTO ids FROM test_ids;
  reused := public.request_workspace_connection(ids.workspace_id, ids.child_id, 'bbbbbbbb-1111-4111-8111-bbbbbbbbbbbb');
  IF reused IS DISTINCT FROM ids.request_id THEN RAISE EXCEPTION 'FAIL: pending request was not reused'; END IF;
END $test$;
SELECT set_config('request.jwt.claim.sub', '22222222-2222-4222-8222-222222222222', true);
SELECT public.approve_guardian_connection((SELECT request_id FROM test_ids));
SELECT set_config('request.jwt.claim.sub', '11111111-1111-4111-8111-111111111111', true);
DO $test$
DECLARE ids record; replay uuid;
BEGIN
  SELECT * INTO ids FROM test_ids;
  replay := public.request_workspace_connection(ids.workspace_id, ids.child_id, 'bbbbbbbb-1111-4111-8111-bbbbbbbbbbbb');
  IF replay IS DISTINCT FROM ids.request_id THEN RAISE EXCEPTION 'FAIL: retry created a new request after approval'; END IF;
END $test$;
RESET ROLE;
DO $test$
BEGIN
  IF (SELECT count(*) FROM public.connection_requests) <> 1
     OR (SELECT count(*) FROM public.connection_events WHERE event_type = 'requested') <> 1 THEN
    RAISE EXCEPTION 'FAIL: retry duplicated request or event';
  END IF;
  RAISE NOTICE 'PASS: reused key returns original after approval';
END $test$;
""")
        stdout, stderr = run_sql(sql)
        self.assertIn("PASS: reused key returns original after approval", stderr)
        self.assertIn("ROLLBACK", stdout)

    def test_guardian_connection_creation(self):
        sql = scenario_sql("""
SET LOCAL ROLE authenticated;
SELECT set_config(
  'request.jwt.claim.sub',
  '11111111-1111-4111-8111-111111111111',
  true
);

UPDATE test_ids
SET request_id = public.request_workspace_connection(
  workspace_id,
  child_id,
  'aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa'
);

RESET ROLE;

DO $test$
DECLARE
  v_requests integer;
  v_events integer;
  v_relationships integer;
BEGIN
  SELECT count(*) INTO v_requests
  FROM public.connection_requests r
  JOIN test_ids t ON t.request_id = r.id
  WHERE r.status = 'pending'
    AND r.initiation_type = 'guardian'
    AND r.workspace_id = t.workspace_id
    AND r.child_id = t.child_id
    AND r.guardian_user_id =
      '11111111-1111-4111-8111-111111111111'
    AND r.initiated_by = r.guardian_user_id;

  SELECT count(*) INTO v_events
  FROM public.connection_events e
  JOIN test_ids t ON t.request_id = e.connection_request_id
  WHERE e.event_type = 'requested';

  SELECT count(*) INTO v_relationships
  FROM public.workspace_children;

  IF v_requests <> 1 OR v_events <> 1
     OR v_relationships <> 0 THEN
    RAISE EXCEPTION
      'FAIL: requests %, events %, relationships %',
      v_requests, v_events, v_relationships;
  END IF;

  RAISE NOTICE 'PASS: Guardian connection creation';
END
$test$;
""")

        stdout, stderr = run_sql(sql)
        self.assertIn("PASS: Guardian connection creation", stderr)
        self.assertIn("ROLLBACK", stdout)



    def test_unrelated_guardian_rejected(self):
        sql = scenario_sql("""
SET LOCAL ROLE authenticated;
SELECT set_config(
  'request.jwt.claim.sub',
  '22222222-2222-4222-8222-222222222222',
  true
);

DO $test$
DECLARE
  v_workspace uuid;
  v_child uuid;
BEGIN
  SELECT workspace_id, child_id
  INTO v_workspace, v_child
  FROM test_ids;

  BEGIN
    PERFORM public.request_workspace_connection(
      v_workspace,
      v_child,
      'bbbbbbbb-1111-4111-8111-bbbbbbbbbbbb'
    );
  EXCEPTION
    WHEN raise_exception THEN
      IF SQLERRM = 'Guardian not authorized' THEN
        RAISE NOTICE 'PASS: Unrelated guardian rejected';
        RETURN;
      END IF;
      RAISE;
  END;

  RAISE EXCEPTION 'FAIL: Unrelated guardian accepted';
END
$test$;

RESET ROLE;

DO $test$
BEGIN
  IF EXISTS (SELECT 1 FROM public.connection_requests)
     OR EXISTS (SELECT 1 FROM public.connection_events) THEN
    RAISE EXCEPTION 'FAIL: Unauthorized records created';
  END IF;

  RAISE NOTICE 'PASS: No unauthorized connection records';
END
$test$;
""")

        stdout, stderr = run_sql(sql)
        self.assertIn("PASS: Unrelated guardian rejected", stderr)
        self.assertIn("PASS: No unauthorized connection records", stderr)
        self.assertIn("ROLLBACK", stdout)


    def check_ineligible_guardian(self, status):
        self.assertIn(status, ("revoked", "disputed"))

        sql = scenario_sql(f"""
UPDATE public.guardianships
SET status = '{status}'
WHERE child_id = (SELECT child_id FROM test_ids)
  AND guardian_user_id =
    '11111111-1111-4111-8111-111111111111';

SET LOCAL ROLE authenticated;
SELECT set_config(
  'request.jwt.claim.sub',
  '11111111-1111-4111-8111-111111111111',
  true
);

DO $test$
DECLARE
  v_workspace uuid;
  v_child uuid;
BEGIN
  SELECT workspace_id, child_id
  INTO v_workspace, v_child
  FROM test_ids;

  BEGIN
    PERFORM public.request_workspace_connection(
      v_workspace, v_child,
      'cccccccc-1111-4111-8111-cccccccccccc'
    );
  EXCEPTION
    WHEN raise_exception THEN
      IF SQLERRM = 'Guardian not authorized' THEN
        RAISE NOTICE 'PASS: Ineligible guardian rejected';
        RETURN;
      END IF;
      RAISE;
  END;

  RAISE EXCEPTION 'FAIL: Ineligible guardian accepted';
END
$test$;

RESET ROLE;

DO $test$
BEGIN
  IF EXISTS (SELECT 1 FROM public.connection_requests)
     OR EXISTS (SELECT 1 FROM public.connection_events) THEN
    RAISE EXCEPTION 'FAIL: Unauthorized connection records';
  END IF;

  RAISE NOTICE 'PASS: No unauthorized records';
END
$test$;
""")

        stdout, stderr = run_sql(sql)
        self.assertIn("PASS: Ineligible guardian rejected", stderr)
        self.assertIn("PASS: No unauthorized records", stderr)
        self.assertIn("ROLLBACK", stdout)

    def test_revoked_guardian_rejected(self):
        self.check_ineligible_guardian("revoked")

    def test_disputed_guardian_rejected(self):
        self.check_ineligible_guardian("disputed")


    def check_ineligible_workspace(self, status):
        self.assertIn(status, ("suspended", "archived"))

        sql = scenario_sql(f"""
UPDATE public.workspaces
SET status = '{status}'
WHERE id = (SELECT workspace_id FROM test_ids);

SET LOCAL ROLE authenticated;
SELECT set_config(
  'request.jwt.claim.sub',
  '11111111-1111-4111-8111-111111111111',
  true
);

DO $test$
DECLARE
  v_workspace uuid;
  v_child uuid;
BEGIN
  SELECT workspace_id, child_id
  INTO v_workspace, v_child
  FROM test_ids;

  BEGIN
    PERFORM public.request_workspace_connection(
      v_workspace,
      v_child,
      'dddddddd-1111-4111-8111-dddddddddddd'
    );
  EXCEPTION
    WHEN raise_exception THEN
      IF SQLERRM = 'Workspace unavailable' THEN
        RAISE NOTICE 'PASS: Ineligible workspace rejected';
        RETURN;
      END IF;
      RAISE;
  END;

  RAISE EXCEPTION 'FAIL: Ineligible workspace accepted';
END
$test$;

RESET ROLE;

DO $test$
BEGIN
  IF EXISTS (SELECT 1 FROM public.connection_requests)
     OR EXISTS (SELECT 1 FROM public.connection_events) THEN
    RAISE EXCEPTION 'FAIL: Unauthorized connection records';
  END IF;

  RAISE NOTICE 'PASS: No unauthorized records';
END
$test$;
""")

        stdout, stderr = run_sql(sql)
        self.assertIn("PASS: Ineligible workspace rejected", stderr)
        self.assertIn("PASS: No unauthorized records", stderr)
        self.assertIn("ROLLBACK", stdout)

    def test_suspended_workspace_rejected(self):
        self.check_ineligible_workspace("suspended")

    def test_archived_workspace_rejected(self):
        self.check_ineligible_workspace("archived")


    def test_connection_idempotent_retry(self):
        sql = scenario_sql("""
SET LOCAL ROLE authenticated;
SELECT set_config(
  'request.jwt.claim.sub',
  '11111111-1111-4111-8111-111111111111',
  true
);

UPDATE test_ids
SET request_id = public.request_workspace_connection(
  workspace_id,
  child_id,
  'eeeeeeee-1111-4111-8111-eeeeeeeeeeee'
);

DO $test$
DECLARE
  v_workspace uuid;
  v_child uuid;
  v_original uuid;
  v_retry uuid;
BEGIN
  SELECT workspace_id, child_id, request_id
  INTO v_workspace, v_child, v_original
  FROM test_ids;

  v_retry := public.request_workspace_connection(
    v_workspace,
    v_child,
    'eeeeeeee-1111-4111-8111-eeeeeeeeeeee'
  );

  IF v_retry IS DISTINCT FROM v_original THEN
    RAISE EXCEPTION 'FAIL: Retry returned different ID';
  END IF;

  RAISE NOTICE 'PASS: Retry returned original request ID';
END
$test$;

RESET ROLE;

DO $test$
DECLARE
  v_requests integer;
  v_events integer;
BEGIN
  SELECT count(*) INTO v_requests
  FROM public.connection_requests;

  SELECT count(*) INTO v_events
  FROM public.connection_events;

  IF v_requests <> 1 OR v_events <> 1 THEN
    RAISE EXCEPTION
      'FAIL: requests %, events %',
      v_requests, v_events;
  END IF;

  RAISE NOTICE 'PASS: No duplicate request or audit event';
END
$test$;
""")

        stdout, stderr = run_sql(sql)
        self.assertIn("PASS: Retry returned original request ID", stderr)
        self.assertIn("PASS: No duplicate request or audit event", stderr)
        self.assertIn("ROLLBACK", stdout)


    def test_connection_request_id_conflict(self):
        sql = scenario_sql("""
SET LOCAL ROLE authenticated;
SELECT set_config(
  'request.jwt.claim.sub',
  '11111111-1111-4111-8111-111111111111',
  true
);



UPDATE test_ids
SET second_child_id = public.create_child(
  'Aarav Conflict Regression',
  'ffffffff-1111-4111-8111-ffffffffffff'
);

UPDATE test_ids
SET request_id = public.request_workspace_connection(
  workspace_id,
  child_id,
  'aaaaaaaa-2222-4222-8222-aaaaaaaaaaaa'
);

DO $test$
DECLARE
  v_workspace uuid;
  v_second_child uuid;
BEGIN
  SELECT workspace_id, second_child_id
  INTO v_workspace, v_second_child
  FROM test_ids;

  BEGIN
    PERFORM public.request_workspace_connection(
      v_workspace,
      v_second_child,
      'aaaaaaaa-2222-4222-8222-aaaaaaaaaaaa'
    );
  EXCEPTION
    WHEN raise_exception THEN
      IF SQLERRM = 'Request ID reused with different details' THEN
        RAISE NOTICE 'PASS: Conflicting request ID rejected';
        RETURN;
      END IF;
      RAISE;
  END;

  RAISE EXCEPTION 'FAIL: Conflicting request accepted';
END
$test$;

RESET ROLE;

DO $test$
DECLARE
  v_requests integer;
  v_events integer;
BEGIN
  SELECT count(*) INTO v_requests
  FROM public.connection_requests;

  SELECT count(*) INTO v_events
  FROM public.connection_events;

  IF v_requests <> 1 OR v_events <> 1 THEN
    RAISE EXCEPTION
      'FAIL: requests %, events %',
      v_requests, v_events;
  END IF;

  RAISE NOTICE 'PASS: Original request and event preserved';
END
$test$;
""")

        stdout, stderr = run_sql(sql)
        self.assertIn("PASS: Conflicting request ID rejected", stderr)
        self.assertIn("PASS: Original request and event preserved", stderr)
        self.assertIn("ROLLBACK", stdout)


    def test_expired_connection_replacement(self):
        sql = scenario_sql("""
SET LOCAL ROLE authenticated;
SELECT set_config(
  'request.jwt.claim.sub',
  '11111111-1111-4111-8111-111111111111',
  true
);

UPDATE test_ids
SET request_id = public.request_workspace_connection(
  workspace_id,
  child_id,
  'aaaaaaaa-3333-4333-8333-aaaaaaaaaaaa'
);

RESET ROLE;

UPDATE public.connection_requests
SET expires_at = now() - interval '1 minute'
WHERE id = (SELECT request_id FROM test_ids);

SET LOCAL ROLE authenticated;
SELECT set_config(
  'request.jwt.claim.sub',
  '11111111-1111-4111-8111-111111111111',
  true
);

DO $test$
DECLARE
  v_workspace uuid;
  v_child uuid;
  v_new_id uuid;
BEGIN
  SELECT workspace_id, child_id
  INTO v_workspace, v_child
  FROM test_ids;

  v_new_id := public.request_workspace_connection(
    v_workspace,
    v_child,
    'bbbbbbbb-3333-4333-8333-bbbbbbbbbbbb'
  );

  IF v_new_id = (SELECT request_id FROM test_ids) THEN
    RAISE EXCEPTION 'FAIL: Expired request reused';
  END IF;

  RAISE NOTICE 'PASS: Replacement request created';
END
$test$;

RESET ROLE;

DO $test$
DECLARE
  v_expired integer;
  v_pending integer;
  v_requested_events integer;
  v_expired_events integer;
BEGIN
  SELECT count(*) INTO v_expired
  FROM public.connection_requests
  WHERE status = 'expired';

  SELECT count(*) INTO v_pending
  FROM public.connection_requests
  WHERE status = 'pending';

  SELECT count(*) INTO v_requested_events
  FROM public.connection_events
  WHERE event_type = 'requested';

  SELECT count(*) INTO v_expired_events
  FROM public.connection_events
  WHERE event_type = 'expired';

  IF v_expired <> 1 OR v_pending <> 1
     OR v_requested_events <> 2
     OR v_expired_events <> 1 THEN
    RAISE EXCEPTION
      'FAIL: expired %, pending %, requested %, expiry events %',
      v_expired, v_pending,
      v_requested_events, v_expired_events;
  END IF;

  IF EXISTS (SELECT 1 FROM public.workspace_children) THEN
    RAISE EXCEPTION 'FAIL: Relationship activated';
  END IF;

  RAISE NOTICE 'PASS: Expiry lifecycle and audit verified';
END
$test$;
""")

        stdout, stderr = run_sql(sql)
        self.assertIn("PASS: Replacement request created", stderr)
        self.assertIn("PASS: Expiry lifecycle and audit verified", stderr)
        self.assertIn("ROLLBACK", stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
