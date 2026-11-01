-- ParentPlus M2: Identity and workspace foundation
-- Status: Draft; do not apply before security review.

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null check (length(trim(display_name)) > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.workspaces (
  id uuid primary key default gen_random_uuid(),
  name text not null check (length(trim(name)) > 0),
  type text not null check (type in ('independent', 'academy')),
  status text not null default 'active'
    check (status in ('active', 'suspended', 'archived')),
  created_by uuid not null references auth.users(id),
  creation_request_id uuid not null,
  created_at timestamptz not null default now(),
  unique (created_by, creation_request_id)
);

create table public.workspace_memberships (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id),
  user_id uuid not null references auth.users(id),
  role text not null check (role in ('owner', 'admin', 'coach')),
  status text not null default 'invited'
    check (status in ('invited', 'active', 'suspended', 'removed')),
  created_at timestamptz not null default now(),
  unique (workspace_id, user_id)
);

create index workspace_memberships_user_idx
  on public.workspace_memberships(user_id);

create index workspace_memberships_workspace_idx
  on public.workspace_memberships(workspace_id);

alter table public.profiles enable row level security;
alter table public.workspaces enable row level security;
alter table public.workspace_memberships enable row level security;

-- No application-user RLS policies are defined in this draft.
-- Workspace creation and initial Owner membership require a
-- trusted, authorized transaction to be designed and tested.
-- Table privileges and privileged-role access must be reviewed
-- before applying this migration.
