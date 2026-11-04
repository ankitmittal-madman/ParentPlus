-- Local-only private completion; recovery and acknowledgement remain unimplemented.
begin;
alter table public.class_setup_intents
  add column completed_course_id uuid,
  add column completed_batch_id uuid,
  add constraint class_setup_intents_completion_pair check ((completed_course_id is null) = (completed_batch_id is null)),
  add foreign key (workspace_id, completed_course_id) references public.courses(workspace_id, id),
  add foreign key (workspace_id, completed_batch_id) references public.batches(workspace_id, id);

create function public.complete_private_class_setup(p_workspace_id uuid, p_intent_id uuid)
returns table (course_id uuid, batch_id uuid)
language plpgsql set search_path = '' as $$
declare
  v_intent public.class_setup_intents%rowtype;
  v_course uuid;
  v_batch uuid;
begin
  perform public.assert_private_workspace_manager(p_workspace_id);
  perform public.assert_private_class_setup_enabled();
  select i.* into v_intent from public.class_setup_intents i
    where i.id=p_intent_id and i.workspace_id=p_workspace_id and i.actor_id=auth.uid()
    for update;
  if not found then
    raise exception using errcode='42501', message='Class setup unavailable';
  end if;
  if v_intent.completed_course_id is not null then
    return query select v_intent.completed_course_id, v_intent.completed_batch_id;
    return;
  end if;
  -- The intent itself is the receipt. Do not adopt a caller-controlled receipt
  -- from the separately callable atomic creation endpoint.
  insert into public.courses (workspace_id,name,created_by,creation_request_id)
    values (p_workspace_id,v_intent.course_name,auth.uid(),pg_catalog.gen_random_uuid()) returning id into v_course;
  insert into public.batches (workspace_id,course_id,name,created_by,creation_request_id)
    values (p_workspace_id,v_course,v_intent.batch_name,auth.uid(),pg_catalog.gen_random_uuid()) returning id into v_batch;
  update public.class_setup_intents i set completed_course_id=v_course,completed_batch_id=v_batch
    where i.id=v_intent.id;
  return query select v_course,v_batch;
end;
$$;
revoke all on function public.complete_private_class_setup(uuid,uuid) from public, anon, authenticated;
commit;
