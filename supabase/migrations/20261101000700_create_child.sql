-- ParentPlus M2: Controlled child creation
-- DRAFT ONLY. Requires security and concurrency testing.

create or replace function public.create_child(
  p_display_name text,
  p_request_id uuid
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_user_id uuid;
  v_child_id uuid;
  v_existing_name text;
  v_name text;
begin
  v_user_id := auth.uid();

  if v_user_id is null then
    raise exception 'Authentication required';
  end if;

  v_name := trim(p_display_name);

  if p_display_name is null
     or length(v_name) < 1
     or length(v_name) > 120 then
    raise exception 'Invalid child name';
  end if;

  if p_request_id is null then
    raise exception 'Request ID required';
  end if;

  insert into public.children (
    display_name, created_by, creation_request_id
  )
  values (
    v_name, v_user_id, p_request_id
  )
  on conflict (created_by, creation_request_id)
    where creation_request_id is not null
  do nothing
  returning id into v_child_id;

  if v_child_id is null then
    select id, display_name
    into v_child_id, v_existing_name
    from public.children
    where created_by = v_user_id
      and creation_request_id = p_request_id;

    if v_child_id is null then
      raise exception 'Child creation retry failed';
    end if;

    if v_existing_name <> v_name then
      raise exception 'Request ID reused with different child details';
    end if;
  end if;

  insert into public.guardianships (
    child_id, guardian_user_id, status, verification_level
  )
  values (
    v_child_id, v_user_id, 'provisional', 'self_declared'
  )
  on conflict (child_id, guardian_user_id) do nothing;

  return v_child_id;
end;
$$;

revoke all on function public.create_child(text, uuid) from public;
revoke all on function public.create_child(text, uuid) from anon;
grant execute on function public.create_child(text, uuid) to authenticated;

-- SECURITY REVIEW REQUIRED:
-- Verify function ownership and execution privileges.
-- Verify atomic child and guardianship creation.
-- Verify idempotency under concurrent requests.
-- Prevent unauthorized linking to existing child identities.
-- Do not expose unrestricted child or guardian records.
