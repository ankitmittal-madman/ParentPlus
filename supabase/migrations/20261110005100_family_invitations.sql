-- Founder testing: academy admission, separate from batch enrolment.
-- Atomic creation/grants; invitation secrets are never stored in plaintext.
begin;
create table public.family_invites (
  id uuid primary key,
  workspace_id uuid not null references public.workspaces(id),
  issued_by uuid not null references auth.users(id),
  token_hash text not null unique check (token_hash ~ '^[0-9a-f]{64}$'),
  created_at timestamptz not null default clock_timestamp(),
  expires_at timestamptz not null default (clock_timestamp() + interval '14 days'),
  accepted_by uuid references auth.users(id),
  child_id uuid references public.children(id),
  relationship_id uuid references public.workspace_children(id),
  accepted_at timestamptz,
  check ((accepted_by is null and child_id is null and relationship_id is null and accepted_at is null)
      or (accepted_by is not null and child_id is not null and relationship_id is not null and accepted_at is not null))
);
alter table public.family_invites enable row level security;
revoke all on public.family_invites from public, anon, authenticated;

create function public.app_issue_family_invite(p_workspace_id uuid, p_request_id uuid, p_token text)
returns table(invite_id uuid, expires_at timestamptz)
language plpgsql security definer set search_path='' as $$
declare v public.family_invites%rowtype; v_hash text;
begin
  perform public.assert_private_workspace_manager(p_workspace_id);
  if p_request_id is null or p_token is null or p_token !~ '^[0-9a-f]{64}$' then
    raise exception using errcode='22023',message='Invalid invitation details';
  end if;
  v_hash:=pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to(p_token,'UTF8')),'hex');
  insert into public.family_invites(id,workspace_id,issued_by,token_hash)
    values(p_request_id,p_workspace_id,auth.uid(),v_hash) on conflict(id) do nothing;
  select * into v from public.family_invites i where i.id=p_request_id for share;
  if v.workspace_id is distinct from p_workspace_id or v.issued_by is distinct from auth.uid()
    or v.token_hash is distinct from v_hash then
    raise exception using errcode='23505',message='Invitation request details changed';
  end if;
  return query select v.id,v.expires_at;
end $$;
revoke all on function public.app_issue_family_invite(uuid,uuid,text) from public,anon,authenticated;
grant execute on function public.app_issue_family_invite(uuid,uuid,text) to authenticated;

-- Private shared check locks current academy and inviter eligibility. A suspended
-- or demoted inviter cannot continue admitting families through an old link.
create function public.assert_private_family_invite_access(p_workspace_id uuid,p_issuer uuid)
returns void language plpgsql set search_path='' as $$
begin
  if auth.uid() is null then raise exception using errcode='42501',message='Invitation unavailable'; end if;
  perform 1 from public.workspaces where id=p_workspace_id and status='active' for share;
  if not found then raise exception using errcode='42501',message='Invitation unavailable'; end if;
  perform 1 from public.workspace_memberships where workspace_id=p_workspace_id and user_id=p_issuer
    and role in ('owner','admin') and status='active' for share;
  if not found then raise exception using errcode='42501',message='Invitation unavailable'; end if;
end $$;
revoke all on function public.assert_private_family_invite_access(uuid,uuid) from public,anon,authenticated;

create function public.app_preview_family_invite(p_token text)
returns table(academy_name text,expires_at timestamptz,state text)
language plpgsql security definer set search_path='' as $$
declare v public.family_invites%rowtype;
begin
  if auth.uid() is null or p_token is null or p_token !~ '^[0-9a-f]{64}$' then
    raise exception using errcode='42501',message='Invitation unavailable'; end if;
  select * into v from public.family_invites where token_hash=pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to(p_token,'UTF8')),'hex') for share;
  if not found then raise exception using errcode='42501',message='Invitation unavailable'; end if;
  perform public.assert_private_family_invite_access(v.workspace_id,v.issued_by);
  if (v.accepted_by is null and v.expires_at<=pg_catalog.clock_timestamp())
    or (v.accepted_by is not null and v.accepted_by<>auth.uid()) then
    raise exception using errcode='42501',message='Invitation unavailable'; end if;
  return query select w.name,v.expires_at,case when v.accepted_by is null then 'pending' else 'accepted' end
    from public.workspaces w where w.id=v.workspace_id;
end $$;
revoke all on function public.app_preview_family_invite(text) from public,anon,authenticated;
grant execute on function public.app_preview_family_invite(text) to authenticated;

create function public.app_accept_family_invite(p_token text,p_child_id uuid)
returns uuid language plpgsql security definer set search_path='' as $$
declare v public.family_invites%rowtype; v_relationship uuid; v_status text; v_actor uuid:=auth.uid();
begin
  if v_actor is null or p_child_id is null or p_token is null or p_token !~ '^[0-9a-f]{64}$' then
    raise exception using errcode='42501',message='Invitation unavailable'; end if;
  select * into v from public.family_invites where token_hash=pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to(p_token,'UTF8')),'hex') for update;
  if not found then raise exception using errcode='42501',message='Invitation unavailable'; end if;
  perform public.assert_private_family_invite_access(v.workspace_id,v.issued_by);
  if v.issued_by=v_actor or (v.accepted_by is not null and (v.accepted_by<>v_actor or v.child_id<>p_child_id)) then
    raise exception using errcode='42501',message='Invitation unavailable'; end if;
  perform 1 from public.children where id=p_child_id and created_by=v_actor for share;
  if not found then raise exception using errcode='42501',message='Child profile unavailable'; end if;
  perform 1 from public.guardianships where child_id=p_child_id and guardian_user_id=v_actor
    and status in ('provisional','active') for share;
  if not found then raise exception using errcode='42501',message='Child profile unavailable'; end if;
  -- Expiry is checked after every potentially waiting eligibility lock.
  if v.accepted_by is null and v.expires_at<=pg_catalog.clock_timestamp() then
    raise exception using errcode='42501',message='Invitation unavailable'; end if;
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(v.workspace_id::text||':'||p_child_id::text,0));
  select id,status into v_relationship,v_status from public.workspace_children
    where workspace_id=v.workspace_id and child_id=p_child_id for update;
  if found and v_status<>'active' then raise exception using errcode='42501',message='Connection unavailable'; end if;
  if v.accepted_by is not null then
    if v_relationship is distinct from v.relationship_id then raise exception using errcode='42501',message='Connection unavailable'; end if;
    return v_relationship;
  end if;
  if v.expires_at<=pg_catalog.clock_timestamp() then raise exception using errcode='42501',message='Invitation unavailable'; end if;
  if v_relationship is null then
    insert into public.workspace_children(workspace_id,child_id) values(v.workspace_id,p_child_id) returning id into v_relationship;
  end if;
  insert into public.connection_requests(id,workspace_id,child_id,guardian_user_id,initiated_by,initiation_type,status,expires_at,confirmed_by,confirmed_at)
    values(v.id,v.workspace_id,p_child_id,v_actor,v.issued_by,'workspace','approved',v.expires_at,v_actor,pg_catalog.clock_timestamp());
  insert into public.connection_events(connection_request_id,workspace_child_id,actor_user_id,event_type)
    values(v.id,v_relationship,v_actor,'approved');
  update public.family_invites set accepted_by=v_actor,child_id=p_child_id,relationship_id=v_relationship,accepted_at=pg_catalog.clock_timestamp() where id=v.id;
  return v_relationship;
end $$;
revoke all on function public.app_accept_family_invite(text,uuid) from public,anon,authenticated;
grant execute on function public.app_accept_family_invite(text,uuid) to authenticated;

create function public.app_family_roster(p_workspace_id uuid,p_after uuid default null)
returns table(relationship_id uuid,child_name text,relationship_status text)
language plpgsql security definer set search_path='' as $$
begin
  perform public.assert_private_workspace_manager(p_workspace_id);
  return query select r.id,c.display_name,r.status from public.workspace_children r
    join public.children c on c.id=r.child_id where r.workspace_id=p_workspace_id
      and (p_after is null or r.id>p_after) order by r.id limit 50;
end $$;
revoke all on function public.app_family_roster(uuid,uuid) from public,anon,authenticated;
grant execute on function public.app_family_roster(uuid,uuid) to authenticated;

create function public.app_child_academies(p_child_id uuid)
returns table(relationship_id uuid,academy_name text,relationship_status text)
language plpgsql security definer set search_path='' as $$
begin
  if auth.uid() is null then raise exception using errcode='42501',message='Child profile unavailable'; end if;
  perform 1 from public.children c join public.guardianships g on g.child_id=c.id
    where c.id=p_child_id and c.created_by=auth.uid() and g.guardian_user_id=auth.uid()
      and g.status in ('provisional','active') for share of c,g;
  if not found then raise exception using errcode='42501',message='Child profile unavailable'; end if;
  return query select r.id,w.name,r.status from public.workspace_children r
    join public.workspaces w on w.id=r.workspace_id where r.child_id=p_child_id and w.status='active'
      and r.status='active' order by r.id limit 100;
end $$;
revoke all on function public.app_child_academies(uuid) from public,anon,authenticated;
grant execute on function public.app_child_academies(uuid) to authenticated;
commit;
