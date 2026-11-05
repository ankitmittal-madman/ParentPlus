-- Local scheduling foundation. No application access until reviewed operations exist.
alter table public.workspace_memberships
  add constraint workspace_memberships_workspace_id_id_key unique (workspace_id, id);

create table public.courses (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id),
  name text not null check (length(trim(name)) > 0),
  unique (workspace_id, id)
);

create table public.batches (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id),
  course_id uuid not null,
  name text not null check (length(trim(name)) > 0),
  unique (workspace_id, id),
  foreign key (workspace_id, course_id) references public.courses(workspace_id, id)
);

create table public.batch_coach_assignments (
  workspace_id uuid not null references public.workspaces(id),
  batch_id uuid not null,
  membership_id uuid not null,
  primary key (workspace_id, batch_id, membership_id),
  foreign key (workspace_id, batch_id) references public.batches(workspace_id, id),
  foreign key (workspace_id, membership_id) references public.workspace_memberships(workspace_id, id)
);

alter table public.courses enable row level security;
alter table public.batches enable row level security;
alter table public.batch_coach_assignments enable row level security;
revoke all on public.courses, public.batches, public.batch_coach_assignments from public, anon, authenticated;
-- Assignment membership role and active status must be checked by future trusted
-- operations at execution time. These tables currently have no application policies.

-- Private building block only. A future trusted write must call this and
-- mutate within the same transaction; the row locks end at transaction end.
create function public.assert_schedule_write_access(p_workspace_id uuid, p_batch_id uuid)
returns void
language plpgsql
set search_path = ''
as $$
declare
  v_actor uuid := auth.uid();
  v_membership uuid;
  v_role text;
begin
  if v_actor is null or p_workspace_id is null or p_batch_id is null then
    raise exception using errcode = '42501', message = 'Schedule access denied';
  end if;

  perform 1 from public.workspaces
    where id = p_workspace_id and status = 'active' for share;
  if not found then
    raise exception using errcode = '42501', message = 'Schedule access denied';
  end if;

  select id, role into v_membership, v_role from public.workspace_memberships
    where workspace_id = p_workspace_id and user_id = v_actor and status = 'active'
    for share;
  if not found then
    raise exception using errcode = '42501', message = 'Schedule access denied';
  end if;

  perform 1 from public.batches
    where workspace_id = p_workspace_id and id = p_batch_id for share;
  if not found then
    raise exception using errcode = '42501', message = 'Schedule access denied';
  end if;

  if v_role = 'coach' then
    perform 1 from public.batch_coach_assignments
      where workspace_id = p_workspace_id and batch_id = p_batch_id
        and membership_id = v_membership for share;
    if not found then
      raise exception using errcode = '42501', message = 'Schedule access denied';
    end if;
  elsif v_role not in ('owner', 'admin') then
    raise exception using errcode = '42501', message = 'Schedule access denied';
  end if;
end;
$$;
revoke all on function public.assert_schedule_write_access(uuid, uuid) from public, anon, authenticated;

-- Private UTC-only persistence building block; not an application scheduling API.
create table public.schedule_sessions (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null,
  batch_id uuid not null,
  starts_at timestamptz not null,
  ends_at timestamptz not null,
  created_by uuid not null references auth.users(id),
  creation_request_id uuid not null,
  unique (created_by, creation_request_id),
  foreign key (workspace_id, batch_id) references public.batches(workspace_id, id),
  check (pg_catalog.isfinite(starts_at) and pg_catalog.isfinite(ends_at)
    and ends_at > starts_at and ends_at - starts_at <= interval '24 hours'
    and pg_catalog.mod(extract(epoch from ends_at - starts_at), 60) = 0)
);
alter table public.schedule_sessions enable row level security;
revoke all on public.schedule_sessions from public, anon, authenticated;

create function public.create_private_session(
  p_workspace_id uuid, p_batch_id uuid, p_starts_at timestamptz,
  p_ends_at timestamptz, p_request_id uuid
)
returns uuid
language plpgsql
set search_path = ''
as $$
declare
  v_actor uuid := auth.uid();
  v_id uuid;
  v_existing record;
begin
  perform public.assert_schedule_write_access(p_workspace_id, p_batch_id);
  if p_request_id is null or p_starts_at is null or p_ends_at is null
     or not pg_catalog.isfinite(p_starts_at) or not pg_catalog.isfinite(p_ends_at)
     or p_ends_at <= p_starts_at or p_ends_at - p_starts_at > interval '24 hours'
     or pg_catalog.mod(extract(epoch from p_ends_at - p_starts_at), 60) <> 0 then
    raise exception using errcode = '22023', message = 'Invalid session details';
  end if;

  insert into public.schedule_sessions (workspace_id, batch_id, starts_at, ends_at, created_by, creation_request_id)
  values (p_workspace_id, p_batch_id, p_starts_at, p_ends_at, v_actor, p_request_id)
  on conflict (created_by, creation_request_id) do nothing
  returning id into v_id;
  if v_id is not null then return v_id; end if;

  select id, workspace_id, batch_id, starts_at, ends_at into v_existing
  from public.schedule_sessions where created_by = v_actor and creation_request_id = p_request_id;
  if not found or v_existing.workspace_id is distinct from p_workspace_id
     or v_existing.batch_id is distinct from p_batch_id
     or v_existing.starts_at is distinct from p_starts_at
     or v_existing.ends_at is distinct from p_ends_at then
    raise exception using errcode = '23505', message = 'Session request conflicts with existing details';
  end if;
  return v_existing.id;
end;
$$;
revoke all on function public.create_private_session(uuid, uuid, timestamptz, timestamptz, uuid) from public, anon, authenticated;

-- Null means scheduling is unavailable until a trusted configuration exists.
alter table public.workspaces add column scheduling_time_zone text;

-- Private draft only: app roles cannot call it. The bounded second-resolution
-- search avoids silently guessing offsets during gaps or repeated local times.
create function public.create_private_local_session(
  p_workspace_id uuid, p_batch_id uuid, p_local_start timestamp,
  p_duration_minutes integer, p_request_id uuid
)
returns uuid
language plpgsql
set search_path = ''
as $$
declare
  v_zone text;
  v_anchor timestamptz;
  v_start timestamptz;
  v_count bigint;
begin
  perform public.assert_schedule_write_access(p_workspace_id, p_batch_id);
  select scheduling_time_zone into v_zone from public.workspaces where id = p_workspace_id;
  if v_zone is null or not exists (select 1 from pg_catalog.pg_timezone_names where name = v_zone)
     or p_local_start is null or not pg_catalog.isfinite(p_local_start)
     or p_local_start < timestamp '2000-01-01 00:00'
     or p_local_start >= timestamp '2101-01-01 00:00'
     or p_local_start <> pg_catalog.date_trunc('minute', p_local_start)
     or p_duration_minutes is null or p_duration_minutes < 1 or p_duration_minutes > 1440 then
    raise exception using errcode = '22023', message = 'Invalid local session details';
  end if;
  v_anchor := p_local_start at time zone v_zone;
  select count(*), min(candidate) into v_count, v_start
  from pg_catalog.generate_series(v_anchor - interval '26 hours', v_anchor + interval '26 hours', interval '1 second') candidate
  where pg_catalog.timezone(v_zone, candidate) = p_local_start;
  if v_count <> 1 then
    raise exception using errcode = '22023', message = 'Local time is ambiguous or nonexistent';
  end if;
  return public.create_private_session(p_workspace_id, p_batch_id, v_start,
    v_start + p_duration_minutes * interval '1 minute', p_request_id);
end;
$$;
revoke all on function public.create_private_local_session(uuid, uuid, timestamp, integer, uuid) from public, anon, authenticated;

-- Private initial configuration only. Changing an established zone requires
-- an explicit policy for existing sessions and recurrence before exposure.
create function public.configure_private_workspace_zone(p_workspace_id uuid, p_zone text)
returns void
language plpgsql
set search_path = ''
as $$
declare
  v_actor uuid := auth.uid();
  v_existing text;
begin
  if v_actor is null or p_workspace_id is null then
    raise exception using errcode = '42501', message = 'Workspace zone access denied';
  end if;
  select scheduling_time_zone into v_existing from public.workspaces
    where id = p_workspace_id and status = 'active' for update;
  if not found then
    raise exception using errcode = '42501', message = 'Workspace zone access denied';
  end if;
  perform 1 from public.workspace_memberships
    where workspace_id = p_workspace_id and user_id = v_actor
      and status = 'active' and role in ('owner', 'admin') for share;
  if not found then
    raise exception using errcode = '42501', message = 'Workspace zone access denied';
  end if;
  if p_zone is null or not exists (select 1 from pg_catalog.pg_timezone_names where name = p_zone) then
    raise exception using errcode = '22023', message = 'Invalid workspace time zone';
  end if;
  if v_existing is not null and v_existing <> p_zone then
    raise exception using errcode = '23514', message = 'Workspace time zone already configured';
  end if;
  if v_existing is null then
    update public.workspaces set scheduling_time_zone = p_zone where id = p_workspace_id;
  end if;
end;
$$;
revoke all on function public.configure_private_workspace_zone(uuid, text) from public, anon, authenticated;

-- Private creation metadata. Null pairs allow controlled historical fixture/import rows.
alter table public.courses add column created_by uuid references auth.users(id), add column creation_request_id uuid,
  add constraint course_request_pair check ((created_by is null) = (creation_request_id is null)),
  add constraint course_request_unique unique (created_by, creation_request_id);
alter table public.batches add column created_by uuid references auth.users(id), add column creation_request_id uuid,
  add constraint batch_request_pair check ((created_by is null) = (creation_request_id is null)),
  add constraint batch_request_unique unique (created_by, creation_request_id);

create function public.assert_private_workspace_manager(p_workspace_id uuid)
returns void language plpgsql set search_path = '' as $$
declare v_actor uuid := auth.uid();
begin
  if v_actor is null or p_workspace_id is null then
    raise exception using errcode='42501', message='Workspace access denied';
  end if;
  perform 1 from public.workspaces where id=p_workspace_id and status='active' for share;
  if not found then raise exception using errcode='42501', message='Workspace access denied'; end if;
  perform 1 from public.workspace_memberships where workspace_id=p_workspace_id and user_id=v_actor and status='active' and role in ('owner','admin') for share;
  if not found then raise exception using errcode='42501', message='Workspace access denied'; end if;
end;
$$;
revoke all on function public.assert_private_workspace_manager(uuid) from public, anon, authenticated;

create function public.create_private_course(p_workspace_id uuid, p_name text, p_request_id uuid)
returns uuid language plpgsql set search_path = '' as $$
declare v_id uuid; v_existing record; v_name text := pg_catalog.btrim(p_name); v_actor uuid := auth.uid();
begin
  perform public.assert_private_workspace_manager(p_workspace_id);
  if p_request_id is null or v_name is null or pg_catalog.length(v_name) not between 1 and 120 then
    raise exception using errcode='22023', message='Invalid course details';
  end if;
  insert into public.courses (workspace_id, name, created_by, creation_request_id)
    values (p_workspace_id, v_name, v_actor, p_request_id)
    on conflict (created_by, creation_request_id) do nothing returning id into v_id;
  if v_id is not null then return v_id; end if;
  select id, workspace_id, name into v_existing from public.courses where created_by=v_actor and creation_request_id=p_request_id;
  if not found or v_existing.workspace_id is distinct from p_workspace_id or v_existing.name is distinct from v_name then
    raise exception using errcode='23505', message='Course request conflicts with existing details';
  end if;
  return v_existing.id;
end;
$$;
revoke all on function public.create_private_course(uuid, text, uuid) from public, anon, authenticated;

create function public.create_private_batch(p_workspace_id uuid, p_course_id uuid, p_name text, p_request_id uuid)
returns uuid language plpgsql set search_path = '' as $$
declare v_id uuid; v_existing record; v_name text := pg_catalog.btrim(p_name); v_actor uuid := auth.uid();
begin
  perform public.assert_private_workspace_manager(p_workspace_id);
  if p_course_id is null or p_request_id is null or v_name is null or pg_catalog.length(v_name) not between 1 and 120 then
    raise exception using errcode='22023', message='Invalid batch details';
  end if;
  perform 1 from public.courses where workspace_id=p_workspace_id and id=p_course_id for key share;
  if not found then raise exception using errcode='22023', message='Invalid batch details'; end if;
  insert into public.batches (workspace_id, course_id, name, created_by, creation_request_id)
    values (p_workspace_id, p_course_id, v_name, v_actor, p_request_id)
    on conflict (created_by, creation_request_id) do nothing returning id into v_id;
  if v_id is not null then return v_id; end if;
  select id, workspace_id, course_id, name into v_existing from public.batches where created_by=v_actor and creation_request_id=p_request_id;
  if not found or v_existing.workspace_id is distinct from p_workspace_id or v_existing.course_id is distinct from p_course_id or v_existing.name is distinct from v_name then
    raise exception using errcode='23505', message='Batch request conflicts with existing details';
  end if;
  return v_existing.id;
end;
$$;
revoke all on function public.create_private_batch(uuid, uuid, text, uuid) from public, anon, authenticated;

-- Local-only assignment operation; app roles remain unable to execute it.
create function public.assign_private_batch_coach(p_workspace_id uuid, p_batch_id uuid, p_membership_id uuid)
returns void language plpgsql set search_path = '' as $$
begin
  perform public.assert_private_workspace_manager(p_workspace_id);
  if p_batch_id is null or p_membership_id is null then
    raise exception using errcode='22023', message='Invalid coach assignment';
  end if;
  perform 1 from public.batches where workspace_id=p_workspace_id and id=p_batch_id for share;
  if not found then raise exception using errcode='22023', message='Invalid coach assignment'; end if;
  perform 1 from public.workspace_memberships where workspace_id=p_workspace_id and id=p_membership_id and role='coach' and status='active' for share;
  if not found then raise exception using errcode='22023', message='Invalid coach assignment'; end if;
  insert into public.batch_coach_assignments (workspace_id, batch_id, membership_id)
    values (p_workspace_id, p_batch_id, p_membership_id) on conflict do nothing;
end;
$$;
revoke all on function public.assign_private_batch_coach(uuid, uuid, uuid) from public, anon, authenticated;
