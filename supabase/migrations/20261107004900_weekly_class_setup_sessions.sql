-- Local-only weekly session creation, atomically coupled to class setup.
begin;

create table public.class_setup_session_series (
  class_setup_intent_id uuid primary key,
  actor_id uuid not null references auth.users(id),
  workspace_id uuid not null references public.workspaces(id),
  batch_id uuid not null,
  time_zone text not null,
  start_date date not null,
  start_time time not null,
  end_date date not null,
  duration_minutes integer not null,
  occurrence_count integer not null,
  created_at timestamptz not null default pg_catalog.now(),
  foreign key (workspace_id, batch_id) references public.batches(workspace_id, id),
  check (pg_catalog.isfinite(start_date) and pg_catalog.isfinite(end_date)
    and end_date >= start_date and duration_minutes between 1 and 1440
    and occurrence_count between 1 and 104)
);
alter table public.class_setup_session_series enable row level security;
revoke all on public.class_setup_session_series from public, anon, authenticated;

alter table public.schedule_sessions
  add column class_setup_intent_id uuid,
  add column local_date date,
  add constraint schedule_sessions_series_pair
    check ((class_setup_intent_id is null) = (local_date is null)),
  add constraint schedule_sessions_series_fk
    foreign key (class_setup_intent_id) references public.class_setup_session_series(class_setup_intent_id),
  add constraint schedule_sessions_series_date_unique
    unique (class_setup_intent_id, local_date);

create function public.complete_private_class_setup_weekly(
  p_workspace_id uuid,
  p_intent_id uuid,
  p_time_zone text,
  p_start_date date,
  p_start_time time,
  p_end_date date,
  p_duration_minutes integer
)
returns table (course_id uuid, batch_id uuid, time_zone text,
               start_date date, start_time time, end_date date,
               duration_minutes integer, occurrence_count integer)
language plpgsql set search_path = '' as $$
declare
  v_intent public.class_setup_intents%rowtype;
  v_course uuid;
  v_batch uuid;
  v_date date;
  v_count integer;
  v_session_id uuid;
  v_session_request uuid;
  v_existing public.class_setup_session_series%rowtype;
begin
  perform public.assert_private_class_setup_enabled();
  perform public.assert_private_workspace_manager(p_workspace_id);
  if p_intent_id is null or p_time_zone is null
     or not exists (select 1 from pg_catalog.pg_timezone_names z where z.name = p_time_zone)
     or p_start_date is null or not pg_catalog.isfinite(p_start_date)
     or p_start_date < date '2000-01-01' or p_start_date >= date '2101-01-01'
     or p_end_date is null or not pg_catalog.isfinite(p_end_date)
     or p_end_date < p_start_date or p_end_date >= date '2101-01-01'
     or p_start_time is null or p_start_time <> pg_catalog.date_trunc('minute', p_start_time)
     or p_duration_minutes is null or p_duration_minutes not between 1 and 1440 then
    raise exception using errcode = '22023', message = 'Invalid weekly schedule details';
  end if;
  v_count := ((p_end_date - p_start_date) / 7) + 1;
  if v_count not between 1 and 104 then
    raise exception using errcode = '22023', message = 'Weekly schedule exceeds the allowed range';
  end if;

  -- A workspace time zone is set once, by an owner or admin. The operation
  -- and zone change share this transaction, so a failed schedule leaves neither.
  perform public.configure_private_workspace_zone(p_workspace_id, p_time_zone);
  select i.* into v_intent from public.class_setup_intents i
    where i.id = p_intent_id and i.workspace_id = p_workspace_id
      and i.actor_id = auth.uid() for update;
  if not found then
    raise exception using errcode = '42501', message = 'Class setup unavailable';
  end if;

  if v_intent.completed_course_id is not null then
    select s.* into v_existing from public.class_setup_session_series s
      where s.class_setup_intent_id = p_intent_id;
    if not found or v_existing.actor_id is distinct from auth.uid()
       or v_existing.workspace_id is distinct from p_workspace_id
       or v_existing.time_zone is distinct from p_time_zone
       or v_existing.start_date is distinct from p_start_date
       or v_existing.start_time is distinct from p_start_time
       or v_existing.end_date is distinct from p_end_date
       or v_existing.duration_minutes is distinct from p_duration_minutes then
      raise exception using errcode = '23505', message = 'Completed schedule details cannot be changed';
    end if;
    return query select v_intent.completed_course_id, v_intent.completed_batch_id,
      v_existing.time_zone, v_existing.start_date, v_existing.start_time,
      v_existing.end_date, v_existing.duration_minutes, v_existing.occurrence_count;
    return;
  end if;

  insert into public.courses (workspace_id, name, created_by, creation_request_id)
    values (p_workspace_id, v_intent.course_name, auth.uid(), pg_catalog.gen_random_uuid())
    returning id into v_course;
  insert into public.batches (workspace_id, course_id, name, created_by, creation_request_id)
    values (p_workspace_id, v_course, v_intent.batch_name, auth.uid(), pg_catalog.gen_random_uuid())
    returning id into v_batch;

  insert into public.class_setup_session_series (
    class_setup_intent_id, actor_id, workspace_id, batch_id, time_zone,
    start_date, start_time, end_date, duration_minutes, occurrence_count
  ) values (
    p_intent_id, auth.uid(), p_workspace_id, v_batch, p_time_zone,
    p_start_date, p_start_time, p_end_date, p_duration_minutes, v_count
  );

  for v_date in
    select g::date from pg_catalog.generate_series(
      p_start_date::timestamp, p_end_date::timestamp, interval '7 days') g
  loop
    v_session_request := pg_catalog.md5(
      auth.uid()::text || ':' || p_intent_id::text || ':' || v_date::text
    )::uuid;
    v_session_id := public.create_private_local_session(
      p_workspace_id, v_batch, v_date + p_start_time,
      p_duration_minutes, v_session_request
    );
    update public.schedule_sessions s
      set class_setup_intent_id = p_intent_id, local_date = v_date
      where s.id = v_session_id and s.created_by = auth.uid();
    if not found then
      raise exception using errcode = '55000', message = 'Weekly schedule persistence failed';
    end if;
  end loop;

  update public.class_setup_intents i
    set completed_course_id = v_course, completed_batch_id = v_batch
    where i.id = p_intent_id;
  return query select v_course, v_batch, p_time_zone, p_start_date,
    p_start_time, p_end_date, p_duration_minutes, v_count;
end;
$$;
revoke all on function public.complete_private_class_setup_weekly(uuid,uuid,text,date,time,date,integer)
  from public, anon, authenticated;

create function public.app_complete_class_setup_weekly(
  p_workspace_id uuid, p_intent_id uuid, p_time_zone text,
  p_start_date date, p_start_time time, p_end_date date,
  p_duration_minutes integer
)
returns table (course_id uuid, batch_id uuid, time_zone text,
               start_date date, start_time time, end_date date,
               duration_minutes integer, occurrence_count integer)
language sql security definer set search_path = '' as $$
  select * from public.complete_private_class_setup_weekly(
    p_workspace_id, p_intent_id, p_time_zone, p_start_date, p_start_time,
    p_end_date, p_duration_minutes)
$$;
revoke all on function public.app_complete_class_setup_weekly(uuid,uuid,text,date,time,date,integer)
  from public, anon, authenticated;
grant execute on function public.app_complete_class_setup_weekly(uuid,uuid,text,date,time,date,integer)
  to authenticated;

-- The previous authenticated RPC could complete only the course and batch.
-- Disable it so callers cannot bypass creation of the weekly series/sessions.
revoke all on function public.app_complete_class_setup(uuid,uuid)
  from public, anon, authenticated;

create function public.recover_private_current_class_setup_v2(p_workspace_id uuid)
returns table (state text, intent_id uuid, prior_intent_id uuid, request_id uuid,
               course_name text, batch_name text, course_id uuid, batch_id uuid,
               acknowledged boolean, time_zone text, start_date date,
               start_time time, end_date date, duration_minutes integer,
               occurrence_count integer)
language sql set search_path = '' as $$
  select c.state, c.intent_id, c.prior_intent_id, c.request_id,
    c.course_name, c.batch_name, c.course_id, c.batch_id, c.acknowledged,
    s.time_zone, s.start_date, s.start_time, s.end_date,
    s.duration_minutes, s.occurrence_count
  from public.recover_private_current_class_setup(p_workspace_id) c
  left join public.class_setup_session_series s
    on s.class_setup_intent_id = c.intent_id
$$;
revoke all on function public.recover_private_current_class_setup_v2(uuid)
  from public, anon, authenticated;

create function public.app_current_class_setup_v2(p_workspace_id uuid)
returns table (state text, intent_id uuid, prior_intent_id uuid, request_id uuid,
               course_name text, batch_name text, course_id uuid, batch_id uuid,
               acknowledged boolean, time_zone text, start_date date,
               start_time time, end_date date, duration_minutes integer,
               occurrence_count integer)
language sql security definer set search_path = '' as $$
  select * from public.recover_private_current_class_setup_v2(p_workspace_id)
$$;
revoke all on function public.app_current_class_setup_v2(uuid)
  from public, anon, authenticated;
grant execute on function public.app_current_class_setup_v2(uuid) to authenticated;

commit;
