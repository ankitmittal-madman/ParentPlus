-- Local draft: archive only superseded, actor-scoped request references.
begin;
create table public.child_creation_history (
  intent_id uuid primary key,
  actor_id uuid not null references auth.users(id) on delete cascade,
  request_id uuid not null,
  prior_intent_id uuid,
  child_id uuid not null references public.children(id) on delete cascade,
  unique nulls not distinct (actor_id, prior_intent_id, request_id)
);
alter table public.child_creation_history enable row level security;
revoke all on public.child_creation_history from public, anon, authenticated;

create function public.archive_private_child_creation_intent()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  if old.id is distinct from new.id then
    insert into public.child_creation_history (intent_id, actor_id, request_id, prior_intent_id, child_id)
      values (old.id, old.actor_id, old.request_id, old.prior_id, old.child_id);
  end if;
  return new;
end;
$$;
revoke all on function public.archive_private_child_creation_intent() from public, anon, authenticated;
create trigger archive_child_creation_intent before update on public.child_creation_intents
  for each row execute function public.archive_private_child_creation_intent();

create function public.app_historical_child_creation(p_prior_intent_id uuid, p_request_id uuid)
returns text language plpgsql security definer set search_path = '' as $$
declare v_actor uuid; v_child uuid;
begin
  v_actor := public.lock_private_child_creation_actor();
  if p_request_id is null then
    raise exception using errcode='22023', message='Child creation unavailable';
  end if;
  select h.child_id into v_child from public.child_creation_history h
    where h.actor_id=v_actor and h.request_id=p_request_id
      and h.prior_intent_id is not distinct from p_prior_intent_id;
  if not found then return 'unknown'; end if;
  perform public.assert_private_child_creation_access(v_actor,v_child);
  return 'found';
end;
$$;
revoke all on function public.app_historical_child_creation(uuid,uuid) from public, anon, authenticated;
grant execute on function public.app_historical_child_creation(uuid,uuid) to authenticated;
commit;
