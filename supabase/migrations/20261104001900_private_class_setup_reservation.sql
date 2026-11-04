-- Local-only prototype: no application-role access, no completion or release operation.
begin;
create table public.class_setup_intents (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid not null references auth.users(id),
  workspace_id uuid not null references public.workspaces(id),
  course_name text not null,
  batch_name text not null,
  unique (actor_id, workspace_id)
);
alter table public.class_setup_intents enable row level security;
revoke all on public.class_setup_intents from public, anon, authenticated;

create function public.reserve_private_class_setup(p_workspace_id uuid, p_course_name text, p_batch_name text)
returns uuid language plpgsql set search_path = '' as $$
declare
  v_actor uuid := auth.uid();
  v_course text := pg_catalog.btrim(p_course_name);
  v_batch text := pg_catalog.btrim(p_batch_name);
  v_intent public.class_setup_intents%rowtype;
begin
  perform public.assert_private_workspace_manager(p_workspace_id);
  perform public.assert_private_class_setup_enabled();
  if v_course is null or pg_catalog.length(v_course) not between 1 and 120
     or v_batch is null or pg_catalog.length(v_batch) not between 1 and 120 then
    raise exception using errcode='22023', message='Invalid class setup details';
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
revoke all on function public.reserve_private_class_setup(uuid,text,text) from public, anon, authenticated;
commit;
