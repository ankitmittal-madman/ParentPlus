-- Explicit admission is separate from academy connection. All tables remain
-- private; authenticated RPCs lock the current authority through transaction end.
begin;

create table public.enrollments (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null,
  batch_id uuid not null,
  child_id uuid not null references public.children(id),
  status text not null default 'active'
    check (status in ('pending','active','paused','completed','withdrawn','cancelled')),
  version integer not null default 1 check (version > 0),
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default clock_timestamp(),
  updated_at timestamptz not null default clock_timestamp(),
  unique (child_id,batch_id),
  foreign key (workspace_id,batch_id) references public.batches(workspace_id,id),
  foreign key (workspace_id,child_id) references public.workspace_children(workspace_id,child_id)
);
create index enrollments_workspace_batch_page_idx on public.enrollments(workspace_id,batch_id,id);
create index enrollments_child_page_idx on public.enrollments(child_id,id);

create table public.enrollment_request_receipts (
  request_id uuid primary key,
  actor_id uuid not null references auth.users(id),
  operation text not null check (operation in ('save','change')),
  workspace_id uuid not null references public.workspaces(id),
  batch_id uuid not null references public.batches(id),
  child_id uuid not null references public.children(id),
  enrollment_id uuid not null references public.enrollments(id),
  requested_status text,
  expected_version integer,
  reason text check (reason in ('temporary_break','schedule_change','other')),
  result_status text not null check (result_status in ('pending','active','paused','completed','withdrawn','cancelled')),
  result_version integer not null check (result_version > 0),
  created_at timestamptz not null default clock_timestamp(),
  check ((operation='save' and requested_status is null and expected_version is null and reason is null)
    or (operation='change' and requested_status in ('active','paused','completed','withdrawn') and expected_version > 0
      and ((requested_status in ('paused','withdrawn') and reason is not null)
        or (requested_status in ('active','completed') and reason is null))))
);
create index enrollment_receipts_workspace_idx on public.enrollment_request_receipts(workspace_id);

create table public.enrollment_events (
  id uuid primary key default gen_random_uuid(),
  enrollment_id uuid not null references public.enrollments(id),
  actor_id uuid not null references auth.users(id),
  from_status text check (from_status in ('pending','active','paused','completed','withdrawn','cancelled')),
  to_status text not null check (to_status in ('active','paused','completed','withdrawn')),
  version integer not null check (version > 0),
  reason text check (reason in ('temporary_break','schedule_change','other')),
  created_at timestamptz not null default clock_timestamp(),
  unique (enrollment_id,version)
);

alter table public.enrollments enable row level security;
alter table public.enrollment_request_receipts enable row level security;
alter table public.enrollment_events enable row level security;
revoke all on public.enrollments,public.enrollment_request_receipts,public.enrollment_events from public,anon,authenticated;

-- These helpers are invoker-only and have no application grants. RPCs execute
-- them as their definer, never trusting actor or tenant identifiers from clients.
create function public.assert_private_enrollment_target(p_workspace_id uuid,p_batch_id uuid,p_child_id uuid)
returns void language plpgsql set search_path='' as $$
begin
  perform public.assert_private_workspace_manager(p_workspace_id);
  perform 1 from public.batches b join public.courses c on c.id=b.course_id and c.workspace_id=b.workspace_id
    where b.workspace_id=p_workspace_id and b.id=p_batch_id for share of b,c;
  if not found then raise exception using errcode='42501',message='Enrollment batch unavailable'; end if;
  perform 1 from public.workspace_children r join public.children c on c.id=r.child_id
    where r.workspace_id=p_workspace_id and r.child_id=p_child_id and r.status='active' for share of r,c;
  if not found then raise exception using errcode='42501',message='Enrollment connection unavailable'; end if;
end $$;
revoke all on function public.assert_private_enrollment_target(uuid,uuid,uuid) from public,anon,authenticated;

create function public.app_enrollment_batches(p_workspace_id uuid)
returns table(batch_id uuid,batch_name text,course_name text)
language plpgsql security definer set search_path='' as $$
declare v_member uuid; v_role text;
begin
  if auth.uid() is null then raise exception using errcode='42501',message='Enrollment access denied'; end if;
  perform 1 from public.workspaces where id=p_workspace_id and status='active' for share;
  if not found then raise exception using errcode='42501',message='Enrollment access denied'; end if;
  select m.id,m.role into v_member,v_role from public.workspace_memberships m
    where m.workspace_id=p_workspace_id and m.user_id=auth.uid() and m.status='active' for share;
  if not found or v_role not in ('owner','admin','coach') then
    raise exception using errcode='42501',message='Enrollment access denied'; end if;
  if v_role in ('owner','admin') then
    return query select b.id,b.name,c.name from public.batches b
      join public.courses c on c.id=b.course_id and c.workspace_id=b.workspace_id
      where b.workspace_id=p_workspace_id order by b.id for share of b,c;
  else
    return query select b.id,b.name,c.name from public.batches b
      join public.courses c on c.id=b.course_id and c.workspace_id=b.workspace_id
      join public.batch_coach_assignments a on a.workspace_id=b.workspace_id and a.batch_id=b.id
      where b.workspace_id=p_workspace_id and a.membership_id=v_member order by b.id for share of b,c,a;
  end if;
end $$;

create function public.app_enrollment_candidates(p_workspace_id uuid,p_after uuid default null)
returns table(child_id uuid,child_name text)
language plpgsql security definer set search_path='' as $$
begin
  perform public.assert_private_workspace_manager(p_workspace_id);
  return query select c.id,c.display_name from public.workspace_children r join public.children c on c.id=r.child_id
    where r.workspace_id=p_workspace_id and r.status='active' and (p_after is null or c.id>p_after)
    order by c.id limit 50 for share of r,c;
end $$;

create function public.app_batch_enrollments(p_workspace_id uuid,p_batch_id uuid,p_after uuid default null)
returns table(enrollment_id uuid,child_id uuid,child_name text,status text,version integer)
language plpgsql security definer set search_path='' as $$
begin
  -- The existing schedule guard has exactly the required manager/assigned coach
  -- authority and locks workspace, membership, batch and coach assignment.
  perform public.assert_schedule_write_access(p_workspace_id,p_batch_id);
  return query select e.id,c.id,c.display_name,e.status,e.version from public.enrollments e
    join public.workspace_children r on r.workspace_id=e.workspace_id and r.child_id=e.child_id
    join public.children c on c.id=e.child_id
    where e.workspace_id=p_workspace_id and e.batch_id=p_batch_id and r.status='active'
      and (p_after is null or e.id>p_after) order by e.id limit 50 for share of e,r,c;
end $$;

create function public.app_save_enrollment(p_workspace_id uuid,p_batch_id uuid,p_child_id uuid,p_request_id uuid)
returns table(enrollment_id uuid,status text,version integer)
language plpgsql security definer set search_path='' as $$
declare v public.enrollments%rowtype; r public.enrollment_request_receipts%rowtype;
begin
  perform public.assert_private_enrollment_target(p_workspace_id,p_batch_id,p_child_id);
  if p_request_id is null then raise exception using errcode='22023',message='Enrollment request required'; end if;
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('enrollment-request:'||p_request_id::text,0));
  select * into r from public.enrollment_request_receipts q where q.request_id=p_request_id;
  if found then
    if r.actor_id is distinct from auth.uid() or r.operation<>'save'
      or r.workspace_id is distinct from p_workspace_id or r.batch_id is distinct from p_batch_id
      or r.child_id is distinct from p_child_id then
      raise exception using errcode='23505',message='Enrollment request details changed'; end if;
    return query select r.enrollment_id,r.result_status,r.result_version;
    return;
  end if;
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('enrollment:'||p_batch_id::text||':'||p_child_id::text,0));
  select * into v from public.enrollments e where e.batch_id=p_batch_id and e.child_id=p_child_id for update;
  if found then
    if v.status<>'active' then raise exception using errcode='23505',message='Enrollment already exists in another state'; end if;
  else
    insert into public.enrollments(workspace_id,batch_id,child_id,created_by)
      values(p_workspace_id,p_batch_id,p_child_id,auth.uid()) returning * into v;
    insert into public.enrollment_events(enrollment_id,actor_id,from_status,to_status,version)
      values(v.id,auth.uid(),null,'active',1);
  end if;
  insert into public.enrollment_request_receipts(request_id,actor_id,operation,workspace_id,batch_id,child_id,enrollment_id,result_status,result_version)
    values(p_request_id,auth.uid(),'save',p_workspace_id,p_batch_id,p_child_id,v.id,v.status,v.version);
  return query select v.id,v.status,v.version;
end $$;

create function public.app_change_enrollment(p_enrollment_id uuid,p_status text,p_expected_version integer,p_reason text,p_request_id uuid)
returns table(enrollment_id uuid,status text,version integer)
language plpgsql security definer set search_path='' as $$
declare v public.enrollments%rowtype; r public.enrollment_request_receipts%rowtype; v_old_status text;
begin
  select * into v from public.enrollments e where e.id=p_enrollment_id;
  if not found then raise exception using errcode='42501',message='Enrollment unavailable'; end if;
  perform public.assert_private_enrollment_target(v.workspace_id,v.batch_id,v.child_id);
  if p_request_id is null or p_status is null or p_status not in ('active','paused','completed','withdrawn')
    or p_expected_version is null or p_expected_version<1
    or (p_status in ('paused','withdrawn') and (p_reason is null or p_reason not in ('temporary_break','schedule_change','other')))
    or (p_status in ('active','completed') and p_reason is not null) then
    raise exception using errcode='22023',message='Invalid enrollment transition details'; end if;
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('enrollment-request:'||p_request_id::text,0));
  select * into r from public.enrollment_request_receipts q where q.request_id=p_request_id;
  if found then
    if r.actor_id is distinct from auth.uid() or r.operation<>'change' or r.enrollment_id is distinct from p_enrollment_id
      or r.requested_status is distinct from p_status or r.expected_version is distinct from p_expected_version
      or r.reason is distinct from p_reason then
      raise exception using errcode='23505',message='Enrollment request details changed'; end if;
    return query select r.enrollment_id,r.result_status,r.result_version;
    return;
  end if;
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('enrollment:'||v.batch_id::text||':'||v.child_id::text,0));
  select * into v from public.enrollments e where e.id=p_enrollment_id for update;
  if not found then raise exception using errcode='42501',message='Enrollment unavailable'; end if;
  if v.version<>p_expected_version then raise exception using errcode='40001',message='Enrollment version changed; refresh before editing'; end if;
  if not ((v.status='active' and p_status in ('paused','completed','withdrawn'))
    or (v.status='paused' and p_status in ('active','completed','withdrawn'))) then
    raise exception using errcode='22023',message='Invalid enrollment transition'; end if;
  v_old_status:=v.status;
  update public.enrollments e set status=p_status,version=e.version+1,updated_at=pg_catalog.clock_timestamp()
    where e.id=p_enrollment_id returning * into v;
  insert into public.enrollment_events(enrollment_id,actor_id,from_status,to_status,version,reason)
    values(v.id,auth.uid(),v_old_status,v.status,v.version,p_reason);
  insert into public.enrollment_request_receipts(request_id,actor_id,operation,workspace_id,batch_id,child_id,enrollment_id,requested_status,expected_version,reason,result_status,result_version)
    values(p_request_id,auth.uid(),'change',v.workspace_id,v.batch_id,v.child_id,v.id,p_status,p_expected_version,p_reason,v.status,v.version);
  return query select v.id,v.status,v.version;
end $$;

create function public.app_parent_enrollments(p_child_id uuid)
returns table(enrollment_id uuid,academy_name text,batch_name text,course_name text,status text,version integer)
language plpgsql security definer set search_path='' as $$
begin
  if auth.uid() is null then raise exception using errcode='42501',message='Child profile unavailable'; end if;
  perform 1 from public.children c join public.guardianships g on g.child_id=c.id
    where c.id=p_child_id and c.created_by=auth.uid() and g.guardian_user_id=auth.uid()
      and g.status in ('provisional','active') for share of c,g;
  if not found then raise exception using errcode='42501',message='Child profile unavailable'; end if;
  return query select e.id,w.name,b.name,c.name,e.status,e.version from public.enrollments e
    join public.workspaces w on w.id=e.workspace_id
    join public.workspace_children r on r.workspace_id=e.workspace_id and r.child_id=e.child_id
    join public.batches b on b.workspace_id=e.workspace_id and b.id=e.batch_id
    join public.courses c on c.workspace_id=b.workspace_id and c.id=b.course_id
    where e.child_id=p_child_id and w.status='active' and r.status='active'
    order by e.id limit 100 for share of e,w,r,b,c;
end $$;

-- No default PUBLIC execution window: creation and all ACL changes commit together.
revoke all on function public.app_enrollment_batches(uuid),public.app_enrollment_candidates(uuid,uuid),
  public.app_batch_enrollments(uuid,uuid,uuid),public.app_save_enrollment(uuid,uuid,uuid,uuid),
  public.app_change_enrollment(uuid,text,integer,text,uuid),public.app_parent_enrollments(uuid) from public,anon,authenticated;
grant execute on function public.app_enrollment_batches(uuid),public.app_enrollment_candidates(uuid,uuid),
  public.app_batch_enrollments(uuid,uuid,uuid),public.app_save_enrollment(uuid,uuid,uuid,uuid),
  public.app_change_enrollment(uuid,text,integer,text,uuid),public.app_parent_enrollments(uuid) to authenticated;
commit;
