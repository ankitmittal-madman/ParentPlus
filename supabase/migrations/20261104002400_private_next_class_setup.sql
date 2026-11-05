-- Local-only protocol draft. App roles have no access to these objects.
begin;
create table public.class_setup_intent_history (
  id uuid primary key,
  actor_id uuid not null references auth.users(id),
  workspace_id uuid not null references public.workspaces(id),
  course_name text not null,
  batch_name text not null,
  completed_course_id uuid not null,
  completed_batch_id uuid not null,
  acknowledged boolean not null check (acknowledged),
  foreign key (workspace_id, completed_course_id) references public.courses(workspace_id, id),
  foreign key (workspace_id, completed_batch_id) references public.batches(workspace_id, id)
);
create table public.class_setup_next_requests (
  actor_id uuid not null references auth.users(id),
  request_id uuid not null,
  workspace_id uuid not null references public.workspaces(id),
  prior_intent_id uuid not null references public.class_setup_intent_history(id),
  course_name text not null,
  batch_name text not null,
  next_intent_id uuid not null,
  primary key (actor_id, request_id)
);
alter table public.class_setup_intent_history enable row level security;
alter table public.class_setup_next_requests enable row level security;
revoke all on public.class_setup_intent_history,public.class_setup_next_requests from public,anon,authenticated;

-- The legacy request contains no stable request ID. Once a next generation
-- exists it must not be allowed to bind a delayed request to the new slot.
create or replace function public.reserve_private_class_setup(p_workspace_id uuid, p_course_name text, p_batch_name text)
returns uuid language plpgsql set search_path = '' as $$
declare
  v_actor uuid := auth.uid();
  v_course text := pg_catalog.btrim(p_course_name);
  v_batch text := pg_catalog.btrim(p_batch_name);
  v_intent public.class_setup_intents%rowtype;
begin
  perform public.assert_private_workspace_manager(p_workspace_id);
  perform public.assert_private_class_setup_enabled();
  if v_course is null or pg_catalog.length(v_course) not between 1 and 120 or v_batch is null or pg_catalog.length(v_batch) not between 1 and 120 then
    raise exception using errcode='22023', message='Invalid class setup details';
  end if;
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(v_actor::text || ':' || p_workspace_id::text, 0));
  if exists (select 1 from public.class_setup_intent_history h where h.actor_id=v_actor and h.workspace_id=p_workspace_id) then
    raise exception using errcode='55000', message='Use the next class setup request';
  end if;
  insert into public.class_setup_intents (actor_id, workspace_id, course_name, batch_name)
    values (v_actor, p_workspace_id, v_course, v_batch)
    on conflict (actor_id, workspace_id) do nothing;
  select * into strict v_intent from public.class_setup_intents
    where actor_id=v_actor and workspace_id=p_workspace_id for update;
  if v_intent.course_name is distinct from v_course or v_intent.batch_name is distinct from v_batch then
    raise exception using errcode='23505', message='Resolve the existing class setup first';
  end if;
  return v_intent.id;
end;
$$;
revoke all on function public.reserve_private_class_setup(uuid,text,text) from public,anon,authenticated;

create function public.advance_private_class_setup(p_workspace_id uuid, p_prior_intent_id uuid, p_request_id uuid, p_course_name text, p_batch_name text)
returns uuid language plpgsql set search_path = '' as $$
declare
  v_actor uuid := auth.uid();
  v_course text := pg_catalog.btrim(p_course_name);
  v_batch text := pg_catalog.btrim(p_batch_name);
  v_prior public.class_setup_intents%rowtype;
  v_receipt public.class_setup_next_requests%rowtype;
  v_next uuid;
begin
  perform public.assert_private_workspace_manager(p_workspace_id);
  perform public.assert_private_class_setup_enabled();
  if p_prior_intent_id is null or p_request_id is null or v_course is null or pg_catalog.length(v_course) not between 1 and 120 or v_batch is null or pg_catalog.length(v_batch) not between 1 and 120 then
    raise exception using errcode='22023', message='Invalid class setup details';
  end if;
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(v_actor::text || ':' || p_workspace_id::text, 0));
  select r.* into v_receipt from public.class_setup_next_requests r where r.actor_id=v_actor and r.request_id=p_request_id;
  if found then
    if v_receipt.workspace_id is distinct from p_workspace_id or v_receipt.prior_intent_id is distinct from p_prior_intent_id or v_receipt.course_name is distinct from v_course or v_receipt.batch_name is distinct from v_batch then
      raise exception using errcode='23505', message='Class setup request conflicts with existing details';
    end if;
    return v_receipt.next_intent_id;
  end if;
  select i.* into v_prior from public.class_setup_intents i where i.actor_id=v_actor and i.workspace_id=p_workspace_id for update;
  if not found or v_prior.id is distinct from p_prior_intent_id or not v_prior.acknowledged or v_prior.completed_course_id is null then
    raise exception using errcode='55000', message='Resolve the existing class setup first';
  end if;
  insert into public.class_setup_intent_history (id,actor_id,workspace_id,course_name,batch_name,completed_course_id,completed_batch_id,acknowledged)
    values (v_prior.id,v_prior.actor_id,v_prior.workspace_id,v_prior.course_name,v_prior.batch_name,v_prior.completed_course_id,v_prior.completed_batch_id,v_prior.acknowledged);
  delete from public.class_setup_intents i where i.id=v_prior.id;
  insert into public.class_setup_intents (actor_id,workspace_id,course_name,batch_name)
    values (v_actor,p_workspace_id,v_course,v_batch) returning id into v_next;
  insert into public.class_setup_next_requests (actor_id,request_id,workspace_id,prior_intent_id,course_name,batch_name,next_intent_id)
    values (v_actor,p_request_id,p_workspace_id,p_prior_intent_id,v_course,v_batch,v_next);
  return v_next;
end;
$$;
revoke all on function public.advance_private_class_setup(uuid,uuid,uuid,text,text) from public,anon,authenticated;
commit;
