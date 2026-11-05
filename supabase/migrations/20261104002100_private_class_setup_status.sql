-- Local-only recovery status. An absent visible intent is always unknown.
begin;
create function public.private_class_setup_status(p_workspace_id uuid)
returns table (state text, intent_id uuid, course_id uuid, batch_id uuid)
language plpgsql set search_path = '' as $$
declare v_intent public.class_setup_intents%rowtype;
begin
  perform public.assert_private_workspace_manager(p_workspace_id);
  perform public.assert_private_class_setup_enabled();
  select i.* into v_intent from public.class_setup_intents i
    where i.workspace_id=p_workspace_id and i.actor_id=auth.uid() for share;
  if not found then
    return query select 'unknown'::text, null::uuid, null::uuid, null::uuid;
  elsif v_intent.completed_course_id is null then
    return query select 'pending'::text, v_intent.id, null::uuid, null::uuid;
  else
    return query select 'completed'::text, v_intent.id, v_intent.completed_course_id, v_intent.completed_batch_id;
  end if;
end;
$$;
revoke all on function public.private_class_setup_status(uuid) from public, anon, authenticated;
commit;
