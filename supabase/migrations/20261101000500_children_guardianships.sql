-- ParentPlus M2: Child identity and guardian relationships
-- DRAFT ONLY. Do not deploy before authorization review.

create table public.children (
  id uuid primary key default gen_random_uuid(),
  display_name text not null
    check (length(trim(display_name)) between 1 and 120),
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.guardianships (
  id uuid primary key default gen_random_uuid(),
  child_id uuid not null references public.children(id),
  guardian_user_id uuid not null references auth.users(id),
  status text not null default 'provisional'
    check (status in (
      'provisional', 'active', 'revoked', 'disputed'
    )),
  verification_level text not null default 'self_declared'
    check (verification_level in (
      'self_declared', 'connection_confirmed', 'formally_verified'
    )),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (child_id, guardian_user_id)
);

create index children_created_by_idx
  on public.children(created_by);

create index guardianships_guardian_idx
  on public.guardianships(guardian_user_id);

create index guardianships_child_idx
  on public.guardianships(child_id);

alter table public.children enable row level security;
alter table public.guardianships enable row level security;

-- No application-user RLS policies in this migration.
-- Child creation and guardian linking require controlled functions.
-- No unrestricted child or guardian directory access.
-- Do not grant direct INSERT, UPDATE or DELETE privileges yet.
-- Formal verification workflows remain deferred.
