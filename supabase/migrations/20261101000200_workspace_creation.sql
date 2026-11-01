-- ParentPlus M2: Idempotent workspace creation
-- DRAFT ONLY. Do not deploy before security and privilege review.

create or replace function public.create_workspace(
  p_name text,
  p_type text,
  p_request_id uuid
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_user_id uuid;
  v_workspace_id uuid;
  v_name text;
  v_existing_name text;
  v_existing_type text;
begin
  v_user_id := auth.uid();
  v_name := trim(p_name);

  if v_user_id is null then
    raise exception 'Authentication required';
  end if;

  if p_name is null or length(v_name) < 2
     or length(v_name) > 120 then
    raise exception 'Invalid workspace name';
  end if;

  if p_type is null or p_type not in ('independent', 'academy') then
    raise exception 'Invalid workspace type';
  end if;

  if p_request_id is null then
    raise exception 'Request ID required';
  end if;

  insert into public.workspaces (
    name, type, created_by, creation_request_id
  )
  values (
    v_name, p_type, v_user_id, p_request_id
  )
  on conflict (created_by, creation_request_id)
  do nothing
  returning id into v_workspace_id;

  if v_workspace_id is null then
    select id, name, type
      into v_workspace_id, v_existing_name, v_existing_type
    from public.workspaces
    where created_by = v_user_id
      and creation_request_id = p_request_id;

    if v_workspace_id is null then
      raise exception 'Unable to resolve existing request';
    end if;

    if v_existing_name <> v_name or v_existing_type <> p_type then
      raise exception 'Request ID reused with different workspace details';
    end if;

    return v_workspace_id;
  end if;

  insert into public.workspace_memberships (
    workspace_id, user_id, role, status
  )
  values (
    v_workspace_id, v_user_id, 'owner', 'active'
  );

  return v_workspace_id;
end;
$$;

revoke all on function public.create_workspace(text, text, uuid) from public;
revoke all on function public.create_workspace(text, text, uuid) from anon;
grant execute on function public.create_workspace(text, text, uuid)
  to authenticated;

-- SECURITY REVIEW REQUIRED:
-- Function owner, RLS bypass behavior, direct table privileges,
-- request replay, role escalation, audit logging and negative tests.
