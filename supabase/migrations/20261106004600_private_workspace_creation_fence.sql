-- LOCAL DRAFT: exact-key fences are retained; lifecycle and hosted rollout remain unreviewed.
begin;
do $$ begin
  update public.workspace_creation_controls set enabled=false where id=true;
  if not found then raise exception using errcode='42501', message='Workspace creation unavailable'; end if;
end $$;
lock table public.workspaces in share row exclusive mode;
lock table public.workspace_creation_receipts in share row exclusive mode;

create table public.workspace_creation_fences (
  actor_id uuid not null,
  request_key uuid not null,
  primary key (actor_id,request_key)
);
alter table public.workspace_creation_fences enable row level security;
revoke all on public.workspace_creation_fences from public, anon, authenticated;

-- Lock before an INSERT reaches its unique index, including legacy callers.
-- This BEFORE trigger must not write receipts: ON CONFLICT may skip the row.
create function public.guard_fenced_workspace_creation()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  -- Advisory locks do not refresh a REPEATABLE READ/SERIALIZABLE snapshot.
  if pg_catalog.current_setting('transaction_isolation') <> 'read committed' then
    raise exception using errcode='0A000', message='Workspace creation isolation unsupported';
  end if;
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(
    'parentplus:workspace-key:' || new.created_by::text || ':' || new.creation_request_id::text,0));
  if exists (select 1 from public.workspace_creation_fences f
             where f.actor_id=new.created_by and f.request_key=new.creation_request_id) then
    raise exception using errcode='42501', message='Workspace creation request fenced';
  end if;
  return new;
end;
$$;
revoke all on function public.guard_fenced_workspace_creation() from public, anon, authenticated;
create trigger guard_fenced_workspace_creation before insert on public.workspaces
  for each row execute function public.guard_fenced_workspace_creation();

create function public.fence_workspace_creation(p_request_id uuid)
returns text language plpgsql security definer set search_path = '' as $$
declare
  v_actor uuid := auth.uid();
  v_enabled boolean;
begin
  if v_actor is null then raise exception 'Authentication required'; end if;
  if p_request_id is null then raise exception 'Request ID required'; end if;
  if pg_catalog.current_setting('transaction_isolation') <> 'read committed' then
    raise exception using errcode='0A000', message='Workspace creation isolation unsupported';
  end if;
  select c.enabled into v_enabled from public.workspace_creation_controls c where c.id=true for share;
  if not found or not v_enabled then
    raise exception using errcode='42501', message='Workspace creation unavailable';
  end if;
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(
    'parentplus:workspace-key:' || v_actor::text || ':' || p_request_id::text,0));
  -- Neither missing receipts nor an inaccessible prior outcome proves absence.
  if exists (select 1 from public.workspace_creation_receipts r where r.actor_id=v_actor and r.request_key=p_request_id)
     or exists (select 1 from public.workspaces w where w.created_by=v_actor and w.creation_request_id=p_request_id) then
    return 'unknown';
  end if;
  insert into public.workspace_creation_fences(actor_id,request_key) values (v_actor,p_request_id)
    on conflict (actor_id,request_key) do nothing;
  return 'fenced';
end;
$$;
revoke all on function public.fence_workspace_creation(uuid) from public, anon, authenticated;

create or replace function public.create_workspace_unguarded_private(p_name text,p_type text,p_request_id uuid)
returns uuid language plpgsql security definer set search_path = '' as $$
declare
  v_user_id uuid := auth.uid();
  v_name text := pg_catalog.btrim(p_name);
  v_workspace_id uuid;
  v_receipt record;
begin
  if v_user_id is null then raise exception 'Authentication required'; end if;
  if v_name is null or pg_catalog.length(v_name) < 2 or pg_catalog.length(v_name) > 120 then
    raise exception 'Invalid workspace name';
  end if;
  if p_type is null or p_type not in ('independent','academy') then raise exception 'Invalid workspace type'; end if;
  if p_request_id is null then raise exception 'Request ID required'; end if;

  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(
    'parentplus:workspace-key:' || v_user_id::text || ':' || p_request_id::text, 0));
  if exists (select 1 from public.workspace_creation_fences f where f.actor_id=v_user_id and f.request_key=p_request_id) then
    raise exception using errcode='42501', message='Workspace creation request fenced';
  end if;
  select * into v_receipt from public.workspace_creation_receipts
  where actor_id=v_user_id and request_key=p_request_id;
  if found then
    perform 1 from public.workspaces where id=v_receipt.workspace_id
      and created_by=v_user_id and creation_request_id=p_request_id and status='active' for share;
    if not found then raise exception using errcode='42501', message='Workspace unavailable'; end if;
    perform 1 from public.workspace_memberships
      where workspace_id=v_receipt.workspace_id and user_id=v_user_id and status='active' for share;
    if not found then raise exception using errcode='42501', message='Workspace unavailable'; end if;
    if v_receipt.original_name is null or v_receipt.original_type is null then
      raise exception using errcode='42501', message='Workspace creation recovery unavailable';
    end if;
    if v_receipt.original_name <> v_name or v_receipt.original_type <> p_type then
      raise exception 'Request ID reused with different workspace details';
    end if;
    return v_receipt.workspace_id;
  end if;

  -- A missing receipt for an existing row must never be guessed or overwritten.
  if exists (select 1 from public.workspaces where created_by=v_user_id and creation_request_id=p_request_id) then
    raise exception using errcode='42501', message='Workspace creation recovery unavailable';
  end if;
  insert into public.workspaces(name,type,created_by,creation_request_id)
    values (v_name,p_type,v_user_id,p_request_id) returning id into v_workspace_id;
  insert into public.workspace_memberships(workspace_id,user_id,role,status)
    values (v_workspace_id,v_user_id,'owner','active');
  update public.workspace_creation_receipts set original_name=v_name, original_type=p_type
    where actor_id=v_user_id and request_key=p_request_id and workspace_id=v_workspace_id
      and original_name is null and original_type is null;
  if not found then
    raise exception using errcode='42501', message='Workspace creation recovery unavailable';
  end if;
  return v_workspace_id;
end;
$$;
revoke all on function public.create_workspace_unguarded_private(text,text,uuid) from public, anon, authenticated;
commit;
