-- Local draft: delegates only; the private database control remains default-off.
-- Publish all wrappers and privileges atomically to avoid default PUBLIC access.
begin;
create function public.app_reserve_class_setup(p_workspace_id uuid, p_course_name text, p_batch_name text)
returns uuid language sql security definer set search_path = '' as $$
  select public.reserve_private_class_setup(p_workspace_id,p_course_name,p_batch_name)
$$;
create function public.app_complete_class_setup(p_workspace_id uuid, p_intent_id uuid)
returns table (course_id uuid,batch_id uuid) language sql security definer set search_path = '' as $$
  select * from public.complete_private_class_setup(p_workspace_id,p_intent_id)
$$;
create function public.app_acknowledge_class_setup(p_workspace_id uuid, p_intent_id uuid)
returns boolean language sql security definer set search_path = '' as $$
  select public.acknowledge_private_class_setup(p_workspace_id,p_intent_id)
$$;
create function public.app_advance_class_setup(p_workspace_id uuid,p_prior_intent_id uuid,p_request_id uuid,p_course_name text,p_batch_name text)
returns uuid language sql security definer set search_path = '' as $$
  select public.advance_private_class_setup(p_workspace_id,p_prior_intent_id,p_request_id,p_course_name,p_batch_name)
$$;
create function public.app_current_class_setup(p_workspace_id uuid)
returns table (state text,intent_id uuid,prior_intent_id uuid,request_id uuid,course_name text,batch_name text,course_id uuid,batch_id uuid,acknowledged boolean)
language sql security definer set search_path = '' as $$
  select * from public.recover_private_current_class_setup(p_workspace_id)
$$;
create function public.app_archived_class_setup(p_workspace_id uuid,p_intent_id uuid)
returns table (state text,intent_id uuid,course_name text,batch_name text,course_id uuid,batch_id uuid)
language sql security definer set search_path = '' as $$
  select * from public.recover_private_archived_class_setup(p_workspace_id,p_intent_id)
$$;
create function public.app_list_archived_class_setups(p_workspace_id uuid,p_after_id uuid,p_limit integer)
returns table (intent_id uuid,course_name text,batch_name text,course_id uuid,batch_id uuid)
language sql security definer set search_path = '' as $$
  select * from public.list_private_archived_class_setups(p_workspace_id,p_after_id,p_limit)
$$;
revoke all on function public.app_reserve_class_setup(uuid,text,text),
 public.app_complete_class_setup(uuid,uuid), public.app_acknowledge_class_setup(uuid,uuid),
 public.app_advance_class_setup(uuid,uuid,uuid,text,text), public.app_current_class_setup(uuid),
 public.app_archived_class_setup(uuid,uuid), public.app_list_archived_class_setups(uuid,uuid,integer)
 from public,anon,authenticated;
grant execute on function public.app_reserve_class_setup(uuid,text,text),
 public.app_complete_class_setup(uuid,uuid), public.app_acknowledge_class_setup(uuid,uuid),
 public.app_advance_class_setup(uuid,uuid,uuid,text,text), public.app_current_class_setup(uuid),
 public.app_archived_class_setup(uuid,uuid), public.app_list_archived_class_setups(uuid,uuid,integer)
 to authenticated;
commit;
