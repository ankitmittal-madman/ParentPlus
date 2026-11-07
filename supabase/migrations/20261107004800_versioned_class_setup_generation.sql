-- Local-only class setup fence: delayed workspace requests carry an observed
-- generation and a stable request ID. Hosted rollout remains disabled.
begin;

-- Drain pre-fence writers before deriving the current workspace generation.
lock table public.class_setup_intents, public.class_setup_intent_history in access exclusive mode;

alter table public.class_setup_intents
  add column generation bigint not null default 1 check (generation > 0);
alter table public.class_setup_intent_history
  add column generation bigint not null default 1 check (generation > 0);

create table public.class_setup_workspace_versions (
  workspace_id uuid primary key references public.workspaces(id) on delete cascade,
  next_generation bigint not null default 1 check (next_generation > 0)
);
create table public.class_setup_begin_requests (
  actor_id uuid not null references auth.users(id),
  request_id uuid not null,
  workspace_id uuid not null references public.workspaces(id),
  expected_generation bigint not null check (expected_generation > 0),
  course_name text not null check (length(trim(course_name)) between 1 and 120),
  batch_name text not null check (length(trim(batch_name)) between 1 and 120),
  intent_id uuid not null,
  primary key (actor_id, request_id)
);
create index class_setup_begin_requests_workspace_generation_idx
  on public.class_setup_begin_requests (workspace_id, expected_generation);

alter table public.class_setup_workspace_versions enable row level security;
alter table public.class_setup_begin_requests enable row level security;
revoke all on public.class_setup_workspace_versions, public.class_setup_begin_requests
  from public, anon, authenticated;

-- Existing acknowledged rows represent generations already consumed. Keep the
-- next token monotonic for pre-migration workspaces without guessing a new ID.
insert into public.class_setup_workspace_versions (workspace_id, next_generation)
select w.id, 1 + coalesce(h.count, 0) + coalesce(a.count, 0)
from public.workspaces w
left join (
  select workspace_id, count(*) as count
  from public.class_setup_intent_history group by workspace_id
) h on h.workspace_id = w.id
left join (
  select workspace_id, count(*) as count
  from public.class_setup_intents where acknowledged group by workspace_id
) a on a.workspace_id = w.id;
update public.class_setup_intents i
set generation = case when i.acknowledged then v.next_generation - 1 else v.next_generation end
from public.class_setup_workspace_versions v
where v.workspace_id = i.workspace_id;

-- The old three-argument RPC cannot distinguish a delayed retry from a new
-- class after another manager acknowledges the current setup.
revoke all on function public.app_begin_class_setup(uuid, text, text)
  from public, anon, authenticated;

create function public.get_private_class_setup_generation(p_workspace_id uuid)
returns table (generation bigint, available boolean)
language plpgsql set search_path = '' as $$
declare v_generation bigint;
begin
  perform public.assert_private_workspace_manager(p_workspace_id);
  perform public.assert_private_class_setup_enabled();
  insert into public.class_setup_workspace_versions (workspace_id)
    values (p_workspace_id) on conflict (workspace_id) do nothing;
  select v.next_generation into strict v_generation
  from public.class_setup_workspace_versions v
  where v.workspace_id = p_workspace_id for share;
  return query select v_generation, not exists (
    select 1 from public.class_setup_intents i
    where i.workspace_id = p_workspace_id and not i.acknowledged
  );
end;
$$;
revoke all on function public.get_private_class_setup_generation(uuid)
  from public, anon, authenticated;

create function public.app_class_setup_generation(p_workspace_id uuid)
returns table (generation bigint, available boolean)
language sql security definer set search_path = '' as $$
  select * from public.get_private_class_setup_generation(p_workspace_id)
$$;
revoke all on function public.app_class_setup_generation(uuid)
  from public, anon, authenticated;
grant execute on function public.app_class_setup_generation(uuid) to authenticated;

create function public.begin_private_class_setup(
  p_workspace_id uuid, p_expected_generation bigint, p_request_id uuid,
  p_course_name text, p_batch_name text
)
returns table (disposition text, state text, intent_id uuid, generation bigint)
language plpgsql set search_path = '' as $$
declare
  v_actor uuid := auth.uid();
  v_generation bigint;
  v_course text := pg_catalog.btrim(p_course_name);
  v_batch text := pg_catalog.btrim(p_batch_name);
  v_receipt public.class_setup_begin_requests%rowtype;
  v_intent public.class_setup_intents%rowtype;
  v_history public.class_setup_intent_history%rowtype;
  v_id uuid;
  v_state text;
begin
  perform public.assert_private_workspace_manager(p_workspace_id);
  perform public.assert_private_class_setup_enabled();
  if p_expected_generation is null or p_expected_generation < 1 or p_request_id is null
     or v_course is null or pg_catalog.length(v_course) not between 1 and 120
     or v_batch is null or pg_catalog.length(v_batch) not between 1 and 120 then
    raise exception using errcode = '22023', message = 'Invalid class setup details';
  end if;

  insert into public.class_setup_workspace_versions (workspace_id)
    values (p_workspace_id) on conflict (workspace_id) do nothing;
  select v.next_generation into strict v_generation
  from public.class_setup_workspace_versions v
  where v.workspace_id = p_workspace_id for update;

  select r.* into v_receipt from public.class_setup_begin_requests r
  where r.actor_id = v_actor and r.request_id = p_request_id for update;
  if found then
    if v_receipt.workspace_id is distinct from p_workspace_id
       or v_receipt.expected_generation is distinct from p_expected_generation
       or v_receipt.course_name is distinct from v_course
       or v_receipt.batch_name is distinct from v_batch then
      raise exception using errcode = '23505', message = 'Class setup request conflicts with existing details';
    end if;
    select i.* into v_intent from public.class_setup_intents i
      where i.id = v_receipt.intent_id and i.actor_id = v_actor and i.workspace_id = p_workspace_id;
    if found then
      v_state := case when v_intent.acknowledged then 'acknowledged'
                      when v_intent.completed_course_id is not null then 'completed'
                      else 'pending' end;
    else
      select h.* into v_history from public.class_setup_intent_history h
        where h.id = v_receipt.intent_id and h.actor_id = v_actor and h.workspace_id = p_workspace_id;
      if not found then
        raise exception using errcode = '55000', message = 'Class setup recovery unavailable';
      end if;
      v_state := 'acknowledged';
    end if;
    return query select 'existing'::text, v_state, v_receipt.intent_id, v_receipt.expected_generation;
    return;
  end if;

  if p_expected_generation is distinct from v_generation then
    raise exception using errcode = '40001', message = 'Workspace setup changed; refresh before starting another class';
  end if;

  select i.* into v_intent from public.class_setup_intents i
  where i.workspace_id = p_workspace_id and not i.acknowledged for update;
  if found then
    if v_intent.actor_id is distinct from v_actor
       or v_intent.generation is distinct from p_expected_generation
       or v_intent.course_name is distinct from v_course
       or v_intent.batch_name is distinct from v_batch then
      raise exception using errcode = '55000', message = 'Resolve the current workspace class setup first';
    end if;
    v_id := v_intent.id;
    v_state := case when v_intent.completed_course_id is not null then 'completed' else 'pending' end;
    insert into public.class_setup_begin_requests
      (actor_id, request_id, workspace_id, expected_generation, course_name, batch_name, intent_id)
    values (v_actor, p_request_id, p_workspace_id, p_expected_generation, v_course, v_batch, v_id);
    return query select 'existing'::text, v_state, v_id, p_expected_generation;
    return;
  end if;

  -- Archive this actor's prior acknowledged result before replacing its single
  -- live row. Other managers may retain their own acknowledged history rows.
  select i.* into v_intent from public.class_setup_intents i
  where i.actor_id = v_actor and i.workspace_id = p_workspace_id for update;
  if found then
    if not v_intent.acknowledged or v_intent.completed_course_id is null then
      raise exception using errcode = '55000', message = 'Resolve the existing class setup first';
    end if;
    insert into public.class_setup_intent_history
      (id, actor_id, workspace_id, course_name, batch_name,
       completed_course_id, completed_batch_id, acknowledged, generation)
    values (v_intent.id, v_intent.actor_id, v_intent.workspace_id, v_intent.course_name,
       v_intent.batch_name, v_intent.completed_course_id, v_intent.completed_batch_id,
       v_intent.acknowledged, v_intent.generation);
    delete from public.class_setup_intents i where i.id = v_intent.id;
  end if;

  insert into public.class_setup_intents
    (actor_id, workspace_id, course_name, batch_name, generation)
  values (v_actor, p_workspace_id, v_course, v_batch, p_expected_generation)
  returning id into v_id;
  insert into public.class_setup_begin_requests
    (actor_id, request_id, workspace_id, expected_generation, course_name, batch_name, intent_id)
  values (v_actor, p_request_id, p_workspace_id, p_expected_generation, v_course, v_batch, v_id);
  return query select 'created'::text, 'pending'::text, v_id, p_expected_generation;
end;
$$;
revoke all on function public.begin_private_class_setup(uuid, bigint, uuid, text, text)
  from public, anon, authenticated;

create function public.app_begin_class_setup_v2(
  p_workspace_id uuid, p_expected_generation bigint, p_request_id uuid,
  p_course_name text, p_batch_name text
)
returns table (disposition text, state text, intent_id uuid, generation bigint)
language sql security definer set search_path = '' as $$
  select * from public.begin_private_class_setup(
    p_workspace_id, p_expected_generation, p_request_id, p_course_name, p_batch_name)
$$;
revoke all on function public.app_begin_class_setup_v2(uuid, bigint, uuid, text, text)
  from public, anon, authenticated;
grant execute on function public.app_begin_class_setup_v2(uuid, bigint, uuid, text, text)
  to authenticated;

create or replace function public.acknowledge_private_class_setup(p_workspace_id uuid, p_intent_id uuid)
returns boolean language plpgsql set search_path = '' as $$
declare
  v_intent public.class_setup_intents%rowtype;
  v_generation bigint;
begin
  perform public.assert_private_workspace_manager(p_workspace_id);
  perform public.assert_private_class_setup_enabled();
  insert into public.class_setup_workspace_versions (workspace_id)
    values (p_workspace_id) on conflict (workspace_id) do nothing;
  select v.next_generation into strict v_generation
  from public.class_setup_workspace_versions v
  where v.workspace_id = p_workspace_id for update;
  select i.* into v_intent from public.class_setup_intents i
    where i.id = p_intent_id and i.workspace_id = p_workspace_id and i.actor_id = auth.uid() for update;
  if not found then
    raise exception using errcode = '42501', message = 'Class setup unavailable';
  end if;
  if v_intent.completed_course_id is null then
    raise exception using errcode = '55000', message = 'Class setup is not complete';
  end if;
  if not v_intent.acknowledged then
    update public.class_setup_intents i set acknowledged = true where i.id = v_intent.id;
    update public.class_setup_workspace_versions v
      set next_generation = v_generation + 1 where v.workspace_id = p_workspace_id;
  end if;
  return true;
end;
$$;
revoke all on function public.acknowledge_private_class_setup(uuid, uuid)
  from public, anon, authenticated;

create or replace function public.advance_private_class_setup(
  p_workspace_id uuid, p_prior_intent_id uuid, p_request_id uuid,
  p_course_name text, p_batch_name text
)
returns uuid language plpgsql set search_path = '' as $$
declare
  v_actor uuid := auth.uid();
  v_course text := pg_catalog.btrim(p_course_name);
  v_batch text := pg_catalog.btrim(p_batch_name);
  v_generation bigint;
  v_prior public.class_setup_intents%rowtype;
  v_receipt public.class_setup_next_requests%rowtype;
  v_next uuid;
begin
  perform public.assert_private_workspace_manager(p_workspace_id);
  perform public.assert_private_class_setup_enabled();
  if p_prior_intent_id is null or p_request_id is null
     or v_course is null or pg_catalog.length(v_course) not between 1 and 120
     or v_batch is null or pg_catalog.length(v_batch) not between 1 and 120 then
    raise exception using errcode = '22023', message = 'Invalid class setup details';
  end if;
  insert into public.class_setup_workspace_versions (workspace_id)
    values (p_workspace_id) on conflict (workspace_id) do nothing;
  select v.next_generation into strict v_generation
  from public.class_setup_workspace_versions v
  where v.workspace_id = p_workspace_id for update;
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(v_actor::text || ':' || p_workspace_id::text, 0));
  select r.* into v_receipt from public.class_setup_next_requests r
    where r.actor_id = v_actor and r.request_id = p_request_id;
  if found then
    if v_receipt.workspace_id is distinct from p_workspace_id
       or v_receipt.prior_intent_id is distinct from p_prior_intent_id
       or v_receipt.course_name is distinct from v_course
       or v_receipt.batch_name is distinct from v_batch then
      raise exception using errcode = '23505', message = 'Class setup request conflicts with existing details';
    end if;
    return v_receipt.next_intent_id;
  end if;
  select i.* into v_prior from public.class_setup_intents i
    where i.actor_id = v_actor and i.workspace_id = p_workspace_id for update;
  if not found or v_prior.id is distinct from p_prior_intent_id
     or not v_prior.acknowledged or v_prior.completed_course_id is null then
    raise exception using errcode = '55000', message = 'Resolve the existing class setup first';
  end if;
  insert into public.class_setup_intent_history
    (id, actor_id, workspace_id, course_name, batch_name,
     completed_course_id, completed_batch_id, acknowledged, generation)
  values (v_prior.id, v_prior.actor_id, v_prior.workspace_id, v_prior.course_name,
     v_prior.batch_name, v_prior.completed_course_id, v_prior.completed_batch_id,
     v_prior.acknowledged, v_prior.generation);
  delete from public.class_setup_intents i where i.id = v_prior.id;
  insert into public.class_setup_intents
    (actor_id, workspace_id, course_name, batch_name, generation)
  values (v_actor, p_workspace_id, v_course, v_batch, v_generation)
  returning id into v_next;
  insert into public.class_setup_next_requests
    (actor_id, request_id, workspace_id, prior_intent_id, course_name, batch_name, next_intent_id)
  values (v_actor, p_request_id, p_workspace_id, p_prior_intent_id, v_course, v_batch, v_next);
  return v_next;
end;
$$;
revoke all on function public.advance_private_class_setup(uuid, uuid, uuid, text, text)
  from public, anon, authenticated;

commit;
