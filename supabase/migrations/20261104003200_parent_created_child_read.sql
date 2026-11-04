-- Local draft: narrowly scoped, default-off read of profiles created by a parent.
begin;
create table public.parent_child_read_controls (
  id boolean primary key default true check (id),
  enabled boolean not null default false
);
insert into public.parent_child_read_controls (id, enabled) values (true, false);
alter table public.parent_child_read_controls enable row level security;
revoke all on public.parent_child_read_controls from public, anon, authenticated;

create function public.app_list_created_children()
returns table (child_id uuid, display_name text)
language plpgsql security definer set search_path = '' as $$
declare
  v_actor uuid := auth.uid();
  v_enabled boolean;
  v_row record;
  v_count integer := 0;
begin
  if v_actor is null then
    raise exception using errcode='42501', message='Child profiles unavailable';
  end if;
  select enabled into v_enabled from public.parent_child_read_controls where id=true for share;
  if not found or not v_enabled then
    raise exception using errcode='42501', message='Child profiles unavailable';
  end if;
  for v_row in
    select c.id, c.display_name from public.children c
      join public.guardianships g on g.child_id=c.id
      where c.created_by=v_actor and g.guardian_user_id=v_actor
        and g.status in ('provisional','active')
      order by c.id limit 101 for share of c,g
  loop
    v_count := v_count + 1;
    if v_count > 100 then
      raise exception using errcode='54000', message='Child profiles unavailable';
    end if;
    child_id := v_row.id;
    display_name := v_row.display_name;
    return next;
  end loop;
end;
$$;
revoke all on function public.app_list_created_children() from public, anon, authenticated;
grant execute on function public.app_list_created_children() to authenticated;
commit;
