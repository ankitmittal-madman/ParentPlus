-- ParentPlus M2: Pending guardian connection uniqueness
-- DRAFT ONLY. Requires lifecycle and concurrency testing.

-- Pending guardian-initiated requests must identify
-- both a child and guardian.
alter table public.connection_requests
  add constraint guardian_pending_identity_required
  check (
    initiation_type <> 'guardian'
    or status <> 'pending'
    or (
      child_id is not null
      and guardian_user_id is not null
    )
  );

-- Prevent multiple pending requests for the same
-- guardian, child and workspace.
create unique index guardian_pending_connection_idx
  on public.connection_requests(
    workspace_id,
    child_id,
    guardian_user_id
  )
  where initiation_type = 'guardian'
    and status = 'pending';

-- Expired requests must be transitioned out of pending
-- before a replacement request is created.
-- The controlled initiation function must handle this
-- atomically and prevent unauthorized transitions.
-- No application-user privileges granted here.
