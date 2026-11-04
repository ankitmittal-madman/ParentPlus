-- Local draft: validate completed batch/course relation during current recovery.
begin;
create or replace function public.recover_private_current_class_setup(p_workspace_id uuid)
returns table (state text, intent_id uuid, prior_intent_id uuid, request_id uuid,
               course_name text, batch_name text, course_id uuid, batch_id uuid, acknowledged boolean)
language plpgsql set search_path = '' as $$
declare
  v_actor uuid := auth.uid();
  v_intent public.class_setup_intents%rowtype;
  v_request public.class_setup_next_requests%rowtype;
begin
  perform public.assert_private_workspace_manager(p_workspace_id);
  perform public.assert_private_class_setup_enabled();
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(v_actor::text || ':' || p_workspace_id::text, 0));
  select i.* into v_intent from public.class_setup_intents i
    where i.workspace_id=p_workspace_id and i.actor_id=v_actor for share;
  if not found then
    return query select 'unknown'::text,null::uuid,null::uuid,null::uuid,null::text,null::text,null::uuid,null::uuid,null::boolean;
    return;
  end if;
  if v_intent.completed_course_id is not null and not exists (
    select 1 from public.batches b where b.id=v_intent.completed_batch_id
      and b.workspace_id=p_workspace_id and b.course_id=v_intent.completed_course_id
  ) then
    raise exception using errcode='55000', message='Class setup recovery unavailable';
  end if;
  select r.* into v_request from public.class_setup_next_requests r
    where r.actor_id=v_actor and r.workspace_id=p_workspace_id and r.next_intent_id=v_intent.id;
  if found then
    if v_request.course_name is distinct from v_intent.course_name
       or v_request.batch_name is distinct from v_intent.batch_name
       or not exists (select 1 from public.class_setup_intent_history h
         where h.id=v_request.prior_intent_id and h.actor_id=v_actor and h.workspace_id=p_workspace_id) then
      raise exception using errcode='55000', message='Class setup recovery unavailable';
    end if;
  elsif exists (select 1 from public.class_setup_intent_history h where h.actor_id=v_actor and h.workspace_id=p_workspace_id) then
    raise exception using errcode='55000', message='Class setup recovery unavailable';
  end if;
  return query select case when v_intent.completed_course_id is null then 'pending'::text else 'completed'::text end,
    v_intent.id,v_request.prior_intent_id,v_request.request_id,v_intent.course_name,v_intent.batch_name,
    v_intent.completed_course_id,v_intent.completed_batch_id,v_intent.acknowledged;
end;
$$;
revoke all on function public.recover_private_current_class_setup(uuid) from public,anon,authenticated;
commit;
