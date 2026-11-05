-- Local-only recovery fence. No hosted deployment is implied.
begin;
create table public.child_creation_fences (
  actor_id uuid not null references auth.users(id),
  request_id uuid not null,
  prior_intent_id uuid,
  primary key (actor_id, request_id)
);
alter table public.child_creation_fences enable row level security;
revoke all on public.child_creation_fences from public, anon, authenticated;

create or replace function public.app_begin_child_creation(p_display_name text,p_prior_intent_id uuid,p_request_id uuid)
returns table (intent_id uuid,child_id uuid,display_name text,acknowledged boolean,prior_intent_id uuid,request_id uuid,disposition text)
language plpgsql security definer set search_path = '' as $$
declare
  v_actor uuid; v_intent public.child_creation_intents%rowtype;
  v_name text := pg_catalog.btrim(p_display_name);
  v_child uuid; v_request uuid; v_next uuid;
  v_has_intent boolean;
begin
  v_actor := public.lock_private_child_creation_actor();
  if exists (select 1 from public.child_creation_fences f where f.actor_id=v_actor and f.request_id=p_request_id) then
    raise exception using errcode='55000', message='Child creation unavailable';
  end if;
  if p_request_id is null or v_name is null or pg_catalog.length(v_name) not between 1 and 120 then
    raise exception using errcode='22023', message='Invalid child profile details';
  end if;
  select i.* into v_intent from public.child_creation_intents i where i.actor_id=v_actor for update;
  v_has_intent := found;
  if v_has_intent then
    perform public.assert_private_child_creation_access(v_actor,v_intent.child_id);
    if p_prior_intent_id is null then
      if v_intent.prior_id is not null then
        raise exception using errcode='55000', message='Child creation unavailable';
      end if;
      if v_intent.request_id is distinct from p_request_id or v_intent.display_name is distinct from v_name then
        raise exception using errcode='23505', message='Resolve the existing child profile first';
      end if;
      return query select v_intent.id,v_intent.child_id,v_intent.display_name,v_intent.acknowledged,v_intent.prior_id,v_intent.request_id,'existing'::text;
      return;
    elsif p_prior_intent_id = v_intent.prior_id then
      if v_intent.request_id is distinct from p_request_id or v_intent.display_name is distinct from v_name then
        raise exception using errcode='23505', message='Resolve the existing child profile first';
      end if;
      return query select v_intent.id,v_intent.child_id,v_intent.display_name,v_intent.acknowledged,v_intent.prior_id,v_intent.request_id,'existing'::text;
      return;
    elsif p_prior_intent_id <> v_intent.id or not v_intent.acknowledged or p_request_id = v_intent.request_id then
      raise exception using errcode='55000', message='Child creation unavailable';
    end if;
  elsif p_prior_intent_id is not null then
    raise exception using errcode='55000', message='Child creation unavailable';
  end if;
  -- Insert directly with an internal random request key: a collision fails closed,
  -- rather than adopting an unrelated pre-existing legacy creation receipt.
  v_request := pg_catalog.gen_random_uuid();
  insert into public.children (display_name,created_by,creation_request_id)
    values (v_name,v_actor,v_request) returning id into v_child;
  insert into public.guardianships (child_id,guardian_user_id,status,verification_level)
    values (v_child,v_actor,'provisional','self_declared');
  v_next := pg_catalog.gen_random_uuid();
  if v_has_intent then
    update public.child_creation_intents i set id=v_next,prior_id=v_intent.id,
      request_id=p_request_id,child_id=v_child,display_name=v_name,acknowledged=false where i.actor_id=v_actor;
  else
    insert into public.child_creation_intents (actor_id,id,prior_id,request_id,child_id,display_name,acknowledged)
      values (v_actor,v_next,null,p_request_id,v_child,v_name,false);
  end if;
  return query select v_next,v_child,v_name,false,p_prior_intent_id,p_request_id,'created'::text;
end;
$$;

create function public.app_fence_child_creation(p_prior_intent_id uuid, p_request_id uuid)
returns text language plpgsql security definer set search_path = '' as $$
declare
  v_actor uuid; v_intent public.child_creation_intents%rowtype;
  v_fence public.child_creation_fences%rowtype; v_has_intent boolean;
begin
  v_actor := public.lock_private_child_creation_actor();
  if p_request_id is null then
    raise exception using errcode='22023', message='Child creation unavailable';
  end if;
  select f.* into v_fence from public.child_creation_fences f
    where f.actor_id=v_actor and f.request_id=p_request_id;
  if found then
    if v_fence.prior_intent_id is distinct from p_prior_intent_id then return 'unknown'; end if;
    return 'fenced';
  end if;
  select i.* into v_intent from public.child_creation_intents i where i.actor_id=v_actor for update;
  v_has_intent := found;
  if v_has_intent then
    perform public.assert_private_child_creation_access(v_actor,v_intent.child_id);
    if v_intent.request_id=p_request_id and v_intent.prior_id is not distinct from p_prior_intent_id then
      return 'created';
    end if;
    if v_intent.request_id=p_request_id or v_intent.id is distinct from p_prior_intent_id or not v_intent.acknowledged then return 'unknown'; end if;
  elsif p_prior_intent_id is not null then
    return 'unknown';
  end if;
  insert into public.child_creation_fences (actor_id,request_id,prior_intent_id)
    values (v_actor,p_request_id,p_prior_intent_id);
  return 'fenced';
end;
$$;
revoke all on function public.app_fence_child_creation(uuid,uuid) from public,anon,authenticated;
grant execute on function public.app_fence_child_creation(uuid,uuid) to authenticated;
commit;
