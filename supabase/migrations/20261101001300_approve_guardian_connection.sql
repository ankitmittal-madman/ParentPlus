-- ParentPlus M3: Independent guardian connection approval.
-- LOCAL DRAFT ONLY. Do not deploy before authorization and concurrency tests.
-- Guardian-initiated requests require independent workspace approval.

create or replace function public.approve_guardian_connection(
  p_connection_request_id uuid
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_actor uuid;
  v_request record;
  v_relationship_id uuid;
  v_relationship_status text;
begin
  v_actor := auth.uid();

  if v_actor is null then
    raise exception 'Authentication required';
  end if;

  if p_connection_request_id is null then
    raise exception 'Connection request ID required';
  end if;

  -- Serialize approval attempts for the same connection request.
  perform pg_catalog.pg_advisory_xact_lock(
    pg_catalog.hashtextextended(
      p_connection_request_id::text, 0
    )
  );

  -- Lock the request to prevent concurrent status changes.
  select *
  into v_request
  from public.connection_requests
  where id = p_connection_request_id
  for update;

  if not found then
    raise exception 'Connection request unavailable';
  end if;

  if v_request.initiation_type <> 'guardian' then
    raise exception 'Unsupported connection initiation type';
  end if;

  if v_request.initiated_by = v_actor then
    raise exception 'Self-approval is not permitted';
  end if;

  if v_request.status not in ('pending', 'approved') then
    raise exception 'Connection request not approvable';
  end if;

  if v_request.status = 'pending'
     and v_request.expires_at <= pg_catalog.clock_timestamp() then
    raise exception 'Connection request expired';
  end if;

  if v_request.status = 'approved'
     and v_request.confirmed_by is distinct from v_actor then
    raise exception 'Approval belongs to another user';
  end if;

  -- Validate active workspace and lock against suspension.
  perform 1
  from public.workspaces
  where id = v_request.workspace_id
    and status = 'active'
  for share;

  if not found then
    raise exception 'Workspace unavailable';
  end if;

  -- Only active owner/admin may approve.
  perform 1
  from public.workspace_memberships
  where workspace_id = v_request.workspace_id
    and user_id = v_actor
    and role in ('owner', 'admin')
    and status = 'active'
  for share;

  if not found then
    raise exception 'Workspace approval not authorized';
  end if;

  -- Guardian must remain eligible at approval time.
  perform 1
  from public.guardianships
  where child_id = v_request.child_id
    and guardian_user_id = v_request.guardian_user_id
    and status in ('provisional', 'active')
  for share;

  if not found then
    raise exception 'Guardian no longer eligible';
  end if;

  -- Prevent concurrent activation of the same relationship.
  perform pg_catalog.pg_advisory_xact_lock(
    pg_catalog.hashtextextended(
      v_request.workspace_id::text || ':' ||
      v_request.child_id::text,
      0
    )
  );

  select id, status
  into v_relationship_id, v_relationship_status
  from public.workspace_children
  where workspace_id = v_request.workspace_id
    and child_id = v_request.child_id
  for update;

  if found then
    if v_relationship_status <> 'active' then
      raise exception 'Existing relationship cannot be reactivated';
    end if;
  elsif v_request.status = 'approved' then
    raise exception 'Approved relationship missing';
  else
    insert into public.workspace_children (
      workspace_id, child_id, status
    )
    values (
      v_request.workspace_id, v_request.child_id, 'active'
    )
    returning id into v_relationship_id;
  end if;

  -- An authorized retry returns the existing active relationship.
  -- It must not modify approval metadata or write another audit event.
  if v_request.status = 'approved' then
    return v_relationship_id;
  end if;

  update public.connection_requests
  set status = 'approved',
      confirmed_by = v_actor,
      confirmed_at = now(),
      updated_at = now()
  where id = p_connection_request_id;

  insert into public.connection_events (
    connection_request_id,
    workspace_child_id,
    actor_user_id,
    event_type
  )
  values (
    p_connection_request_id,
    v_relationship_id,
    v_actor,
    'approved'
  );

  return v_relationship_id;
end;
$$;

revoke all on function public.approve_guardian_connection(uuid)
  from public;

revoke all on function public.approve_guardian_connection(uuid)
  from anon;

grant execute on function public.approve_guardian_connection(uuid)
  to authenticated;
