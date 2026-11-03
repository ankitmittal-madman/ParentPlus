-- Local draft only: hosted ownership, signed-JWT, security and integration review required.
-- Definition and revoke are one transactional statement, with no PUBLIC window.
do $migration$
begin
  execute $definition$
create function public.create_batch(p_workspace_id uuid, p_course_id uuid, p_name text, p_request_id uuid)
returns uuid
language sql
security definer
set search_path = ''
as $$
  select public.create_private_batch(p_workspace_id, p_course_id, p_name, p_request_id);
$$;
$definition$;
-- Stay private until the guarded 018 migration installs the shared control.
revoke all on function public.create_batch(uuid, uuid, text, uuid) from public, anon, authenticated;
end;
$migration$;
