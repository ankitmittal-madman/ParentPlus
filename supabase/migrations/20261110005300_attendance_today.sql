-- Explicit confirmation and parent reports. Private persistence, bounded RPCs.
begin;
alter table public.schedule_sessions
 add column status text not null default 'scheduled' check(status in ('scheduled','cancelled')),
 add column version integer not null default 1 check(version>0),
 add column updated_at timestamptz not null default clock_timestamp(),
 add unique(workspace_id,batch_id,id);
alter table public.enrollments add unique(workspace_id,batch_id,child_id,id);
create function public.attendance_session_lifecycle() returns trigger language plpgsql set search_path='' as $$
begin
 if new.workspace_id is distinct from old.workspace_id or new.batch_id is distinct from old.batch_id then
  raise exception using errcode='22023',message='Session scope immutable'; end if;
 if (new.starts_at,new.ends_at,new.status) is distinct from (old.starts_at,old.ends_at,old.status) then
  new.version:=old.version+1; new.updated_at:=clock_timestamp();
 else new.version:=old.version; new.updated_at:=old.updated_at; end if;
 return new;
end $$;
create trigger attendance_session_lifecycle before update on public.schedule_sessions for each row execute function public.attendance_session_lifecycle();
create table public.attendance_sheets(
 session_id uuid primary key,workspace_id uuid not null,batch_id uuid not null,
 version integer not null check(version>0),session_version integer not null check(session_version>0),
 roster_token text not null check(roster_token ~ '^[0-9a-f]{64}$'),roster_size integer not null check(roster_size between 1 and 200),
 saved_by uuid not null references auth.users(id),saved_at timestamptz not null,
 unique(workspace_id,batch_id,session_id),
 foreign key(workspace_id,batch_id,session_id) references public.schedule_sessions(workspace_id,batch_id,id));
create table public.attendance_records(
 session_id uuid not null,workspace_id uuid not null,batch_id uuid not null,enrollment_id uuid not null,child_id uuid not null,
 status text not null check(status in ('present','late','absent','excused','make_up')),
 sheet_version integer not null check(sheet_version>0),source text not null default 'coach_confirmed' check(source='coach_confirmed'),
 confirmed_by uuid not null references auth.users(id),confirmed_at timestamptz not null,
 primary key(session_id,enrollment_id),unique(session_id,child_id),unique(workspace_id,batch_id,session_id,enrollment_id,child_id),
 foreign key(workspace_id,batch_id,session_id) references public.attendance_sheets(workspace_id,batch_id,session_id),
 foreign key(workspace_id,batch_id,child_id,enrollment_id) references public.enrollments(workspace_id,batch_id,child_id,id));
create table public.attendance_record_events(
 id uuid primary key default gen_random_uuid(),workspace_id uuid not null,batch_id uuid not null,session_id uuid not null,enrollment_id uuid not null,child_id uuid not null,
 status text not null check(status in ('present','late','absent','excused','make_up')),
 from_status text check(from_status in ('present','late','absent','excused','make_up')),
 sheet_version integer not null check(sheet_version>0),actor_id uuid not null references auth.users(id),created_at timestamptz not null,
 unique(session_id,enrollment_id,sheet_version),foreign key(workspace_id,batch_id,session_id,enrollment_id,child_id)
 references public.attendance_records(workspace_id,batch_id,session_id,enrollment_id,child_id));
create table public.attendance_request_receipts(
 request_id uuid primary key,actor_id uuid not null references auth.users(id),canonical_payload jsonb not null check(jsonb_typeof(canonical_payload)='object'),
 workspace_id uuid not null,batch_id uuid not null,session_id uuid not null,
 result_version integer not null check(result_version>0),result_session_version integer not null check(result_session_version>0),
 result_roster_token text not null check(result_roster_token ~ '^[0-9a-f]{64}$'),result_saved_at timestamptz not null,result_record_count integer not null check(result_record_count between 1 and 200),
 foreign key(workspace_id,batch_id,session_id) references public.attendance_sheets(workspace_id,batch_id,session_id));
create table public.parent_signals(
 id uuid primary key default gen_random_uuid(),workspace_id uuid not null,batch_id uuid not null,session_id uuid not null,enrollment_id uuid not null,child_id uuid not null,
 actor_id uuid not null references auth.users(id),type text not null check(type in ('running_late','missing_today','dropped_off','picked_up')),
 reason text,created_at timestamptz not null default clock_timestamp(),
 check((type='missing_today' and reason is not null and reason in ('unwell','travelling','other')) or (type<>'missing_today' and reason is null)),
 unique(workspace_id,batch_id,session_id,child_id,id),
 foreign key(workspace_id,batch_id,session_id) references public.schedule_sessions(workspace_id,batch_id,id),
 foreign key(workspace_id,batch_id,child_id,enrollment_id) references public.enrollments(workspace_id,batch_id,child_id,id));
create table public.parent_signal_request_receipts(
 request_id uuid primary key,actor_id uuid not null references auth.users(id),canonical_payload jsonb not null check(jsonb_typeof(canonical_payload)='object'),
 signal_id uuid not null unique references public.parent_signals(id),workspace_id uuid not null,batch_id uuid not null,session_id uuid not null,child_id uuid not null,
 result_created_at timestamptz not null,
 foreign key(workspace_id,batch_id,session_id,child_id,signal_id) references public.parent_signals(workspace_id,batch_id,session_id,child_id,id));
create table public.parent_items(
 id uuid primary key default gen_random_uuid(),workspace_id uuid not null,batch_id uuid not null,child_id uuid not null,enrollment_id uuid not null,source_session_id uuid not null,
 type text not null check(length(btrim(type)) between 1 and 80),schema_version integer not null check(schema_version>0),
 priority smallint not null default 0 check(priority between 0 and 100),created_at timestamptz not null,updated_at timestamptz not null,expires_at timestamptz,
 payload jsonb not null check(jsonb_typeof(payload)='object' and octet_length(payload::text)<=16384),
 audience_policy text not null default 'child_guardian' check(audience_policy='child_guardian'),
 unique(workspace_id,child_id,type,source_session_id),
 foreign key(workspace_id,batch_id,source_session_id) references public.schedule_sessions(workspace_id,batch_id,id),
 foreign key(workspace_id,batch_id,child_id,enrollment_id) references public.enrollments(workspace_id,batch_id,child_id,id));
create index attendance_sessions_workspace_page on public.schedule_sessions(workspace_id,starts_at,id);
create index attendance_sessions_batch_page on public.schedule_sessions(workspace_id,batch_id,starts_at,id);
create index attendance_active_enrollments on public.enrollments(workspace_id,batch_id,id) where status='active';
create index attendance_records_child_time on public.attendance_records(child_id,confirmed_at desc,session_id);
create index attendance_events_sheet on public.attendance_record_events(session_id,sheet_version,enrollment_id);
create index parent_signals_latest on public.parent_signals(session_id,child_id,actor_id,created_at desc,id desc);
create index parent_items_page on public.parent_items(child_id,created_at desc,id desc);
alter table public.attendance_sheets enable row level security;
revoke all on public.attendance_sheets from public,anon,authenticated;
alter table public.attendance_records enable row level security;
revoke all on public.attendance_records from public,anon,authenticated;
alter table public.attendance_record_events enable row level security;
revoke all on public.attendance_record_events from public,anon,authenticated;
alter table public.attendance_request_receipts enable row level security;
revoke all on public.attendance_request_receipts from public,anon,authenticated;
alter table public.parent_signals enable row level security;
revoke all on public.parent_signals from public,anon,authenticated;
alter table public.parent_signal_request_receipts enable row level security;
revoke all on public.parent_signal_request_receipts from public,anon,authenticated;
alter table public.parent_items enable row level security;
revoke all on public.parent_items from public,anon,authenticated;
-- Private helpers run under the calling definer, never as a standalone client API.
create function public.attendance_clock() returns timestamptz language sql volatile set search_path='' as $$ select pg_catalog.clock_timestamp() $$;
create function public.attendance_read_committed() returns void language plpgsql set search_path='' as $$
begin if current_setting('transaction_isolation')<>'read committed' then raise exception using errcode='25001',message='Read committed required'; end if; end $$;
create function public.attendance_zone(p_workspace uuid) returns text language plpgsql set search_path='' as $$
declare z text;
begin
 select scheduling_time_zone into z from public.workspaces where id=p_workspace;
 if z is null or not exists(select 1 from pg_catalog.pg_timezone_names where name=z) then raise exception using errcode='22023',message='Academy time zone unavailable'; end if;
 return z;
end $$;
create function public.attendance_zone(p_workspace uuid,p_date date) returns text language plpgsql set search_path='' as $$
declare z text:=public.attendance_zone(p_workspace);
begin
 if p_date is null or not isfinite(p_date) or p_date<'2000-01-01'::date or p_date>'2100-12-31'::date then raise exception using errcode='22023',message='Invalid local date'; end if;
 return z;
end $$;
create function public.attendance_staff(p_workspace uuid,p_batch uuid default null,p_update boolean default false) returns void language plpgsql set search_path='' as $$
declare m uuid;r text;
begin
 if auth.uid() is null then raise exception using errcode='42501',message='Attendance access denied'; end if;
 perform 1 from public.workspaces where id=p_workspace and status='active' for share;
 if not found then raise exception using errcode='42501',message='Attendance access denied'; end if;
 select id,role into m,r from public.workspace_memberships where workspace_id=p_workspace and user_id=auth.uid() and status='active' for share;
 if not found or r not in ('owner','admin','coach') then raise exception using errcode='42501',message='Attendance access denied'; end if;
 if p_batch is not null then
  if p_update then perform 1 from public.batches where workspace_id=p_workspace and id=p_batch for update;
  else perform 1 from public.batches where workspace_id=p_workspace and id=p_batch for share; end if;
  if not found then raise exception using errcode='42501',message='Attendance batch unavailable'; end if;
  if r='coach' then perform 1 from public.batch_coach_assignments where workspace_id=p_workspace and batch_id=p_batch and membership_id=m for share;
   if not found then raise exception using errcode='42501',message='Attendance access denied'; end if;
  end if;
 end if;
end $$;
create function public.attendance_parent(p_child uuid,p_workspace uuid default null,p_batch uuid default null,p_session uuid default null) returns void language plpgsql set search_path='' as $$
begin
 if auth.uid() is null then raise exception using errcode='42501',message='Parent access denied'; end if;
 if p_workspace is not null then
  perform 1 from public.workspaces where id=p_workspace and status='active' for share;
  if not found then raise exception using errcode='42501',message='Parent access denied'; end if;
 end if;
 if p_batch is not null then
  perform 1 from public.batches where id=p_batch and workspace_id=p_workspace for share;
  if not found then raise exception using errcode='42501',message='Parent access denied'; end if;
 end if;
 if p_session is not null then
  perform 1 from public.schedule_sessions where id=p_session and workspace_id=p_workspace and batch_id=p_batch for share;
  if not found then raise exception using errcode='42501',message='Parent access denied'; end if;
 end if;
 perform 1 from public.children where id=p_child and created_by=auth.uid() for share;
 if not found then raise exception using errcode='42501',message='Parent access denied'; end if;
 perform 1 from public.guardianships where child_id=p_child and guardian_user_id=auth.uid() and status in ('provisional','active') for share;
 if not found then raise exception using errcode='42501',message='Parent access denied'; end if;
 if p_workspace is not null then
  perform 1 from public.workspace_children where workspace_id=p_workspace and child_id=p_child and status='active' for share;
  if not found then raise exception using errcode='42501',message='Parent access denied'; end if;
  if p_batch is not null then
   perform 1 from public.enrollments where workspace_id=p_workspace and batch_id=p_batch and child_id=p_child for share;
  else perform 1 from public.enrollments where workspace_id=p_workspace and child_id=p_child order by id limit 1 for share; end if;
  if not found then raise exception using errcode='42501',message='Parent enrollment unavailable'; end if;
 end if;
end $$;
create function public.attendance_roster(p_workspace uuid,p_batch uuid,p_lock boolean default false) returns jsonb language plpgsql set search_path='' as $$
declare ids uuid[]; n integer; token text; rows jsonb;
begin
 select array_agg(id order by id),count(*) into ids,n from (select id from public.enrollments where workspace_id=p_workspace and batch_id=p_batch and status='active' order by id limit 201) e;
 if n>200 then return jsonb_build_object('too_large',true,'size',null,'token',null,'members','[]'::jsonb); end if;
 if p_lock then
  perform 1 from public.children c join public.enrollments e on e.child_id=c.id where e.id=any(ids) order by c.id for share of c;
  -- Lock inactive connections as well: reactivation must not create a phantom.
  perform 1 from public.workspace_children r join public.enrollments e on e.workspace_id=r.workspace_id and e.child_id=r.child_id where e.id=any(ids) order by r.child_id for share of r;
  perform 1 from public.enrollments where id=any(ids) order by id for share;
 end if;
 select coalesce(jsonb_agg(jsonb_build_object('enrollment_id',e.id,'child_id',e.child_id,'enrollment_version',e.version,'relationship_id',r.id) order by e.id),'[]'::jsonb)
 into rows from public.enrollments e join public.workspace_children r on r.workspace_id=e.workspace_id and r.child_id=e.child_id where e.id=any(ids) and e.status='active' and r.status='active';
 token:=encode(sha256(convert_to(rows::text,'UTF8')),'hex');
 return jsonb_build_object('too_large',false,'size',jsonb_array_length(rows),'token',token,'members',rows);
end $$;
create function public.attendance_payload(p jsonb) returns jsonb language plpgsql set search_path='' as $$
declare x jsonb; a jsonb; n integer;v1 integer;v2 integer;w uuid;s uuid;
begin
 if p is null or jsonb_typeof(p)<>'object' or octet_length(p::text)>65536 or (select count(*) from jsonb_object_keys(p))<>7 or not p ?& array['operation','workspace_id','session_id','expected_session_version','expected_sheet_version','roster_token','records'] or p->>'operation' is distinct from 'save_attendance' then raise exception using errcode='22023',message='Invalid attendance payload'; end if;
 if jsonb_typeof(p->'workspace_id')<>'string' or jsonb_typeof(p->'session_id')<>'string' or jsonb_typeof(p->'roster_token')<>'string' or (p->>'roster_token')!~'^[0-9a-f]{64}$' or jsonb_typeof(p->'expected_session_version')<>'number' or jsonb_typeof(p->'expected_sheet_version')<>'number' or (p->>'expected_session_version')!~'^[0-9]+$' or (p->>'expected_sheet_version')!~'^[0-9]+$' then raise exception using errcode='22023',message='Invalid attendance payload'; end if;
 w:=(p->>'workspace_id')::uuid;s:=(p->>'session_id')::uuid;v1:=(p->>'expected_session_version')::integer;v2:=(p->>'expected_sheet_version')::integer;
 if v1<1 or v2<0 or jsonb_typeof(p->'records')<>'array' then raise exception using errcode='22023',message='Invalid attendance payload'; end if;
 n:=jsonb_array_length(p->'records'); if n<1 or n>200 then raise exception using errcode='22023',message='Invalid attendance records'; end if;
 for x in select value from jsonb_array_elements(p->'records') loop
  if jsonb_typeof(x)<>'object' or (select count(*) from jsonb_object_keys(x))<>3 or not x ?& array['enrollment_id','child_id','status'] or jsonb_typeof(x->'enrollment_id')<>'string' or jsonb_typeof(x->'child_id')<>'string' or jsonb_typeof(x->'status')<>'string' or x->>'status' not in ('present','late','absent','excused','make_up') then raise exception using errcode='22023',message='Invalid attendance record'; end if;
 end loop;
 select jsonb_agg(jsonb_build_object('enrollment_id',(value->>'enrollment_id')::uuid,'child_id',(value->>'child_id')::uuid,'status',value->>'status') order by (value->>'enrollment_id')::uuid) into a from jsonb_array_elements(p->'records');
 if (select count(distinct value->>'enrollment_id') from jsonb_array_elements(a))<>n or (select count(distinct value->>'child_id') from jsonb_array_elements(a))<>n then raise exception using errcode='22023',message='Duplicate attendance record'; end if;
 return jsonb_build_object('operation','save_attendance','workspace_id',w,'session_id',s,'expected_session_version',v1,'expected_sheet_version',v2,'roster_token',p->>'roster_token','records',a);
exception when invalid_text_representation or numeric_value_out_of_range then raise exception using errcode='22023',message='Invalid attendance payload';
end $$;
-- Lock current and historical request members in one global resource order.
create function public.attendance_save_roster_locks(p_workspace uuid,p_batch uuid,p_records jsonb) returns void language plpgsql set search_path='' as $$
declare ids uuid[];v_child_ids uuid[];n integer;
begin
 select array_agg(id),count(*) into ids,n from (select id from public.enrollments where workspace_id=p_workspace and batch_id=p_batch and status='active' order by id limit 201) q;
 if n>200 then ids:='{}'::uuid[]; end if;
 select array_agg(distinct id) into ids from (select unnest(ids) id union select (value->>'enrollment_id')::uuid from jsonb_array_elements(p_records)) q;
 select array_agg(distinct id) into v_child_ids from (select child_id id from public.enrollments where id=any(ids) union select (value->>'child_id')::uuid from jsonb_array_elements(p_records)) q;
 perform 1 from public.children where id=any(v_child_ids) order by id for share;
 perform 1 from public.workspace_children where workspace_id=p_workspace and child_id=any(v_child_ids) order by child_id for share;
 perform 1 from public.enrollments where id=any(ids) order by id for share;
end $$;
create function public.attendance_payload_access(p jsonb,p_batch uuid) returns void language plpgsql set search_path='' as $$
declare x jsonb;w uuid:=(p->>'workspace_id')::uuid;
begin
 for x in select value from jsonb_array_elements(p->'records') order by (value->>'child_id')::uuid loop
  perform 1 from public.children where id=(x->>'child_id')::uuid for share;
  if not found then raise exception using errcode='42501',message='Attendance child unavailable'; end if;
 end loop;
 for x in select value from jsonb_array_elements(p->'records') order by (value->>'child_id')::uuid loop
  perform 1 from public.workspace_children where workspace_id=w and child_id=(x->>'child_id')::uuid and status='active' for share;
  if not found then raise exception using errcode='42501',message='Attendance connection unavailable'; end if;
 end loop;
 for x in select value from jsonb_array_elements(p->'records') order by (value->>'enrollment_id')::uuid loop
  perform 1 from public.enrollments where workspace_id=w and batch_id=p_batch and id=(x->>'enrollment_id')::uuid and child_id=(x->>'child_id')::uuid for share;
  if not found then raise exception using errcode='42501',message='Attendance enrollment unavailable'; end if;
 end loop;
end $$;
create function public.attendance_session_json(p_session uuid,p_roster jsonb default null) returns jsonb language plpgsql set search_path='' as $$
declare s public.schedule_sessions%rowtype;h public.attendance_sheets%rowtype;r jsonb;b text;c text;n integer;
begin
 select * into s from public.schedule_sessions where id=p_session;
 perform public.attendance_staff(s.workspace_id,s.batch_id,false);
 select * into s from public.schedule_sessions where id=p_session for share;
 select * into h from public.attendance_sheets where session_id=p_session;
 r:=coalesce(p_roster,public.attendance_roster(s.workspace_id,s.batch_id,false));
 select bb.name,cc.name into b,c from public.batches bb join public.courses cc on cc.id=bb.course_id where bb.id=s.batch_id;
 select count(*) into n from public.attendance_records a join jsonb_array_elements(r->'members') m on a.enrollment_id=(m->>'enrollment_id')::uuid and a.child_id=(m->>'child_id')::uuid where a.session_id=s.id;
 return jsonb_build_object('id',s.id,'batch_id',s.batch_id,'batch_name',b,'course_name',c,'starts_at',s.starts_at,'ends_at',s.ends_at,'status',s.status,'version',s.version,'sheet_version',coalesce(h.version,0),'roster_size',r->'size','roster_too_large',r->'too_large','marked_count',n,'attendance_current',coalesce(h.session_version=s.version and h.roster_token=r->>'token',false));
end $$;
create function public.attendance_receipt(r public.attendance_request_receipts) returns jsonb language sql set search_path='' as $$
 select jsonb_build_object('request_id',r.request_id,'session_id',r.session_id,'sheet_version',r.result_version,'session_version',r.result_session_version,'roster_token',r.result_roster_token,'saved_at',r.result_saved_at,'record_count',r.result_record_count) $$;
create function public.app_attendance_sheet(p_workspace_id uuid,p_session_id uuid) returns jsonb language plpgsql security definer set search_path='' set timezone='UTC' as $$
declare s public.schedule_sessions%rowtype;h public.attendance_sheets%rowtype;r jsonb;rows jsonb;z text;
begin
 select * into s from public.schedule_sessions where id=p_session_id and workspace_id=p_workspace_id;
 if not found then raise exception using errcode='42501',message='Attendance session unavailable'; end if;
 perform public.attendance_staff(p_workspace_id,s.batch_id,true);
 select * into s from public.schedule_sessions where id=p_session_id for share;
 z:=public.attendance_zone(p_workspace_id);
 perform public.attendance_zone(p_workspace_id,(s.starts_at at time zone z)::date);
 r:=public.attendance_roster(p_workspace_id,s.batch_id,true);
 select * into h from public.attendance_sheets where session_id=s.id for update;
 select coalesce(jsonb_agg(jsonb_build_object('enrollment_id',m->'enrollment_id','enrollment_version',m->'enrollment_version','child_id',m->'child_id','child_name',c.display_name,'status',a.status,'confirmed_at',a.confirmed_at) order by (m->>'enrollment_id')::uuid),'[]'::jsonb)
 into rows from jsonb_array_elements(r->'members') m join public.children c on c.id=(m->>'child_id')::uuid left join public.attendance_records a on a.session_id=s.id and a.enrollment_id=(m->>'enrollment_id')::uuid;
 return jsonb_build_object('session',public.attendance_session_json(s.id,r),'time_zone',z,'server_now',clock_timestamp(),'sheet_version',coalesce(h.version,0),'saved_at',h.saved_at,'saved_roster_token',h.roster_token,'roster_token',r->'token','roster_too_large',r->'too_large','rows',rows);
end $$;
create function public.app_save_attendance(p_workspace_id uuid,p_session_id uuid,p_expected_session_version integer,p_expected_sheet_version integer,p_roster_token text,p_records jsonb,p_request_id uuid) returns jsonb language plpgsql security definer set search_path='' set timezone='UTC' as $$
declare p jsonb;s public.schedule_sessions%rowtype;h public.attendance_sheets%rowtype;q public.attendance_request_receipts%rowtype;r jsonb;x jsonb;old_status text;v integer;t timestamptz;z text;
begin
 perform public.attendance_read_committed();
 p:=public.attendance_payload(jsonb_build_object('operation','save_attendance','workspace_id',p_workspace_id,'session_id',p_session_id,'expected_session_version',p_expected_session_version,'expected_sheet_version',p_expected_sheet_version,'roster_token',p_roster_token,'records',p_records));
 if p_request_id is null then raise exception using errcode='22023',message='Request required'; end if;
 select * into s from public.schedule_sessions where id=p_session_id and workspace_id=p_workspace_id;
 if not found then raise exception using errcode='42501',message='Attendance session unavailable'; end if;
 perform public.attendance_staff(p_workspace_id,s.batch_id,true);
 select * into s from public.schedule_sessions where id=p_session_id for share;
 -- Current roster locks include every bounded candidate, including hidden links.
 perform public.attendance_save_roster_locks(p_workspace_id,s.batch_id,p->'records');
 r:=public.attendance_roster(p_workspace_id,s.batch_id,true);
 perform public.attendance_payload_access(p,s.batch_id);
 perform pg_advisory_xact_lock(hashtextextended('attendance-request:'||p_request_id::text,0));
 select * into q from public.attendance_request_receipts where request_id=p_request_id;
 if found then
  if q.actor_id is distinct from auth.uid() or q.canonical_payload is distinct from p then raise exception using errcode='23505',message='Attendance request details changed'; end if;
  return public.attendance_receipt(q);
 end if;
 select * into h from public.attendance_sheets where session_id=s.id for update;
 if s.status<>'scheduled' or s.version<>p_expected_session_version or coalesce(h.version,0)<>p_expected_sheet_version or (r->>'too_large')::boolean or r->>'token' is distinct from p_roster_token or jsonb_array_length(p_records)<>jsonb_array_length(r->'members') or exists(select 1 from jsonb_array_elements(p->'records') a where not exists(select 1 from jsonb_array_elements(r->'members') b where a->'enrollment_id'=b->'enrollment_id' and a->'child_id'=b->'child_id')) then raise exception using errcode='40001',message='Attendance version or roster changed'; end if;
 z:=public.attendance_zone(p_workspace_id);
 perform public.attendance_zone(p_workspace_id,(s.starts_at at time zone z)::date);t:=clock_timestamp();v:=coalesce(h.version,0)+1;
 insert into public.attendance_sheets values(s.id,p_workspace_id,s.batch_id,v,s.version,p_roster_token,jsonb_array_length(p_records),auth.uid(),t)
 on conflict(session_id) do update set version=excluded.version,session_version=excluded.session_version,roster_token=excluded.roster_token,roster_size=excluded.roster_size,saved_by=excluded.saved_by,saved_at=excluded.saved_at;
 for x in select value from jsonb_array_elements(p->'records') order by (value->>'enrollment_id')::uuid loop
  select status into old_status from public.attendance_records where session_id=s.id and enrollment_id=(x->>'enrollment_id')::uuid;
  insert into public.attendance_records(session_id,workspace_id,batch_id,enrollment_id,child_id,status,sheet_version,confirmed_by,confirmed_at)
  values(s.id,p_workspace_id,s.batch_id,(x->>'enrollment_id')::uuid,(x->>'child_id')::uuid,x->>'status',v,auth.uid(),t)
  on conflict(session_id,enrollment_id) do update set status=excluded.status,sheet_version=excluded.sheet_version,confirmed_by=excluded.confirmed_by,confirmed_at=excluded.confirmed_at;
  insert into public.attendance_record_events(workspace_id,batch_id,session_id,enrollment_id,child_id,status,from_status,sheet_version,actor_id,created_at)
  values(p_workspace_id,s.batch_id,s.id,(x->>'enrollment_id')::uuid,(x->>'child_id')::uuid,x->>'status',old_status,v,auth.uid(),t);
  insert into public.parent_items(workspace_id,batch_id,child_id,enrollment_id,source_session_id,type,schema_version,created_at,updated_at,payload)
  values(p_workspace_id,s.batch_id,(x->>'child_id')::uuid,(x->>'enrollment_id')::uuid,s.id,'attendance',1,t,t,jsonb_build_object('session_id',s.id,'date',(s.starts_at at time zone z)::date,'status',x->>'status','confirmed_at',t,'title','Attendance recorded','body',(x->>'status')||' on '||((s.starts_at at time zone z)::date)::text))
  on conflict(workspace_id,child_id,type,source_session_id) do update set payload=excluded.payload,updated_at=excluded.updated_at;
 end loop;
 insert into public.attendance_request_receipts values(p_request_id,auth.uid(),p,p_workspace_id,s.batch_id,s.id,v,s.version,p_roster_token,t,jsonb_array_length(p_records)) returning * into q;
 return public.attendance_receipt(q);
end $$;
create function public.app_attendance_request_status(p_workspace_id uuid,p_session_id uuid,p_request_id uuid,p_payload jsonb) returns jsonb language plpgsql security definer set search_path='' set timezone='UTC' as $$
declare p jsonb;s public.schedule_sessions%rowtype;q public.attendance_request_receipts%rowtype;
begin
 perform public.attendance_read_committed();p:=public.attendance_payload(p_payload);
 if p_request_id is null or (p->>'workspace_id')::uuid is distinct from p_workspace_id or (p->>'session_id')::uuid is distinct from p_session_id then raise exception using errcode='22023',message='Invalid status scope'; end if;
 select * into s from public.schedule_sessions where id=p_session_id and workspace_id=p_workspace_id;
 if not found then raise exception using errcode='42501',message='Attendance session unavailable'; end if;
 perform public.attendance_staff(p_workspace_id,s.batch_id,true);
 perform 1 from public.schedule_sessions where id=p_session_id for share;
 perform public.attendance_payload_access(p,s.batch_id);
 perform pg_advisory_xact_lock(hashtextextended('attendance-request:'||p_request_id::text,0));
 select * into q from public.attendance_request_receipts where request_id=p_request_id;
 if not found then return jsonb_build_object('state','unknown','receipt',null); end if;
 if q.actor_id is distinct from auth.uid() or q.canonical_payload is distinct from p then raise exception using errcode='23505',message='Attendance request details changed'; end if;
 return jsonb_build_object('state','known','receipt',public.attendance_receipt(q));
end $$;
create function public.app_today_academies(p_after uuid default null) returns jsonb language plpgsql security definer set search_path='' set timezone='UTC' as $$
declare rows jsonb;next_id uuid;
begin
 if auth.uid() is null then raise exception using errcode='42501',message='Today access denied'; end if;
 with page as (select w.id,w.name,w.scheduling_time_zone from public.workspaces w join public.workspace_memberships m on m.workspace_id=w.id where w.status='active' and m.user_id=auth.uid() and m.status='active' and m.role in ('owner','admin','coach') and (p_after is null or w.id>p_after) order by w.id limit 51 for share of w,m), numbered as(select *,row_number() over(order by id) n from page)
 select coalesce(jsonb_agg(jsonb_build_object('workspace_id',id,'name',name,'time_zone',scheduling_time_zone) order by id) filter(where n<=50),'[]'::jsonb),case when count(*)>50 then (array_agg(id order by id))[50] else null end into rows,next_id from numbered;
 return jsonb_build_object('academies',rows,'next_after',next_id);
end $$;
create function public.app_today_sessions(p_workspace_id uuid,p_date date,p_after_start timestamptz default null,p_after_id uuid default null) returns jsonb language plpgsql security definer set search_path='' set timezone='UTC' as $$
declare z text;rows jsonb;nxt jsonb;
begin
 perform public.attendance_staff(p_workspace_id);z:=public.attendance_zone(p_workspace_id,p_date);
 if (p_after_start is null)<>(p_after_id is null) or (p_after_start is not null and not isfinite(p_after_start)) then raise exception using errcode='22023',message='Invalid session cursor'; end if;
 with page as(select s.* from public.schedule_sessions s join public.workspace_memberships m on m.workspace_id=s.workspace_id and m.user_id=auth.uid() and m.status='active' where s.workspace_id=p_workspace_id and (m.role in ('owner','admin') or (m.role='coach' and exists(select 1 from public.batch_coach_assignments a where a.workspace_id=s.workspace_id and a.batch_id=s.batch_id and a.membership_id=m.id))) and s.starts_at>=p_date::timestamp at time zone z and s.starts_at<(p_date+1)::timestamp at time zone z and (p_after_start is null or (s.starts_at,s.id)>(p_after_start,p_after_id)) order by s.starts_at,s.id limit 51), numbered as(select *,row_number() over(order by starts_at,id) n from page)
 select coalesce(jsonb_agg(public.attendance_session_json(id) order by starts_at,id) filter(where n<=50),'[]'::jsonb),case when count(*)>50 then (jsonb_agg(jsonb_build_object('starts_at',starts_at,'id',id) order by starts_at,id)->49) else null end into rows,nxt from numbered;
 return jsonb_build_object('date',p_date,'time_zone',z,'server_now',clock_timestamp(),'sessions',rows,'next',nxt);
end $$;
create function public.app_parent_academies(p_child_id uuid,p_after uuid default null) returns jsonb language plpgsql security definer set search_path='' set timezone='UTC' as $$
declare rows jsonb;nxt uuid;
begin
 perform public.attendance_parent(p_child_id);
 with page as(select w.id,w.name,w.scheduling_time_zone from public.workspaces w join public.workspace_children r on r.workspace_id=w.id and r.child_id=p_child_id and r.status='active' where w.status='active' and exists(select 1 from public.enrollments e where e.child_id=p_child_id and e.workspace_id=w.id) and (p_after is null or w.id>p_after) order by w.id limit 51 for share of w,r), numbered as(select *,row_number() over(order by id) n from page)
 select coalesce(jsonb_agg(jsonb_build_object('workspace_id',id,'name',name,'time_zone',scheduling_time_zone) order by id) filter(where n<=50),'[]'::jsonb),case when count(*)>50 then (array_agg(id order by id))[50] else null end into rows,nxt from numbered;
 return jsonb_build_object('academies',rows,'next_after',nxt);
end $$;
create function public.app_parent_batches(p_child_id uuid,p_workspace_id uuid,p_after uuid default null) returns jsonb language plpgsql security definer set search_path='' set timezone='UTC' as $$
declare rows jsonb;nxt uuid;
begin
 perform public.attendance_parent(p_child_id,p_workspace_id);
 with page as(select b.id,b.name,c.name course_name,e.id enrollment_id,e.status from public.enrollments e join public.batches b on b.id=e.batch_id and b.workspace_id=e.workspace_id join public.courses c on c.id=b.course_id where e.workspace_id=p_workspace_id and e.child_id=p_child_id and (p_after is null or b.id>p_after) order by b.id limit 51 for share of b,c,e), numbered as(select *,row_number() over(order by id) n from page)
 select coalesce(jsonb_agg(jsonb_build_object('batch_id',id,'batch_name',name,'course_name',course_name,'enrollment_id',enrollment_id,'enrollment_status',status) order by id) filter(where n<=50),'[]'::jsonb),case when count(*)>50 then (array_agg(id order by id))[50] else null end into rows,nxt from numbered;
 return jsonb_build_object('batches',rows,'next_after',nxt);
end $$;
create function public.parent_signal_payload(p jsonb) returns jsonb language plpgsql set search_path='' as $$
declare v integer;w uuid;s uuid;c uuid;k text;r text;
begin
 if p is null or jsonb_typeof(p)<>'object' or octet_length(p::text)>65536 or (select count(*) from jsonb_object_keys(p))<>7 or not p ?& array['operation','workspace_id','session_id','child_id','expected_session_version','type','reason'] or p->>'operation' is distinct from 'send_parent_signal' or jsonb_typeof(p->'workspace_id')<>'string' or jsonb_typeof(p->'session_id')<>'string' or jsonb_typeof(p->'child_id')<>'string' or jsonb_typeof(p->'expected_session_version')<>'number' or (p->>'expected_session_version')!~'^[0-9]+$' or jsonb_typeof(p->'type')<>'string' then raise exception using errcode='22023',message='Invalid signal payload'; end if;
 w:=(p->>'workspace_id')::uuid;s:=(p->>'session_id')::uuid;c:=(p->>'child_id')::uuid;v:=(p->>'expected_session_version')::integer;k:=p->>'type';r:=p->>'reason';
 if v<1 or k not in ('running_late','missing_today','dropped_off','picked_up') or (k='missing_today' and (jsonb_typeof(p->'reason')<>'string' or r not in ('unwell','travelling','other'))) or (k<>'missing_today' and jsonb_typeof(p->'reason')<>'null') then raise exception using errcode='22023',message='Invalid signal details'; end if;
 return jsonb_build_object('operation','send_parent_signal','child_id',c,'workspace_id',w,'session_id',s,'expected_session_version',v,'type',k,'reason',r);
exception when invalid_text_representation or numeric_value_out_of_range then raise exception using errcode='22023',message='Invalid signal payload';
end $$;
create function public.parent_signal_json(s public.parent_signals) returns jsonb language sql set search_path='' as $$
 select jsonb_build_object('id',s.id,'child_id',s.child_id,'actor_id',s.actor_id,'type',s.type,'reason',s.reason,'created_at',s.created_at) $$;
create function public.parent_signal_receipt(q public.parent_signal_request_receipts) returns jsonb language sql set search_path='' as $$
 select jsonb_build_object('request_id',q.request_id,'signal_id',q.signal_id,'session_id',q.session_id,'child_id',q.child_id,'type',q.canonical_payload->'type','reason',q.canonical_payload->'reason','created_at',q.result_created_at) $$;
create function public.app_send_parent_signal(p_child_id uuid,p_workspace_id uuid,p_session_id uuid,p_expected_session_version integer,p_type text,p_reason text,p_request_id uuid) returns jsonb language plpgsql security definer set search_path='' set timezone='UTC' as $$
declare p jsonb;s public.schedule_sessions%rowtype;e public.enrollments%rowtype;q public.parent_signal_request_receipts%rowtype;v public.parent_signals%rowtype;z text;
begin
 perform public.attendance_read_committed();p:=public.parent_signal_payload(jsonb_build_object('operation','send_parent_signal','child_id',p_child_id,'workspace_id',p_workspace_id,'session_id',p_session_id,'expected_session_version',p_expected_session_version,'type',p_type,'reason',p_reason));
 if p_request_id is null then raise exception using errcode='22023',message='Request required'; end if;
 select * into s from public.schedule_sessions where id=p_session_id and workspace_id=p_workspace_id;
 if not found then raise exception using errcode='42501',message='Signal session unavailable'; end if;
 perform public.attendance_parent(p_child_id,p_workspace_id,s.batch_id,s.id);
 perform pg_advisory_xact_lock(hashtextextended('parent-signal-request:'||p_request_id::text,0));
 perform pg_advisory_xact_lock(hashtextextended('parent-signal:'||s.id::text||':'||p_child_id::text||':'||auth.uid()::text,0));
 select * into q from public.parent_signal_request_receipts where request_id=p_request_id;
 if found then
  if q.actor_id is distinct from auth.uid() or q.canonical_payload is distinct from p then raise exception using errcode='23505',message='Signal request details changed'; end if;
  return public.parent_signal_receipt(q);
 end if;
 select * into s from public.schedule_sessions where id=p_session_id;
 select * into e from public.enrollments where workspace_id=p_workspace_id and batch_id=s.batch_id and child_id=p_child_id;
 z:=public.attendance_zone(p_workspace_id);
 perform public.attendance_zone(p_workspace_id,(s.starts_at at time zone z)::date);
 if s.status<>'scheduled' or s.version<>p_expected_session_version or e.status<>'active' or (s.starts_at at time zone z)::date<>(public.attendance_clock() at time zone z)::date then raise exception using errcode='40001',message='Signal session version or local day changed'; end if;
 insert into public.parent_signals(workspace_id,batch_id,session_id,enrollment_id,child_id,actor_id,type,reason) values(p_workspace_id,s.batch_id,s.id,e.id,p_child_id,auth.uid(),p_type,p_reason) returning * into v;
 insert into public.parent_signal_request_receipts values(p_request_id,auth.uid(),p,v.id,p_workspace_id,s.batch_id,s.id,p_child_id,v.created_at) returning * into q;
 return public.parent_signal_receipt(q);
end $$;
create function public.app_parent_signal_request_status(p_child_id uuid,p_workspace_id uuid,p_session_id uuid,p_request_id uuid,p_payload jsonb) returns jsonb language plpgsql security definer set search_path='' set timezone='UTC' as $$
declare p jsonb;s public.schedule_sessions%rowtype;q public.parent_signal_request_receipts%rowtype;
begin
 perform public.attendance_read_committed();p:=public.parent_signal_payload(p_payload);
 if p_request_id is null or (p->>'workspace_id')::uuid is distinct from p_workspace_id or (p->>'session_id')::uuid is distinct from p_session_id or (p->>'child_id')::uuid is distinct from p_child_id then raise exception using errcode='22023',message='Invalid signal status scope'; end if;
 select * into s from public.schedule_sessions where id=p_session_id and workspace_id=p_workspace_id;
 if not found then raise exception using errcode='42501',message='Signal session unavailable'; end if;
 perform public.attendance_parent(p_child_id,p_workspace_id,s.batch_id,s.id);
 perform pg_advisory_xact_lock(hashtextextended('parent-signal-request:'||p_request_id::text,0));
 perform pg_advisory_xact_lock(hashtextextended('parent-signal:'||s.id::text||':'||p_child_id::text||':'||auth.uid()::text,0));
 select * into q from public.parent_signal_request_receipts where request_id=p_request_id;
 if not found then return jsonb_build_object('state','unknown','receipt',null); end if;
 if q.actor_id is distinct from auth.uid() or q.canonical_payload is distinct from p then raise exception using errcode='23505',message='Signal request details changed'; end if;
 return jsonb_build_object('state','known','receipt',public.parent_signal_receipt(q));
end $$;
create function public.app_session_parent_signals(p_workspace_id uuid,p_session_id uuid,p_after_child uuid default null,p_after_actor uuid default null) returns jsonb language plpgsql security definer set search_path='' set timezone='UTC' as $$
declare b uuid;rows jsonb;nxt jsonb;
begin
 if (p_after_child is null)<>(p_after_actor is null) then raise exception using errcode='22023',message='Invalid signal cursor'; end if;
 select batch_id into b from public.schedule_sessions where id=p_session_id and workspace_id=p_workspace_id;
 if not found then raise exception using errcode='42501',message='Signal session unavailable'; end if;
 perform public.attendance_staff(p_workspace_id,b);
 perform 1 from public.schedule_sessions where id=p_session_id for share;
 with latest as(select distinct on(s.child_id,s.actor_id) s.* from public.parent_signals s join public.enrollments e on e.id=s.enrollment_id and e.status='active' join public.workspace_children r on r.workspace_id=s.workspace_id and r.child_id=s.child_id and r.status='active' join public.children c on c.id=s.child_id and c.created_by=s.actor_id join public.guardianships g on g.child_id=s.child_id and g.guardian_user_id=s.actor_id and g.status in ('provisional','active') where s.session_id=p_session_id and (p_after_child is null or (s.child_id,s.actor_id)>(p_after_child,p_after_actor)) order by s.child_id,s.actor_id,s.created_at desc,s.id desc), page as(select *,row_number() over(order by child_id,actor_id) n from (select * from latest order by child_id,actor_id limit 51) p)
 select coalesce(jsonb_agg(jsonb_build_object('id',id,'child_id',child_id,'actor_id',actor_id,'type',type,'reason',reason,'created_at',created_at) order by child_id,actor_id) filter(where n<=50),'[]'::jsonb),case when count(*)>50 then (jsonb_agg(jsonb_build_object('child_id',child_id,'actor_id',actor_id) order by child_id,actor_id)->49) else null end into rows,nxt from page;
 return jsonb_build_object('signals',rows,'next',nxt,'server_now',clock_timestamp());
end $$;
create function public.app_parent_sessions(p_child_id uuid,p_workspace_id uuid,p_date date,p_batch_id uuid default null,p_after_start timestamptz default null,p_after_id uuid default null) returns jsonb language plpgsql security definer set search_path='' set timezone='UTC' as $$
declare z text;rows jsonb;nxt jsonb;
begin
 perform public.attendance_parent(p_child_id,p_workspace_id,p_batch_id);z:=public.attendance_zone(p_workspace_id,p_date);
 if (p_after_start is null)<>(p_after_id is null) or (p_after_start is not null and not isfinite(p_after_start)) then raise exception using errcode='22023',message='Invalid session cursor'; end if;
 with page as(select s.*,b.name batch_name,c.name course_name,e.id enrollment_id,e.status enrollment_status from public.schedule_sessions s join public.batches b on b.id=s.batch_id join public.courses c on c.id=b.course_id join public.enrollments e on e.batch_id=s.batch_id and e.workspace_id=s.workspace_id and e.child_id=p_child_id where s.workspace_id=p_workspace_id and (p_batch_id is null or s.batch_id=p_batch_id) and s.starts_at>=p_date::timestamp at time zone z and s.starts_at<(p_date+1)::timestamp at time zone z and (p_after_start is null or (s.starts_at,s.id)>(p_after_start,p_after_id)) order by s.starts_at,s.id limit 51), numbered as(select *,row_number() over(order by starts_at,id) n from page)
 select coalesce(jsonb_agg(jsonb_build_object('id',s.id,'batch_id',s.batch_id,'batch_name',s.batch_name,'course_name',s.course_name,'starts_at',s.starts_at,'ends_at',s.ends_at,'status',s.status,'version',s.version,'enrollment_id',s.enrollment_id,'enrollment_status',s.enrollment_status,'attendance',(select jsonb_build_object('status',a.status,'confirmed_at',a.confirmed_at) from public.attendance_records a where a.session_id=s.id and a.enrollment_id=s.enrollment_id),'own_latest_signal',(select public.parent_signal_json(ps) from public.parent_signals ps where ps.session_id=s.id and ps.child_id=p_child_id and ps.actor_id=auth.uid() order by ps.created_at desc,ps.id desc limit 1),'can_signal',s.status='scheduled' and s.enrollment_status='active' and (s.starts_at at time zone z)::date=(public.attendance_clock() at time zone z)::date) order by s.starts_at,s.id) filter(where s.n<=50),'[]'::jsonb),case when count(*)>50 then jsonb_agg(jsonb_build_object('starts_at',s.starts_at,'id',s.id) order by s.starts_at,s.id)->49 else null end into rows,nxt from numbered s;
 return jsonb_build_object('date',p_date,'time_zone',z,'server_now',clock_timestamp(),'sessions',rows,'next',nxt);
end $$;
create function public.app_parent_items(p_child_id uuid,p_workspace_id uuid,p_batch_id uuid default null,p_before_created timestamptz default null,p_before_id uuid default null) returns jsonb language plpgsql security definer set search_path='' set timezone='UTC' as $$
declare rows jsonb;nxt jsonb;
begin
 perform public.attendance_parent(p_child_id,p_workspace_id,p_batch_id);
 if (p_before_created is null)<>(p_before_id is null) or (p_before_created is not null and not isfinite(p_before_created)) then raise exception using errcode='22023',message='Invalid item cursor'; end if;
 with page as(select i.* from public.parent_items i join public.enrollments e on e.id=i.enrollment_id and e.child_id=i.child_id and e.workspace_id=i.workspace_id and e.batch_id=i.batch_id where i.child_id=p_child_id and i.workspace_id=p_workspace_id and (p_batch_id is null or i.batch_id=p_batch_id) and (i.expires_at is null or i.expires_at>clock_timestamp()) and (p_before_created is null or (i.created_at,i.id)<(p_before_created,p_before_id)) order by i.created_at desc,i.id desc limit 51), numbered as(select *,row_number() over(order by created_at desc,id desc) n from page)
 select coalesce(jsonb_agg(jsonb_build_object('id',id,'type',type,'schema_version',schema_version,'child_id',child_id,'class_id',batch_id,'priority',priority,'created_at',created_at,'expires_at',expires_at,'payload',payload) order by created_at desc,id desc) filter(where n<=50),'[]'::jsonb),case when count(*)>50 then jsonb_agg(jsonb_build_object('created_at',created_at,'id',id) order by created_at desc,id desc)->49 else null end into rows,nxt from numbered;
 return jsonb_build_object('items',rows,'next',nxt);
end $$;
create function public.app_parent_attendance_week(p_child_id uuid,p_workspace_id uuid,p_week_start date,p_batch_id uuid default null) returns jsonb language plpgsql security definer set search_path='' set timezone='UTC' as $$
declare z text;rows jsonb;attended bigint;recorded bigint;
begin
 perform public.attendance_parent(p_child_id,p_workspace_id,p_batch_id);z:=public.attendance_zone(p_workspace_id,p_week_start);
 if extract(isodow from p_week_start)<>1 then raise exception using errcode='22023',message='Week must start Monday'; end if;
 with facts as(select a.session_id,a.batch_id,b.name batch_name,(s.starts_at at time zone z)::date date,a.status,a.confirmed_at,s.starts_at from public.attendance_records a join public.schedule_sessions s on s.id=a.session_id and s.workspace_id=a.workspace_id and s.batch_id=a.batch_id join public.batches b on b.id=a.batch_id join public.enrollments e on e.id=a.enrollment_id and e.child_id=p_child_id and e.workspace_id=p_workspace_id where a.child_id=p_child_id and a.workspace_id=p_workspace_id and (p_batch_id is null or a.batch_id=p_batch_id) and s.starts_at>=p_week_start::timestamp at time zone z and s.starts_at<(p_week_start+7)::timestamp at time zone z), numbered as(select *,row_number() over(order by starts_at,session_id) n from facts)
 select count(*) filter(where status in ('present','late','make_up')),count(*),coalesce(jsonb_agg(jsonb_build_object('session_id',session_id,'batch_id',batch_id,'batch_name',batch_name,'date',date,'status',status,'confirmed_at',confirmed_at) order by starts_at,session_id) filter(where n<=50),'[]'::jsonb) into attended,recorded,rows from numbered;
 return jsonb_build_object('week_start',p_week_start,'time_zone',z,'attended_count',attended,'recorded_count',recorded,'rows',rows,'has_more',recorded>50);
end $$;
-- Apply every ACL before the transaction becomes visible.
do $$ declare f record; begin
 for f in select p.oid,p.proname,pg_get_function_identity_arguments(p.oid) args from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname='public' and p.proname in ('attendance_session_lifecycle','attendance_clock','attendance_read_committed','attendance_zone','attendance_staff','attendance_parent','attendance_roster','attendance_payload','attendance_save_roster_locks','attendance_payload_access','attendance_session_json','attendance_receipt','app_attendance_sheet','app_save_attendance','app_attendance_request_status','app_today_academies','app_today_sessions','app_parent_academies','app_parent_batches','parent_signal_payload','parent_signal_json','parent_signal_receipt','app_send_parent_signal','app_parent_signal_request_status','app_session_parent_signals','app_parent_sessions','app_parent_items','app_parent_attendance_week') loop
 execute format('revoke all on function public.%I(%s) from public,anon,authenticated',f.proname,f.args);
 if f.proname like 'app_%' then execute format('grant execute on function public.%I(%s) to authenticated',f.proname,f.args); end if;
 end loop;
end $$;
commit;
