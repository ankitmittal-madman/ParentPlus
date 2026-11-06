#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

CONTAINER="${PARENTPLUS_TEST_CONTAINER:-parentplus-pg-test}"
DB="parentplus_test"
USER="parentplus_test"

case "$CONTAINER" in
  parentplus-pg-test|parentplus-pg-ci-fresh)
    ;;
  *)
    echo "STOP: Unapproved test container name"
    exit 1
    ;;
esac

echo "=== VERIFY TEST DATABASE ISOLATION ==="

NETWORK=$(docker inspect "$CONTAINER" \
  --format '{{.HostConfig.NetworkMode}}')

if [ "$NETWORK" != "none" ]; then
  echo "STOP: Database container is not network isolated"
  exit 1
fi

if [ -n "$(docker port "$CONTAINER")" ]; then
  echo "STOP: Database exposes network ports"
  exit 1
fi

IDENTITY=$(docker exec "$CONTAINER" \
  psql -X -A -t -v ON_ERROR_STOP=1 \
  -U "$USER" -d "$DB" \
  -c "SELECT current_user || ':' || current_database();")

if [ "$IDENTITY" != "$USER:$DB" ]; then
  echo "STOP: Unexpected database identity"
  exit 1
fi

STATE=$(docker exec "$CONTAINER" \
  psql -X -A -t -v ON_ERROR_STOP=1 \
  -U "$USER" -d "$DB" \
  -c "SELECT
    (SELECT count(*) FROM pg_namespace WHERE nspname='auth') || ':' ||
    (SELECT count(*) FROM pg_tables WHERE schemaname='public') || ':' ||
    (SELECT count(*) FROM pg_roles WHERE rolname IN ('anon','authenticated'));")

if [ "$STATE" != "0:0:0" ]; then
  echo "STOP: Test database is not empty"
  exit 1
fi

echo "PASS: Isolated empty database verified"

mapfile -t MIGRATIONS < <(
  find supabase/migrations -maxdepth 1 \
    -type f -name '*.sql' | sort
)

if [ "${#MIGRATIONS[@]}" -ne 38 ]; then
  echo "STOP: Unexpected migration count"
  exit 1
fi

echo "=== LOAD SYNTHETIC AUTH FIXTURE ==="

docker exec -i "$CONTAINER" \
  psql -X -q -v ON_ERROR_STOP=1 \
  -U "$USER" -d "$DB" \
  < tests/database/supabase_auth_fixture.sql

echo "=== APPLY DATABASE MIGRATIONS ==="

for FILE in "${MIGRATIONS[@]}"; do
  echo "Applying $(basename "$FILE")"

  docker exec -i "$CONTAINER" \
    psql -X -q -v ON_ERROR_STOP=1 \
    -U "$USER" -d "$DB" \
    < "$FILE"

  # A partial local reconstruction must never expose the ungated drafts.
  case "$(basename "$FILE")" in
    20261103001600_authenticated_course_draft.sql) SIGNATURE='public.create_course(uuid,text,uuid)' ;;
    20261103001700_authenticated_batch_draft.sql) SIGNATURE='public.create_batch(uuid,uuid,text,uuid)' ;;
    *) SIGNATURE='' ;;
  esac
  if [ -n "$SIGNATURE" ]; then
    PARTIAL_ACCESS=$(docker exec "$CONTAINER" psql -X -A -t -q -v ON_ERROR_STOP=1 \
      -U "$USER" -d "$DB" -c "SELECT has_function_privilege('authenticated', '$SIGNATURE', 'EXECUTE') OR has_function_privilege('anon', '$SIGNATURE', 'EXECUTE');")
    if [ "$PARTIAL_ACCESS" != "f" ]; then
      echo "STOP: Ungated draft operation exposed during partial migration: $SIGNATURE"
      exit 1
    fi
    echo "PASS: Partial migration keeps draft operation private"
  fi
done

echo "=== VERIFY DATABASE BASELINE ==="

BASELINE=$(docker exec "$CONTAINER" \
  psql -X -A -t -v ON_ERROR_STOP=1 \
  -U "$USER" -d "$DB" \
  -c "SELECT
    (SELECT count(*) FROM auth.users) || ':' ||
    (SELECT count(*) FROM public.profiles) || ':' ||
    (SELECT count(*) FROM pg_tables WHERE schemaname='public') || ':' ||
    (SELECT count(*) FROM public.workspaces) || ':' ||
    (SELECT count(*) FROM public.children) || ':' ||
    (SELECT count(*) FROM public.child_creation_controls WHERE id=true AND NOT enabled);")

if [ "$BASELINE" != "3:3:23:0:0:1" ]; then
  echo "STOP: Unexpected database baseline: $BASELINE"
  exit 1
fi

echo "PASS: Database initialized successfully"
echo "PASS: All 38 migrations applied"
