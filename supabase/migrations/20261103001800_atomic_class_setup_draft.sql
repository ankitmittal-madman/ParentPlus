-- The combined operation is independently gated in the database. The singleton
-- defaults off; application roles have no access to configure it.
create table public.class_setup_controls (
  id boolean primary key default true check (id),
  enabled boolean not null default false
);
insert into public.class_setup_controls (id, enabled) values (true, false);
alter table public.class_setup_controls enable row level security;
revoke all on public.class_setup_controls from public, anon, authenticated;

-- Shared gate applies to the standalone and combined creation entrypoints.
create function public.assert_private_class_setup_enabled()
returns void language plpgsql set search_path = '' as $$
declare v_enabled boolean;
begin
  select enabled into v_enabled from public.class_setup_controls where id=true for share;
  if not found or not v_enabled then
    raise exception using errcode='42501', message='Class setup unavailable';
  end if;
end;
$$;
revoke all on function public.assert_private_class_setup_enabled() from public, anon, authenticated;

create or replace function public.create_course(p_workspace_id uuid, p_name text, p_request_id uuid)
returns uuid language plpgsql security definer set search_path = '' as $$
begin
  perform public.assert_private_workspace_manager(p_workspace_id);
  perform public.assert_private_class_setup_enabled();
  return public.create_private_course(p_workspace_id, p_name, p_request_id);
end;
$$;
revoke all on function public.create_course(uuid,text,uuid) from public, anon, authenticated;
grant execute on function public.create_course(uuid,text,uuid) to authenticated;

create or replace function public.create_batch(p_workspace_id uuid, p_course_id uuid, p_name text, p_request_id uuid)
returns uuid language plpgsql security definer set search_path = '' as $$
begin
  perform public.assert_private_workspace_manager(p_workspace_id);
  perform public.assert_private_class_setup_enabled();
  return public.create_private_batch(p_workspace_id, p_course_id, p_name, p_request_id);
end;
$$;
revoke all on function public.create_batch(uuid,uuid,text,uuid) from public, anon, authenticated;
grant execute on function public.create_batch(uuid,uuid,text,uuid) to authenticated;

-- LOCAL DRAFT ONLY. Separate atomic receipts prevent adoption of standalone writes.
create table public.class_setup_requests (
  actor_id uuid not null references auth.users(id),
  request_id uuid not null,
  workspace_id uuid not null references public.workspaces(id),
  course_name text not null,
  batch_name text not null,
  course_id uuid,
  batch_id uuid,
  primary key (actor_id, request_id),
  check ((course_id is null) = (batch_id is null)),
  foreign key (workspace_id, course_id) references public.courses(workspace_id, id),
  foreign key (workspace_id, batch_id) references public.batches(workspace_id, id)
);
alter table public.class_setup_requests enable row level security;
revoke all on public.class_setup_requests from public, anon, authenticated;

-- Publish function and permissions atomically; the database control is already off.
do $migration$
begin
  execute $definition$
create function public.create_course_and_batch(p_workspace_id uuid, p_course_name text, p_batch_name text, p_request_id uuid)
returns table (course_id uuid, batch_id uuid)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_actor uuid := auth.uid();
  v_course_name text := pg_catalog.btrim(p_course_name);
  v_batch_name text := pg_catalog.btrim(p_batch_name);
  v_reserved uuid;
  v_prior record;
  v_course_id uuid;
  v_batch_id uuid;
begin
  perform public.assert_private_workspace_manager(p_workspace_id);
  perform public.assert_private_class_setup_enabled();
  if p_request_id is null or v_course_name is null or v_batch_name is null
     or pg_catalog.length(v_course_name) not between 1 and 120
     or pg_catalog.length(v_batch_name) not between 1 and 120 then
    raise exception using errcode='22023', message='Invalid class setup details';
  end if;
  insert into public.class_setup_requests (actor_id,request_id,workspace_id,course_name,batch_name)
    values (v_actor,p_request_id,p_workspace_id,v_course_name,v_batch_name)
    on conflict (actor_id,request_id) do nothing returning request_id into v_reserved;
  if v_reserved is null then
    select r.workspace_id,r.course_name,r.batch_name,r.course_id,r.batch_id into v_prior
      from public.class_setup_requests r where r.actor_id=v_actor and r.request_id=p_request_id;
    if not found or v_prior.workspace_id is distinct from p_workspace_id
       or v_prior.course_name is distinct from v_course_name or v_prior.batch_name is distinct from v_batch_name
       or v_prior.course_id is null or v_prior.batch_id is null then
      raise exception using errcode='23505', message='Class setup request conflicts with existing details';
    end if;
    return query select v_prior.course_id::uuid, v_prior.batch_id::uuid;
    return;
  end if;
  -- Internal request keys are generated separately; a collision fails and rolls back
  -- instead of reusing an independently created course or batch.
  insert into public.courses (workspace_id,name,created_by,creation_request_id)
    values (p_workspace_id,v_course_name,v_actor,pg_catalog.gen_random_uuid()) returning id into v_course_id;
  insert into public.batches (workspace_id,course_id,name,created_by,creation_request_id)
    values (p_workspace_id,v_course_id,v_batch_name,v_actor,pg_catalog.gen_random_uuid()) returning id into v_batch_id;
  update public.class_setup_requests r set course_id=v_course_id,batch_id=v_batch_id
    where r.actor_id=v_actor and r.request_id=p_request_id;
  return query select v_course_id,v_batch_id;
end;
$$;
$definition$;
  revoke all on function public.create_course_and_batch(uuid,text,text,uuid) from public, anon, authenticated;
  grant execute on function public.create_course_and_batch(uuid,text,text,uuid) to authenticated;
end;
$migration$;
