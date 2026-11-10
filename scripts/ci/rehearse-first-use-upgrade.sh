#!/usr/bin/env bash
# Synthetic PostgreSQL-only upgrade rehearsal. This is not Supabase Auth or
# hosted-database evidence. Never point this script at an existing database.
set -euo pipefail
cd "$(dirname "$0")/../.."
container=parentplus-upgrade-rehearsal
if docker inspect "$container" >/dev/null 2>&1; then echo 'STOP: rehearsal container already exists'; exit 1; fi
docker run -d --name "$container" --network none -e POSTGRES_USER=parentplus_test -e POSTGRES_PASSWORD=localtest -e POSTGRES_DB=parentplus_test postgres:17 >/dev/null
trap 'docker rm -f "$container" >/dev/null' EXIT
for i in {1..60}; do if docker exec "$container" pg_isready -U parentplus_test -d parentplus_test >/dev/null 2>&1 && docker exec "$container" psql -U parentplus_test -d parentplus_test -tAc 'select 1' >/dev/null 2>&1; then break; fi; sleep 1; done
[ "$(docker inspect "$container" --format '{{.HostConfig.NetworkMode}}')" = none ]
[ -z "$(docker port "$container")" ]
run_sql() { docker exec -i "$container" psql -X -q -v ON_ERROR_STOP=1 -U parentplus_test -d parentplus_test; }
run_sql < tests/database/supabase_auth_fixture.sql
mapfile -t migrations < <(find supabase/migrations -maxdepth 1 -name '*.sql' -type f | sort)
[ "${#migrations[@]}" -eq 49 ]
for ((i=0; i<13; i++)); do run_sql < "${migrations[$i]}"; done
run_sql <<'SQL'
insert into public.workspaces(id,name,type,created_by,creation_request_id) values ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','Fictional Academy','academy','11111111-1111-4111-8111-111111111111','bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb');
insert into public.workspace_memberships(workspace_id,user_id,role,status) values ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','11111111-1111-4111-8111-111111111111','owner','active');
insert into public.children(id,display_name,created_by) values ('cccccccc-cccc-4ccc-8ccc-cccccccccccc','Fictional Child','22222222-2222-4222-8222-222222222222');
insert into public.guardianships(child_id,guardian_user_id,status) values ('cccccccc-cccc-4ccc-8ccc-cccccccccccc','22222222-2222-4222-8222-222222222222','active');
SQL
for ((i=13; i<49; i++)); do echo "Applying $(basename "${migrations[$i]}")"; run_sql < "${migrations[$i]}"; done
run_sql <<'SQL'
do $$ begin
 if not exists(select 1 from public.workspaces where id='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa' and name='Fictional Academy') or not exists(select 1 from public.workspace_memberships where workspace_id='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa' and status='active') or not exists(select 1 from public.children where id='cccccccc-cccc-4ccc-8ccc-cccccccccccc' and display_name='Fictional Child') or not exists(select 1 from public.guardianships where child_id='cccccccc-cccc-4ccc-8ccc-cccccccccccc' and status='active') then raise exception 'existing synthetic records lost or altered'; end if;
 if (select count(*) from public.workspace_creation_controls where id and not enabled) <> 1 or (select count(*) from public.child_creation_controls where id and not enabled) <> 1 or (select count(*) from public.class_setup_controls where id and not enabled) <> 1 then raise exception 'creation controls not confirmed disabled'; end if;
end $$;
SQL
echo 'PASS: 001–013 baseline with fictional records upgraded through 049; selected records survived and creation controls remained disabled.'
