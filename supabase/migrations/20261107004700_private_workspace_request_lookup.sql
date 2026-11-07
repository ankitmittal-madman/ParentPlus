-- LOCAL DRAFT: a candidate key is not proof of the intended submission.
begin;

create function public.workspace_creation_key_for_workspace(p_workspace_id uuid)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  v_actor uuid := auth.uid();
  v_enabled boolean;
  v_key uuid;
  v_outcome record;
begin
  if v_actor is null then raise exception 'Authentication required'; end if;
  if p_workspace_id is null then raise exception 'Workspace ID required'; end if;
  if pg_catalog.current_setting('transaction_isolation') <> 'read committed' then
    raise exception using errcode='0A000', message='Workspace recovery isolation unsupported';
  end if;
  select c.enabled into v_enabled from public.workspace_creation_controls c where c.id=true for share;
  if not found or not v_enabled then
    raise exception using errcode='42501', message='Workspace creation unavailable';
  end if;
  -- This read does not establish access. The exact-key status operation takes
  -- the request lock and rechecks workspace, membership and receipt before return.
  select w.creation_request_id into v_key from public.workspaces w
    where w.id=p_workspace_id and w.created_by=v_actor and w.status='active';
  if not found then return pg_catalog.jsonb_build_object('status','unknown'); end if;
  select * into v_outcome from public.workspace_creation_recovery_status(v_key);
  if not found or v_outcome.status is distinct from 'known' or v_outcome.workspace_id is distinct from p_workspace_id then
    return pg_catalog.jsonb_build_object('status','unknown');
  end if;
  return pg_catalog.jsonb_build_object('status','known','request_key',v_key,'workspace_id',p_workspace_id);
end;
$$;
revoke all on function public.workspace_creation_key_for_workspace(uuid) from public, anon, authenticated;
commit;
