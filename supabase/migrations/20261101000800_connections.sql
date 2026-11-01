-- ParentPlus M2: Connection and relationship foundation
-- DRAFT ONLY. Do not deploy before security review.

create table public.connection_requests (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id),
  child_id uuid references public.children(id),
  guardian_user_id uuid references auth.users(id),
  initiated_by uuid not null references auth.users(id),
  initiation_type text not null
    check (initiation_type in ('workspace', 'guardian')),
  status text not null default 'pending'
    check (status in (
      'pending', 'approved', 'rejected', 'expired', 'cancelled'
    )),
  expires_at timestamptz not null,
  confirmed_by uuid references auth.users(id),
  confirmed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint connection_approval_integrity check (
    (
      status = 'approved'
      and child_id is not null
      and guardian_user_id is not null
      and confirmed_by is not null
      and confirmed_at is not null
    )
    or (
      status <> 'approved'
      and confirmed_by is null
      and confirmed_at is null
    )
  )
);

create table public.workspace_children (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id),
  child_id uuid not null references public.children(id),
  status text not null default 'active'
    check (status in (
      'active', 'alumni', 'restricted', 'archived'
    )),
  connected_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (workspace_id, child_id)
);

create table public.connection_events (
  id uuid primary key default gen_random_uuid(),
  connection_request_id uuid references public.connection_requests(id),
  workspace_child_id uuid references public.workspace_children(id),
  actor_user_id uuid references auth.users(id),
  event_type text not null
    check (event_type in (
      'requested', 'approved', 'rejected',
      'cancelled', 'expired', 'restricted',
      'reactivated', 'archived'
    )),
  created_at timestamptz not null default now(),
  check (
    connection_request_id is not null
    or workspace_child_id is not null
  )
);

create index connection_requests_workspace_idx
  on public.connection_requests(workspace_id);

create index connection_requests_guardian_idx
  on public.connection_requests(guardian_user_id);

create index connection_requests_child_idx
  on public.connection_requests(child_id);

create index workspace_children_child_idx
  on public.workspace_children(child_id);

create index connection_events_request_idx
  on public.connection_events(connection_request_id);

create index connection_events_relationship_idx
  on public.connection_events(workspace_child_id);

alter table public.connection_requests enable row level security;
alter table public.workspace_children enable row level security;
alter table public.connection_events enable row level security;

-- No direct application-user access or RLS policies in this draft.
-- Approval and activation require separate authorized functions.
-- Invitation tokens must be stored securely in a separate design.
-- Guardian self-declaration is not formal legal verification.
-- No enrollment is created by connection approval.
