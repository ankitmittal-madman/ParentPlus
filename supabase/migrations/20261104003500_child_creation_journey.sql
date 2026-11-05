-- Local, default-off durable journey for one current child creation per actor.
-- The legacy authenticated entrypoint is revoked atomically with these wrappers.
begin;
create table public.child_creation_intents (
  actor_id uuid primary key references auth.users(id),
  id uuid not null unique default gen_random_uuid(),
  prior_id uuid,
  request_id uuid not null,
  child_id uuid not null references public.children(id),
  display_name text not null,
  acknowledged boolean not null default false,
  check (prior_id is null or prior_id <> id)
);
alter table public.child_creation_intents enable row level security;
revoke all on public.child_creation_intents from public, anon, authenticated;

create function public.lock_private_child_creation_actor()
returns uuid language plpgsql set search_path = '' as $$
declare v_actor uuid := auth.uid(); v_enabled boolean;
begin
  if v_actor is null then
    raise exception using errcode='42501', message='Child creation unavailable';
  end if;
  select enabled into v_enabled from public.child_creation_controls where id=true for share;
  if not found or not v_enabled then
    raise exception using errcode='42501', message='Child creation unavailable';
  end if;
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('parent-child-creation:' || v_actor::text,0));
  return v_actor;
end;
$$;
revoke all on function public.lock_private_child_creation_actor() from public,anon,authenticated;

create function public.assert_private_child_creation_access(p_actor uuid,p_child uuid)
returns void language plpgsql set search_path = '' as $$
begin
  perform 1 from public.children c join public.guardianships g on g.child_id=c.id
    where c.id=p_child and c.created_by=p_actor and g.guardian_user_id=p_actor
      and g.status in ('provisional','active') for share of c,g;
  if not found then
    raise exception using errcode='42501', message='Child creation unavailable';
  end if;
end;
$$;
revoke all on function public.assert_private_child_creation_access(uuid,uuid) from public,anon,authenticated;

create function public.app_current_child_creation()
returns table (intent_id uuid,child_id uuid,display_name text,acknowledged boolean,prior_intent_id uuid,request_id uuid)
language plpgsql security definer set search_path = '' as $$
declare v_actor uuid; v_intent public.child_creation_intents%rowtype;
begin
  v_actor := public.lock_private_child_creation_actor();
  select i.* into v_intent from public.child_creation_intents i where i.actor_id=v_actor for update;
  if not found then return; end if;
  perform public.assert_private_child_creation_access(v_actor,v_intent.child_id);
  return query select v_intent.id,v_intent.child_id,v_intent.display_name,v_intent.acknowledged,v_intent.prior_id,v_intent.request_id;
end;
$$;

create function public.app_begin_child_creation(p_display_name text,p_prior_intent_id uuid,p_request_id uuid)
returns table (intent_id uuid,child_id uuid,display_name text,acknowledged boolean,prior_intent_id uuid,request_id uuid,disposition text)
language plpgsql security definer set search_path = '' as $$
declare
  v_actor uuid; v_intent public.child_creation_intents%rowtype;
  v_name text := pg_catalog.btrim(p_display_name);
  v_child uuid; v_request uuid; v_next uuid;
  v_has_intent boolean;
begin
  v_actor := public.lock_private_child_creation_actor();
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

create function public.app_ack_child_creation(p_intent_id uuid)
returns boolean language plpgsql security definer set search_path = '' as $$
declare v_actor uuid; v_intent public.child_creation_intents%rowtype;
begin
  v_actor := public.lock_private_child_creation_actor();
  select i.* into v_intent from public.child_creation_intents i where i.actor_id=v_actor for update;
  if not found or v_intent.id is distinct from p_intent_id then
    raise exception using errcode='42501', message='Child creation unavailable';
  end if;
  perform public.assert_private_child_creation_access(v_actor,v_intent.child_id);
  update public.child_creation_intents i set acknowledged=true where i.actor_id=v_actor;
  return true;
end;
$$;
revoke all on function public.app_current_child_creation(),public.app_begin_child_creation(text,uuid,uuid),public.app_ack_child_creation(uuid) from public,anon,authenticated;
grant execute on function public.app_current_child_creation(),public.app_begin_child_creation(text,uuid,uuid),public.app_ack_child_creation(uuid) to authenticated;
revoke all on function public.create_child(text,uuid) from public,anon,authenticated;
commit;
