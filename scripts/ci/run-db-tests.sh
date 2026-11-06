#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

CONTAINER="${PARENTPLUS_TEST_CONTAINER:-parentplus-pg-test}"
case "$CONTAINER" in
  parentplus-pg-test|parentplus-pg-ci-fresh) ;;
  *) echo "STOP: Unapproved container"; exit 1 ;;
esac

DB="parentplus_test"
USER="parentplus_test"

echo "=== VERIFY TEST DATABASE ==="

NETWORK=$(docker inspect "$CONTAINER" \
  --format '{{.HostConfig.NetworkMode}}')

if [ "$NETWORK" != "none" ]; then
  echo "STOP: Database is not network isolated"
  exit 1
fi

if [ -n "$(docker port "$CONTAINER")" ]; then
  echo "STOP: Database exposes ports"
  exit 1
fi

docker exec "$CONTAINER" \
  pg_isready -U "$USER" -d "$DB"

echo "=== RUN DATABASE UNITTEST SUITES ==="

python3 scripts/ci/database_junit.py

echo "=== RUN STANDALONE CONCURRENCY TESTS ==="

python3 scripts/ci/concurrency_junit.py

echo "=== VERIFY DATABASE CLEANUP ==="

docker exec -i "$CONTAINER" \
  psql -X -v ON_ERROR_STOP=1 \
  -U "$USER" -d "$DB" <<'SQL'
DO $$
DECLARE
  v_remaining bigint;
BEGIN
  SELECT
    (SELECT count(*) FROM public.workspaces) +
    (SELECT count(*) FROM public.workspace_memberships) +
    (SELECT count(*) FROM public.children) +
    (SELECT count(*) FROM public.guardianships) +
    (SELECT count(*) FROM public.workspace_children) +
    (SELECT count(*) FROM public.connection_request_receipts) +
    (SELECT count(*) FROM public.connection_requests) +
    (SELECT count(*) FROM public.connection_events) +
    (SELECT count(*) FROM public.courses) +
    (SELECT count(*) FROM public.batches) +
    (SELECT count(*) FROM public.batch_coach_assignments) +
    (SELECT count(*) FROM public.schedule_sessions) +
    (SELECT count(*) FROM public.batch_coach_mutation_requests) +
    (SELECT count(*) FROM public.class_setup_requests) +
    (SELECT count(*) FROM public.class_setup_intents) +
    (SELECT count(*) FROM public.class_setup_next_requests) +
    (SELECT count(*) FROM public.class_setup_intent_history) +
    (SELECT count(*) FROM public.child_creation_intents) +
    (SELECT count(*) FROM public.child_creation_fences) +
    (SELECT count(*) FROM public.child_creation_history) +
    (SELECT count(*) FROM (VALUES ('anon'),('authenticated')) r(role_name) WHERE has_function_privilege(r.role_name, 'public.create_child(text,uuid)', 'EXECUTE')) +
    (SELECT count(*) FROM (VALUES ('anon'),('authenticated')) r(role_name)
      CROSS JOIN (VALUES ('public.create_course(uuid,text,uuid)'),('public.create_batch(uuid,uuid,text,uuid)'),('public.create_course_and_batch(uuid,text,text,uuid)')) f(signature)
      WHERE has_function_privilege(r.role_name, f.signature, 'EXECUTE')) +
    (SELECT count(*) FROM public.class_setup_controls WHERE enabled) +
    (SELECT count(*) FROM public.parent_child_read_controls WHERE enabled) +
    (SELECT CASE WHEN count(*)=1 AND bool_and(id AND NOT enabled) THEN 0 ELSE 1 END FROM public.child_creation_controls)
  INTO v_remaining;

  IF v_remaining <> 0 THEN
    RAISE EXCEPTION 'Test cleanup incomplete: % records', v_remaining;
  END IF;

  RAISE NOTICE 'PASS: Database cleanup verified';
END;
$$;
SQL

echo "PASS: All database tests completed"
echo "PASS: Database cleanup verified"
