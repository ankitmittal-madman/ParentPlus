-- A retry must not recreate or bypass a removed, revoked or disputed relationship.
begin;
create or replace function public.create_child(p_display_name text, p_request_id uuid)
returns uuid language plpgsql security definer set search_path = '' as $$
declare
  v_user_id uuid := auth.uid();
  v_child_id uuid;
  v_existing_name text;
  v_name text := pg_catalog.btrim(p_display_name);
begin
  if v_user_id is null then
    raise exception 'Authentication required';
  end if;
  if v_name is null or pg_catalog.length(v_name) not between 1 and 120 then
    raise exception 'Invalid child name';
  end if;
  if p_request_id is null then
    raise exception 'Request ID required';
  end if;
  insert into public.children (display_name, created_by, creation_request_id)
    values (v_name, v_user_id, p_request_id)
    on conflict (created_by, creation_request_id) where creation_request_id is not null
    do nothing returning id into v_child_id;
  if v_child_id is null then
    select c.id, c.display_name into v_child_id, v_existing_name
      from public.children c where c.created_by=v_user_id and c.creation_request_id=p_request_id
      for update;
    if v_child_id is null then
      raise exception 'Child creation retry failed';
    end if;
    perform 1 from public.guardianships g
      where g.child_id=v_child_id and g.guardian_user_id=v_user_id
        and g.status in ('provisional','active') for share;
    if not found then
      raise exception using errcode='42501', message='Child creation unavailable';
    end if;
    if v_existing_name <> v_name then
      raise exception 'Request ID reused with different child details';
    end if;
    return v_child_id;
  end if;
  insert into public.guardianships (child_id, guardian_user_id, status, verification_level)
    values (v_child_id, v_user_id, 'provisional', 'self_declared');
  return v_child_id;
end;
$$;
revoke all on function public.create_child(text,uuid) from public,anon,authenticated;
grant execute on function public.create_child(text,uuid) to authenticated;
commit;
