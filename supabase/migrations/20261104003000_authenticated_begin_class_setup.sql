-- Local draft: distinguish a new reservation from an existing one atomically.
begin;
create function public.app_begin_class_setup(p_workspace_id uuid,p_course_name text,p_batch_name text)
returns table (disposition text,state text,intent_id uuid)
language plpgsql security definer set search_path = '' as $$
declare
  v_actor uuid := auth.uid();
  v_intent public.class_setup_intents%rowtype;
  v_existing boolean;
  v_id uuid;
begin
  perform public.assert_private_workspace_manager(p_workspace_id);
  perform public.assert_private_class_setup_enabled();
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(v_actor::text || ':' || p_workspace_id::text,0));
  select i.* into v_intent from public.class_setup_intents i
    where i.actor_id=v_actor and i.workspace_id=p_workspace_id for update;
  v_existing := found;
  v_id := public.reserve_private_class_setup(p_workspace_id,p_course_name,p_batch_name);
  if not v_existing then
    return query select 'created'::text,'pending'::text,v_id;
  else
    return query select 'existing'::text,
      case when v_intent.acknowledged then 'acknowledged'::text
           when v_intent.completed_course_id is not null then 'completed'::text
           else 'pending'::text end, v_id;
  end if;
end;
$$;
revoke all on function public.app_begin_class_setup(uuid,text,text) from public,anon,authenticated;
grant execute on function public.app_begin_class_setup(uuid,text,text) to authenticated;
-- The old wrapper does not distinguish a new request from a retry.
revoke all on function public.app_reserve_class_setup(uuid,text,text) from public,anon,authenticated;
commit;
