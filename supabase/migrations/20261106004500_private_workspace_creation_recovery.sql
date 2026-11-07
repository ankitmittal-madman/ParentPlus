-- LOCAL DRAFT: private status only; an unknown result does not prove absence.
begin;

create function public.workspace_creation_recovery_status(p_request_id uuid)
returns table(status text, workspace_id uuid)
language plpgsql security definer set search_path = '' as $$
declare
  v_actor uuid := auth.uid();
  v_enabled boolean;
  v_receipt record;
begin
  if v_actor is null then raise exception 'Authentication required'; end if;
  if p_request_id is null then raise exception 'Request ID required'; end if;
  select c.enabled into v_enabled from public.workspace_creation_controls c where c.id=true for share;
  if not found or not v_enabled then
    raise exception using errcode='42501', message='Workspace creation unavailable';
  end if;
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(
    'parentplus:workspace-key:' || v_actor::text || ':' || p_request_id::text, 0));
  select r.workspace_id,r.original_name,r.original_type into v_receipt
    from public.workspace_creation_receipts r
    where r.actor_id=v_actor and r.request_key=p_request_id;
  if not found or v_receipt.original_name is null or v_receipt.original_type is null
     or v_receipt.original_type not in ('independent','academy')
     or v_receipt.original_name <> pg_catalog.btrim(v_receipt.original_name)
     or pg_catalog.length(v_receipt.original_name) < 2
     or pg_catalog.length(v_receipt.original_name) > 120 then
    return query select 'unknown'::text, null::uuid;
    return;
  end if;
  perform 1 from public.workspaces w where w.id=v_receipt.workspace_id
    and w.created_by=v_actor and w.creation_request_id=p_request_id and w.status='active' for share;
  if not found then
    return query select 'unknown'::text, null::uuid;
    return;
  end if;
  perform 1 from public.workspace_memberships m where m.workspace_id=v_receipt.workspace_id
    and m.user_id=v_actor and m.status='active' for share;
  if not found then
    return query select 'unknown'::text, null::uuid;
    return;
  end if;
  -- Workspace and membership are locked before the receipt, matching the
  -- workspace-first lifecycle order. Recheck the initial receipt after waits.
  perform 1 from public.workspace_creation_receipts r
    where r.actor_id=v_actor and r.request_key=p_request_id and r.workspace_id=v_receipt.workspace_id
      and r.original_name is not null and r.original_type in ('independent','academy')
      and r.original_name=pg_catalog.btrim(r.original_name)
      and pg_catalog.length(r.original_name) between 2 and 120 for share;
  if not found then
    return query select 'unknown'::text, null::uuid;
    return;
  end if;
  return query select 'known'::text, v_receipt.workspace_id::uuid;
end;
$$;
revoke all on function public.workspace_creation_recovery_status(uuid) from public, anon, authenticated;
commit;
