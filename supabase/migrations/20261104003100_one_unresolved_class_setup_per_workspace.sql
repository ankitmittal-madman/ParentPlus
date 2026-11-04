-- Conservative local draft: one unresolved class setup per workspace.
-- Building the index fails closed if existing unresolved duplicates exist.
begin;
create unique index class_setup_one_unresolved_per_workspace
  on public.class_setup_intents (workspace_id)
  where not acknowledged;
commit;
