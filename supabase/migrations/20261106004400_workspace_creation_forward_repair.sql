-- LOCAL DRAFT: repairs surviving workspace receipts; deleted keys cannot be reconstructed.
begin;
-- Disable first and wait for guarded callers before acquiring workspace locks.
do $$ begin
  update public.workspace_creation_controls set enabled=false where id=true;
  if not found then raise exception using errcode='42501', message='Workspace creation unavailable'; end if;
end $$;
lock table public.workspaces in share row exclusive mode;
lock table public.workspace_creation_receipts in share row exclusive mode;

-- A live workspace may not adopt another workspace's retained request key.
do $$ begin
  if exists (
    select 1 from public.workspaces w join public.workspace_creation_receipts r
      on r.actor_id=w.created_by and r.request_key=w.creation_request_id
    where r.workspace_id <> w.id
  ) then
    raise exception using errcode='42501', message='Workspace creation recovery unavailable';
  end if;
end $$;

create or replace function public.record_workspace_creation_tombstone()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  begin
    insert into public.workspace_creation_receipts(actor_id,request_key,workspace_id,original_name,original_type)
      values (new.created_by,new.creation_request_id,new.id,null,null);
  exception when unique_violation then
    raise exception using errcode='42501', message='Workspace creation recovery unavailable';
  end;
  return new;
end;
$$;
revoke all on function public.record_workspace_creation_tombstone() from public, anon, authenticated;
drop trigger if exists workspace_creation_tombstone on public.workspaces;
create trigger workspace_creation_tombstone after insert on public.workspaces
  for each row execute function public.record_workspace_creation_tombstone();

-- Only surviving records can be reconciled; never infer original payloads.
insert into public.workspace_creation_receipts(actor_id,request_key,workspace_id,original_name,original_type)
select w.created_by,w.creation_request_id,w.id,null,null from public.workspaces w
where not exists (select 1 from public.workspace_creation_receipts r
                  where r.actor_id=w.created_by and r.request_key=w.creation_request_id);

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
