-- Private operation receipts preserve intent across delayed retries. Direct app access is denied.
create table public.batch_coach_mutation_requests (
  actor_id uuid not null references auth.users(id),
  request_id uuid not null,
  operation text not null check (operation in ('assign', 'remove')),
  workspace_id uuid not null,
  batch_id uuid not null,
  membership_id uuid not null,
  primary key (actor_id, request_id),
  foreign key (workspace_id, batch_id) references public.batches(workspace_id, id),
  foreign key (workspace_id, membership_id) references public.workspace_memberships(workspace_id, id)
);
alter table public.batch_coach_mutation_requests enable row level security;
revoke all on public.batch_coach_mutation_requests from public, anon, authenticated;

-- Remove the older unversioned operation so privileged callers cannot bypass replay protection.
drop function public.assign_private_batch_coach(uuid, uuid, uuid);

-- Actor and workspace checks precede any receipt lookup. Request-key and target
-- locks serialize concurrent calls even when the assignment row does not exist.
create function public.mutate_private_batch_coach(p_workspace_id uuid, p_batch_id uuid, p_membership_id uuid, p_request_id uuid, p_operation text)
returns void language plpgsql set search_path = '' as $$
declare v_actor uuid := auth.uid(); v_prior record;
begin
  perform public.assert_private_workspace_manager(p_workspace_id);
  if p_batch_id is null or p_membership_id is null or p_request_id is null or p_operation not in ('assign', 'remove') or p_operation is null then
    raise exception using errcode='22023', message='Invalid coach assignment';
  end if;
  perform 1 from public.batches where workspace_id=p_workspace_id and id=p_batch_id for share;
  if not found then raise exception using errcode='22023', message='Invalid coach assignment'; end if;
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('coach-request:' || v_actor::text || ':' || p_request_id::text, 0));
  select operation, workspace_id, batch_id, membership_id into v_prior
    from public.batch_coach_mutation_requests where actor_id=v_actor and request_id=p_request_id;
  if found then
    if v_prior.operation is distinct from p_operation or v_prior.workspace_id is distinct from p_workspace_id or v_prior.batch_id is distinct from p_batch_id or v_prior.membership_id is distinct from p_membership_id then
      raise exception using errcode='23505', message='Coach assignment request conflicts with existing details';
    end if;
    return;
  end if;
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('coach-target:' || p_workspace_id::text || ':' || p_batch_id::text || ':' || p_membership_id::text, 0));
  perform 1 from public.workspace_memberships where workspace_id=p_workspace_id and id=p_membership_id
    and (p_operation='remove' or (role='coach' and status='active')) for share;
  if not found then raise exception using errcode='22023', message='Invalid coach assignment'; end if;
  insert into public.batch_coach_mutation_requests (actor_id, request_id, operation, workspace_id, batch_id, membership_id)
    values (v_actor, p_request_id, p_operation, p_workspace_id, p_batch_id, p_membership_id);
  if p_operation='assign' then
    insert into public.batch_coach_assignments (workspace_id, batch_id, membership_id)
      values (p_workspace_id, p_batch_id, p_membership_id) on conflict do nothing;
  else
    delete from public.batch_coach_assignments where workspace_id=p_workspace_id and batch_id=p_batch_id and membership_id=p_membership_id;
  end if;
end;
$$;
revoke all on function public.mutate_private_batch_coach(uuid,uuid,uuid,uuid,text) from public, anon, authenticated;

create function public.assign_private_batch_coach(p_workspace_id uuid, p_batch_id uuid, p_membership_id uuid, p_request_id uuid)
returns void language sql set search_path = '' as $$
  select public.mutate_private_batch_coach(p_workspace_id, p_batch_id, p_membership_id, p_request_id, 'assign');
$$;
revoke all on function public.assign_private_batch_coach(uuid,uuid,uuid,uuid) from public, anon, authenticated;

create function public.remove_private_batch_coach(p_workspace_id uuid, p_batch_id uuid, p_membership_id uuid, p_request_id uuid)
returns void language sql set search_path = '' as $$
  select public.mutate_private_batch_coach(p_workspace_id, p_batch_id, p_membership_id, p_request_id, 'remove');
$$;
revoke all on function public.remove_private_batch_coach(uuid,uuid,uuid,uuid) from public, anon, authenticated;
