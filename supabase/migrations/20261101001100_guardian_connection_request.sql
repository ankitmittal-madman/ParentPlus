-- ParentPlus M2: Guardian-initiated connection request
-- DRAFT ONLY. Requires security, lifecycle and concurrency tests.

create or replace function public.request_workspace_connection(
  p_workspace_id uuid,
  p_child_id uuid,
  p_request_id uuid
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_user_id uuid;
  v_request_id uuid;
  v_existing record;
  v_expired_id uuid;
begin
  v_user_id := auth.uid();

  if v_user_id is null then
    raise exception 'Authentication required';
  end if;

  if p_workspace_id is null
     or p_child_id is null
     or p_request_id is null then
    raise exception 'Required identifiers missing';
  end if;

  -- Serialize requests for the same guardian-child-workspace.
  perform pg_catalog.pg_advisory_xact_lock(
    pg_catalog.hashtextextended(
      v_user_id::text || ':' ||
      p_child_id::text || ':' ||
      p_workspace_id::text,
      0
    )
  );

  -- Lock and validate guardian eligibility.
  perform 1
  from public.guardianships
  where child_id = p_child_id
    and guardian_user_id = v_user_id
    and status in ('provisional', 'active')
  for share;

  if not found then
    raise exception 'Guardian not authorized';
  end if;

  -- Lock and validate destination workspace.
  perform 1
  from public.workspaces
  where id = p_workspace_id
    and status = 'active'
  for share;

  if not found then
    raise exception 'Workspace unavailable';
  end if;

  -- Same idempotency key must represent the same operation.
  select *
  into v_existing
  from public.connection_requests
  where initiated_by = v_user_id
    and creation_request_id = p_request_id;

  if found then
    if v_existing.workspace_id <> p_workspace_id
       or v_existing.child_id <> p_child_id
       or v_existing.initiation_type <> 'guardian' then
      raise exception 'Request ID reused with different details';
    end if;

    return v_existing.id;
  end if;

  -- Expire stale pending requests and audit each transition.
  for v_expired_id in
    with expired_requests as (
      update public.connection_requests
      set status = 'expired',
          updated_at = now()
      where workspace_id = p_workspace_id
        and child_id = p_child_id
        and guardian_user_id = v_user_id
        and initiation_type = 'guardian'
        and status = 'pending'
        and expires_at <= now()
      returning id
    )
    select id from expired_requests
  loop
    insert into public.connection_events (
      connection_request_id, actor_user_id, event_type
    )
    values (v_expired_id, v_user_id, 'expired');
  end loop;

  -- Reuse an existing valid pending request.
  select id into v_request_id
  from public.connection_requests
  where workspace_id = p_workspace_id
    and child_id = p_child_id
    and guardian_user_id = v_user_id
    and initiation_type = 'guardian'
    and status = 'pending'
    and expires_at > now();

  if v_request_id is not null then
    return v_request_id;
  end if;

  insert into public.connection_requests (
    workspace_id,
    child_id,
    guardian_user_id,
    initiated_by,
    initiation_type,
    status,
    expires_at,
    creation_request_id
  )
  values (
    p_workspace_id,
    p_child_id,
    v_user_id,
    v_user_id,
    'guardian',
    'pending',
    now() + interval '7 days',
    p_request_id
  )
  returning id into v_request_id;

  insert into public.connection_events (
    connection_request_id, actor_user_id, event_type
  )
  values (v_request_id, v_user_id, 'requested');

  return v_request_id;
end;
$$;

revoke all on function public.request_workspace_connection(uuid,uuid,uuid)
  from public;
revoke all on function public.request_workspace_connection(uuid,uuid,uuid)
  from anon;
grant execute on function public.request_workspace_connection(uuid,uuid,uuid)
  to authenticated;

-- SECURITY REVIEW REQUIRED:
-- Confirm guardian and workspace state under concurrent changes.
-- Test request ID conflicts and expired request replacement.
-- Review function ownership and effective privileges.
-- Add auditable request and expiry events.
-- Finalize expiry duration and rate limits.
-- Ensure no relationship or enrollment is created.
