-- ParentPlus M2: Child creation idempotency
-- DRAFT ONLY. Do not deploy before security review.

alter table public.children
  add column creation_request_id uuid;

-- Every child created through the controlled V1 workflow
-- must use a unique request ID for its creator.
-- Nullable for migration compatibility and future imports.
create unique index children_creation_request_idx
  on public.children(created_by, creation_request_id)
  where creation_request_id is not null;

-- No application-user access granted by this migration.
-- Child creation must use a controlled authenticated function.
-- Existing-child linking requires separate guardian authorization.
