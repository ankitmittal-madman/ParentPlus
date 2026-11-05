-- Local-only keyset discovery. UUID order is not chronological; pages are snapshots.
begin;
create index class_setup_intent_history_actor_workspace_id_idx
  on public.class_setup_intent_history (actor_id,workspace_id,id);
create function public.list_private_archived_class_setups(p_workspace_id uuid, p_after_id uuid, p_limit integer)
returns table (intent_id uuid, course_name text, batch_name text, course_id uuid, batch_id uuid)
language plpgsql set search_path = '' as $$
declare
  v_actor uuid := auth.uid();
  v_history public.class_setup_intent_history%rowtype;
begin
  perform public.assert_private_workspace_manager(p_workspace_id);
  perform public.assert_private_class_setup_enabled();
  if p_limit is null or p_limit < 1 or p_limit > 50 then
    raise exception using errcode='22023', message='Invalid page size';
  end if;
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(v_actor::text || ':' || p_workspace_id::text, 0));
  for v_history in
    select h.* from public.class_setup_intent_history h
      where h.workspace_id=p_workspace_id and h.actor_id=v_actor and (p_after_id is null or h.id > p_after_id)
      order by h.id limit p_limit
  loop
    if not exists (select 1 from public.batches b where b.id=v_history.completed_batch_id
        and b.workspace_id=p_workspace_id and b.course_id=v_history.completed_course_id) then
      raise exception using errcode='55000', message='Class setup recovery unavailable';
    end if;
    return query select v_history.id,v_history.course_name,v_history.batch_name,v_history.completed_course_id,v_history.completed_batch_id;
  end loop;
end;
$$;
revoke all on function public.list_private_archived_class_setups(uuid,uuid,integer) from public,anon,authenticated;
commit;
