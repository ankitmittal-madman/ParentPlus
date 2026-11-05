-- Local-only acknowledgement: deliberately retains the slot and receipt.
begin;
alter table public.class_setup_intents add column acknowledged boolean not null default false;
alter table public.class_setup_intents add constraint class_setup_ack_requires_completion
  check (not acknowledged or completed_course_id is not null);

create function public.acknowledge_private_class_setup(p_workspace_id uuid, p_intent_id uuid)
returns boolean language plpgsql set search_path = '' as $$
declare v_intent public.class_setup_intents%rowtype;
begin
  perform public.assert_private_workspace_manager(p_workspace_id);
  perform public.assert_private_class_setup_enabled();
  select i.* into v_intent from public.class_setup_intents i
    where i.id=p_intent_id and i.workspace_id=p_workspace_id and i.actor_id=auth.uid() for update;
  if not found then
    raise exception using errcode='42501', message='Class setup unavailable';
  end if;
  if v_intent.completed_course_id is null then
    raise exception using errcode='55000', message='Class setup is not complete';
  end if;
  if not v_intent.acknowledged then
    update public.class_setup_intents i set acknowledged=true where i.id=v_intent.id;
  end if;
  return true;
end;
$$;
revoke all on function public.acknowledge_private_class_setup(uuid,uuid) from public, anon, authenticated;
commit;
