-- ParentPlus M2: Initial RLS policies
-- DRAFT ONLY. Requires database security testing.

-- Restrict direct application-role table operations.
revoke all on public.profiles from anon, authenticated;
revoke all on public.workspaces from anon, authenticated;
revoke all on public.workspace_memberships from anon, authenticated;

-- Profile access: own record only.
grant select on public.profiles to authenticated;
grant update (display_name) on public.profiles to authenticated;

create policy profiles_select_own
on public.profiles
for select
to authenticated
using (id = (select auth.uid()));

create policy profiles_update_own
on public.profiles
for update
to authenticated
using (id = (select auth.uid()))
with check (id = (select auth.uid()));

-- Membership access: own active memberships only.
grant select on public.workspace_memberships to authenticated;

create policy memberships_select_own_active
on public.workspace_memberships
for select
to authenticated
using (
  user_id = (select auth.uid())
  and status = 'active'
);

-- Workspace access: active membership required.
grant select on public.workspaces to authenticated;

create policy workspaces_select_active_member
on public.workspaces
for select
to authenticated
using (
  exists (
    select 1
    from public.workspace_memberships m
    where m.workspace_id = workspaces.id
      and m.user_id = (select auth.uid())
      and m.status = 'active'
  )
);

-- No direct insert, update or delete privileges are granted
-- for workspaces or workspace_memberships.
-- Staff invitations and role changes require future trusted operations.
-- Verify effective privileges and function ownership before deployment.
