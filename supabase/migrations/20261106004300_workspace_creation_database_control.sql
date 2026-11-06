-- LOCAL DRAFT: defaults off; hosted rollout and receipt retention remain unreviewed.
begin;

create table public.workspace_creation_controls (
  id boolean primary key default true check (id),
  enabled boolean not null default false
);
insert into public.workspace_creation_controls (id, enabled) values (true, false);
alter table public.workspace_creation_controls enable row level security;
revoke all on public.workspace_creation_controls from public, anon, authenticated;

alter function public.create_workspace(text, text, uuid) rename to create_workspace_unguarded_private;
revoke all on function public.create_workspace_unguarded_private(text, text, uuid)
  from public, anon, authenticated;

create function public.create_workspace(p_name text, p_type text, p_request_id uuid)
returns uuid language plpgsql security definer set search_path = '' as $$
declare
  v_enabled boolean;
begin
  if auth.uid() is null then raise exception 'Authentication required'; end if;
  select enabled into v_enabled from public.workspace_creation_controls where id=true for share;
  if not found or not v_enabled then
    raise exception using errcode='42501', message='Workspace creation unavailable';
  end if;
  return public.create_workspace_unguarded_private(p_name, p_type, p_request_id);
end;
$$;
revoke all on function public.create_workspace(text, text, uuid) from public, anon, authenticated;
grant execute on function public.create_workspace(text, text, uuid) to authenticated;
commit;
