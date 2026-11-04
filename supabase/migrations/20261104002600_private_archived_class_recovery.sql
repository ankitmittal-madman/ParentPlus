-- Local-only lookup for a known archived intent. Unknown never means failure.
begin;
create function public.recover_private_archived_class_setup(p_workspace_id uuid, p_intent_id uuid)
returns table (state text, intent_id uuid, course_name text, batch_name text, course_id uuid, batch_id uuid)
language plpgsql set search_path = '' as $$
declare
  v_actor uuid := auth.uid();
  v_history public.class_setup_intent_history%rowtype;
begin
  perform public.assert_private_workspace_manager(p_workspace_id);
  perform public.assert_private_class_setup_enabled();
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(v_actor::text || ':' || p_workspace_id::text, 0));
  select h.* into v_history from public.class_setup_intent_history h
    where h.id=p_intent_id and h.workspace_id=p_workspace_id and h.actor_id=v_actor;
  if not found then
    return query select 'unknown'::text,null::uuid,null::text,null::text,null::uuid,null::uuid;
  else
    if not exists (select 1 from public.batches b where b.id=v_history.completed_batch_id
        and b.workspace_id=p_workspace_id and b.course_id=v_history.completed_course_id) then
      raise exception using errcode='55000', message='Class setup recovery unavailable';
    end if;
    return query select 'archived'::text,v_history.id,v_history.course_name,v_history.batch_name,
      v_history.completed_course_id,v_history.completed_batch_id;
  end if;
end;
$$;
revoke all on function public.recover_private_archived_class_setup(uuid,uuid) from public,anon,authenticated;
commit;
