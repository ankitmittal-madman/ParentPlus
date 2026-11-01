-- ParentPlus M2: Connection request idempotency
-- DRAFT ONLY. Requires authorization review.

alter table public.connection_requests
  add column creation_request_id uuid;

-- One logical request per initiating user and request ID.
-- Nullable to support future invitation and import workflows.
create unique index connection_request_idempotency_idx
  on public.connection_requests(
    initiated_by,
    creation_request_id
  )
  where creation_request_id is not null;

-- This index prevents duplicate request IDs.
-- It does not prevent different pending requests for the
-- same child and workspace using different request IDs.
-- That rule requires a separate lifecycle and concurrency design.
