#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."

CONTAINER="parentplus-pg-ci-fresh"
EVIDENCE="test-results/database"

mkdir -p "$EVIDENCE"

if docker container inspect "$CONTAINER" >/dev/null 2>&1; then
  echo "STOP: CI container already exists"
  exit 1
fi

CREATED=0
INITIALIZED=0
TEST_EXIT=1

cleanup() {
  status=$?
  trap - EXIT

  if [ "$CREATED" -eq 1 ]; then
    if [ "$INITIALIZED" -eq 1 ]; then
      echo "=== VERIFY DATABASE CLEANUP ==="

      if docker exec "$CONTAINER" \
        psql -X -A -t -v ON_ERROR_STOP=1 \
        -U parentplus_test -d parentplus_test \
        -c "SELECT
          (SELECT count(*) FROM public.workspaces) +
          (SELECT count(*) FROM public.workspace_memberships) +
          (SELECT count(*) FROM public.children) +
          (SELECT count(*) FROM public.guardianships) +
          (SELECT count(*) FROM public.workspace_children) +
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
    (SELECT count(*) FROM (VALUES ('anon'),('authenticated')) r(role_name)
      CROSS JOIN (VALUES ('public.create_course(uuid,text,uuid)'),('public.create_batch(uuid,uuid,text,uuid)'),('public.create_course_and_batch(uuid,text,text,uuid)')) f(signature)
      WHERE has_function_privilege(r.role_name, f.signature, 'EXECUTE')) +
    (SELECT count(*) FROM public.class_setup_controls WHERE enabled);" \
        > "$EVIDENCE/cleanup-count.txt" \
        2> "$EVIDENCE/cleanup-error.txt"; then

        if [ "$(cat "$EVIDENCE/cleanup-count.txt")" != "0" ]; then
          echo "FAIL: Residual database records"
          status=1
        else
          echo "PASS: Database cleanup verified"
        fi
      else
        echo "FAIL: Cleanup audit failed"
        status=1
      fi
    else
      echo "NOT VERIFIED: Initialization incomplete" \
        > "$EVIDENCE/cleanup-status.txt"
    fi

    if ! docker rm -f "$CONTAINER" >/dev/null; then
      echo "FAIL: Container removal failed"
      status=1
    fi
  fi

  exit "$status"
}

trap cleanup EXIT

echo "=== CREATE ISOLATED POSTGRESQL ==="

docker run -d \
  --name "$CONTAINER" \
  --network none \
  --tmpfs /var/lib/postgresql \
  --tmpfs /tmp \
  -e POSTGRES_USER=parentplus_test \
  -e POSTGRES_DB=parentplus_test \
  -e POSTGRES_PASSWORD=parentplus_local_only \
  -e PGDATA=/var/lib/postgresql/pgdata \
  postgres:17 > "$EVIDENCE/container-id.txt"

CREATED=1

echo "=== WAIT FOR POSTGRESQL ==="

READY=0

for attempt in $(seq 1 30); do
  if docker exec "$CONTAINER" \
    pg_isready -U parentplus_test \
    -d parentplus_test >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 2
done

test "$READY" -eq 1

echo "=== INITIALIZE DATABASE ==="

PARENTPLUS_TEST_CONTAINER="$CONTAINER" \
  bash scripts/ci/init-test-db.sh \
  2>&1 | tee "$EVIDENCE/initialization.log"

INITIALIZED=1

echo "=== EXECUTE DATABASE TESTS ==="

if PARENTPLUS_TEST_CONTAINER="$CONTAINER" \
  timeout 300s bash scripts/ci/run-db-tests.sh \
  2>&1 | tee "$EVIDENCE/database-tests.log"; then
  TEST_EXIT=0
else
  TEST_EXIT=1
fi

echo "=== VALIDATE TEST EVIDENCE ==="

if python3 scripts/ci/validate-db-evidence.py \
  2>&1 | tee "$EVIDENCE/evidence-validation.log"; then
  EVIDENCE_EXIT=0
else
  EVIDENCE_EXIT=1
fi

if [ "$TEST_EXIT" -ne 0 ] || [ "$EVIDENCE_EXIT" -ne 0 ]; then
  echo "FAIL: Database quality gate"
  exit 1
fi

echo "PASS: Test execution and evidence validation"
