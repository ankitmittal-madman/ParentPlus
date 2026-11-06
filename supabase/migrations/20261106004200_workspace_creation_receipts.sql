-- LOCAL DRAFT ONLY: receipt retention, legacy recovery and hosted privileges require review.
begin;
create table public.workspace_creation_receipts (
  actor_id uuid not null,
  request_key uuid not null,
  workspace_id uuid not null,
  original_name text,
  original_type text,
  primary key (actor_id, request_key),
  check ((original_name is null and original_type is null) or
         (original_name is not null and original_type is not null and original_type in ('independent', 'academy')))
);
alter table public.workspace_creation_receipts enable row level security;
revoke all on public.workspace_creation_receipts from public, anon, authenticated;
-- Drain writers that inserted before cutover and prevent new inserts until
-- the trigger, backfill and replacement implementation commit together.
lock table public.workspaces in share row exclusive mode;

create function public.record_workspace_creation_tombstone()
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
create trigger workspace_creation_tombstone after insert on public.workspaces
  for each row execute function public.record_workspace_creation_tombstone();
-- A current name is not evidence of the original name. Preserve unknown legacy keys.
insert into public.workspace_creation_receipts(actor_id,request_key,workspace_id,original_name,original_type)
select created_by,creation_request_id,id,null,null from public.workspaces;

create or replace function public.create_workspace(p_name text,p_type text,p_request_id uuid)
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
revoke all on function public.create_workspace(text,text,uuid) from public,anon,authenticated;
grant execute on function public.create_workspace(text,text,uuid) to authenticated;
commit;
