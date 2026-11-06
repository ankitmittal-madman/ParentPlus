-- Local draft: keep incomplete connection writes unavailable to application roles.
-- Review migration ordering and effective role privileges before any hosted rollout.
begin;
revoke all on function public.request_workspace_connection(uuid,uuid,uuid)
  from public, anon, authenticated;
revoke all on function public.approve_guardian_connection(uuid)
  from public, anon, authenticated;
commit;
