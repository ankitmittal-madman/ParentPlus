#!/usr/bin/env python3
"""Owned local rehearsal helper: synthetic storage plans, never provider timings."""
import hashlib
import json
import re


def storage_queries(source):
    markers={
        'sessions':('public.app_today_sessions(', 'with page as(', '), numbered as('),
        'roster':('public.attendance_roster(', 'from (', ') e;'),
        'latest_signals':('public.app_session_parent_signals(', 'with latest as(', '), page as('),
        'feed':('public.app_parent_items(', 'with page as(', '), numbered as('),
        'weekly':('public.app_parent_attendance_week(', 'with facts as(', '), numbered as('),
    }
    result={}
    for name,(function,start,end) in markers.items():
        # A source-shape change needs deliberate review, never a stale copied query.
        if source.count('create function '+function)!=1:
            raise ValueError('Attendance query shape changed: '+name)
        body=source.split('create function '+function,1)[1].split('end $$;',1)[0]
        if body.count(start)!=1 or end not in body.split(start,1)[1]:
            raise ValueError('Attendance query shape changed: '+name)
        result[name]=body.split(start,1)[1].split(end,1)[0]
    return result


def collect(sql, source, out, actor):
    """Only called after preservation assertions in an owned network-none PG17."""
    sql(f"""
create temp table perf_academies as select n,md5('perf-w-'||n)::uuid w,md5('perf-c-'||n)::uuid c,md5('perf-b-'||n)::uuid b from generate_series(1,8) n;
insert into public.workspaces(id,name,type,created_by,creation_request_id,scheduling_time_zone) select w,'Fictional Plan Academy '||n,'academy','{actor}',gen_random_uuid(),'UTC' from perf_academies;
insert into public.workspace_memberships(workspace_id,user_id,role,status) select w,'{actor}','owner','active' from perf_academies;
insert into public.courses(id,workspace_id,name) select c,w,'Fictional Plan Course' from perf_academies;
insert into public.batches(id,workspace_id,course_id,name) select b,w,c,'Fictional Plan Batch' from perf_academies;
create temp table perf_children as select a.*,g,md5('perf-child-'||n||'-'||g)::uuid child,md5('perf-enrol-'||n||'-'||g)::uuid enrol from perf_academies a cross join generate_series(1,100) g;
insert into public.children(id,display_name,created_by) select child,'Fictional Plan Child '||g,'{actor}' from perf_children;
insert into public.guardianships(child_id,guardian_user_id,status) select child,'{actor}','active' from perf_children;
insert into public.workspace_children(workspace_id,child_id,status) select w,child,'active' from perf_children;
insert into public.enrollments(id,workspace_id,batch_id,child_id,created_by) select enrol,w,b,child,'{actor}' from perf_children;
create temp table perf_sessions as select a.*,d,md5('perf-session-'||n||'-'||d)::uuid sess,'2026-11-01T10:00:00Z'::timestamptz+d*interval '1 day' start from perf_academies a cross join generate_series(0,59) d;
insert into public.schedule_sessions(id,workspace_id,batch_id,starts_at,ends_at,created_by,creation_request_id) select sess,w,b,start,start+interval '1 hour','{actor}',gen_random_uuid() from perf_sessions;
insert into public.attendance_sheets(session_id,workspace_id,batch_id,version,session_version,roster_token,roster_size,saved_by,saved_at) select sess,w,b,1,1,repeat('a',64),100,'{actor}',start from perf_sessions;
insert into public.attendance_records(session_id,workspace_id,batch_id,enrollment_id,child_id,status,sheet_version,confirmed_by,confirmed_at) select s.sess,s.w,s.b,c.enrol,c.child,'present',1,'{actor}',s.start from perf_sessions s join perf_children c on c.w=s.w;
insert into public.parent_items(workspace_id,batch_id,child_id,enrollment_id,source_session_id,type,schema_version,created_at,updated_at,payload) select s.w,s.b,c.child,c.enrol,s.sess,'attendance_record',1,s.start,s.start,'{{}}'::jsonb from perf_sessions s join perf_children c on c.w=s.w;
insert into public.parent_signals(workspace_id,batch_id,session_id,enrollment_id,child_id,actor_id,type,created_at) select s.w,s.b,s.sess,c.enrol,c.child,'{actor}','running_late',s.start+t*interval '1 second' from perf_sessions s join perf_children c on c.w=s.w cross join generate_series(1,2) t;
analyze;
""")
    scope=json.loads(sql("select json_build_object('workspace',workspace_id,'batch',batch_id,'session',id,'child',md5('perf-child-1-1')::uuid) from public.schedule_sessions where id=md5('perf-session-1-9')::uuid;"))
    values={
        'p_workspace_id':"'"+scope['workspace']+"'::uuid",'p_workspace':"'"+scope['workspace']+"'::uuid",
        'p_batch':"'"+scope['batch']+"'::uuid",'p_session_id':"'"+scope['session']+"'::uuid",
        'p_child_id':"'"+scope['child']+"'::uuid",'p_date':"'2026-11-10'::date",'p_week_start':"'2026-11-09'::date",'z':"'UTC'",
        'p_after_start':'NULL::timestamptz','p_after_id':'NULL::uuid','p_after_child':'NULL::uuid','p_after_actor':'NULL::uuid',
        'p_before_created':'NULL::timestamptz','p_before_id':'NULL::uuid','p_batch_id':'NULL::uuid',
    }
    queries=storage_queries(source)
    report={'scope':'Synthetic local PostgreSQL17 storage SELECTs extracted from shipped SQL; superuser plans exclude RPC authorisation and provider/network latency; no performance SLA claimed',
            'migration_sha256':hashlib.sha256(source.encode()).hexdigest(),'fixture':{'academies':8,'children':800,'sessions':480,'attendance_records':48000,'parent_items':48000,'parent_signals':96000},'queries':{}}
    for name,query in queries.items():
        query=re.sub(r'\b('+'|'.join(sorted(values,key=len,reverse=True))+r')\b',lambda m:values[m.group()],query)
        query=query.replace("auth.uid()", "'"+actor+"'::uuid")
        plan=json.loads(sql('EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) '+query))[0]
        rows=plan['Plan']['Actual Rows']
        expected={'sessions':1,'roster':100,'latest_signals':100,'feed':51,'weekly':7}[name]
        if rows!=expected:raise AssertionError(f'{name}: expected {expected} rows, observed {rows}')
        report['queries'][name]={'sql':query,'expected_rows':expected,'plan':plan}
    (out/'query-plans.json').write_text(json.dumps(report,indent=2)+'\n')
