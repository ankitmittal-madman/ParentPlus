#!/usr/bin/env python3
"""Local PG17 052→053 preservation/rollback rehearsal; NO hosted transport.

The real upgrade tool is copied to a disposable source bundle. Its HTTP boundary
is replaced with an owned network-isolated PostgreSQL adapter. This establishes
SQL/receipt/preservation behaviour, not Supabase Auth/JWT or Management API transport.
"""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'test-results/database/attendance-upgrade'
CONTAINER='parentplus-upgrade-attendance'
DOCKER=['docker','--host=unix:///var/run/docker.sock']
ENV={k:v for k,v in os.environ.items() if k not in {'DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH'}}
A='11111111-1111-4111-8111-111111111111'
B='22222222-2222-4222-8222-222222222222'
W='a0000000-0000-4000-8000-000000000001'
C='d0000000-0000-4000-8000-000000000001'
COURSE='e0000000-0000-4000-8000-000000000001'
BATCH='b0000000-0000-4000-8000-000000000001'
SESSION='f0000000-0000-4000-8000-000000000001'
TOKEN='ab'*32


def literal(value):return "'"+value.replace("'","''")+"'"

def docker(*args,check=True):
    return subprocess.run(DOCKER+list(args),env=ENV,text=True,capture_output=True,check=check,timeout=180)


def main():
    (ROOT/'work').mkdir(mode=0o700,exist_ok=True)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'summary.json').write_text(json.dumps({'status':'running','scope':'local only; not release evidence'})+'\n')
    if docker('inspect',CONTAINER,check=False).returncode==0:
        raise RuntimeError('Existing rehearsal container preserved; refusing to reuse it')
    created=None
    try:
        created=docker('run','-d','--name',CONTAINER,'--network','none','--label','parentplus.rehearsal=attendance-053','--label','parentplus.workdir='+str(ROOT),'-e','POSTGRES_USER=parentplus_test','-e','POSTGRES_PASSWORD=localtest','-e','POSTGRES_DB=parentplus_test','postgres:17').stdout.strip()
        if not re.fullmatch('[0-9a-f]{64}',created):raise RuntimeError('Invalid owned container identity')
        meta=json.loads(docker('inspect',created).stdout)[0]
        assert meta['Id']==created and meta['HostConfig']['NetworkMode']=='none' and not docker('port',created).stdout.strip()
        def sql(text):
            result=subprocess.run(DOCKER+['exec','-i',created,'psql','-X','-q','-A','-t','-v','ON_ERROR_STOP=1','-U','parentplus_test','-d','parentplus_test'],input=text+'\n',env=ENV,text=True,capture_output=True,timeout=150)
            if result.returncode:
                (OUT/'postgres-last-error.log').write_text('LOCAL synthetic fixture only\n'+result.stderr)
                result.check_returncode()
            return result.stdout.strip()
        def query(text):return json.loads(sql("SELECT coalesce(jsonb_agg(to_jsonb(r)),'[]'::jsonb) FROM ("+text.strip().rstrip(';')+") r;"))
        for _ in range(120):
            try:
                if sql('select 1')=='1':break
            except subprocess.CalledProcessError:time.sleep(.25)
        else:raise RuntimeError('Owned PostgreSQL did not become ready')
        sql((ROOT/'tests/database/supabase_auth_fixture.sql').read_text())
        # The minimal SQL unit fixture omits this real Auth audit field.
        sql("alter table auth.users add column created_at timestamptz not null default '2026-11-01T00:00:00Z';")
        sql('create schema supabase_migrations; create table supabase_migrations.schema_migrations(version text primary key,name text,statements text[]);')
        paths=sorted((ROOT/'supabase/migrations').glob('*.sql'));assert len(paths)==53
        for path in paths[:-1]:
            original=path.read_text();sql(original)
            version,name=path.stem.split('_',1)
            sql(f'insert into supabase_migrations.schema_migrations values({literal(version)},{literal(name)},array[{literal(original)}]);')
        sql(f"""begin;
select set_config('request.jwt.claim.sub','{A}',true);
insert into public.workspaces(id,name,type,created_by,creation_request_id,scheduling_time_zone) values('{W}','Fictional Upgrade Academy','academy','{A}',gen_random_uuid(),'Asia/Kolkata');
insert into public.workspace_memberships(workspace_id,user_id,role,status) values('{W}','{A}','owner','active');
select set_config('request.jwt.claim.sub','{B}',true);
insert into public.children(id,display_name,created_by) values('{C}','Fictional Upgrade Child','{B}');
insert into public.guardianships(child_id,guardian_user_id,status) values('{C}','{B}','active');
select set_config('request.jwt.claim.sub','{A}',true);
insert into public.courses(id,workspace_id,name) values('{COURSE}','{W}','Fictional Upgrade Course');
insert into public.batches(id,workspace_id,course_id,name) values('{BATCH}','{W}','{COURSE}','Fictional Upgrade Batch');
insert into public.batch_coach_assignments select '{W}','{BATCH}',id from public.workspace_memberships where workspace_id='{W}' and user_id='{A}';
insert into public.schedule_sessions(id,workspace_id,batch_id,starts_at,ends_at,created_by,creation_request_id) values('{SESSION}','{W}','{BATCH}','2026-11-10T11:30:00Z','2026-11-10T12:30:00Z','{A}',gen_random_uuid());
set local role authenticated;
select * from public.app_issue_family_invite('{W}',gen_random_uuid(),'{TOKEN}');
select set_config('request.jwt.claim.sub','{B}',true);
select public.app_accept_family_invite('{TOKEN}','{C}');
select set_config('request.jwt.claim.sub','{A}',true);
select * from public.app_save_enrollment('{W}','{BATCH}','{C}',gen_random_uuid());
commit;""")
        def schema_snapshot():
            return query("""SELECT jsonb_build_object(
 'columns',(select jsonb_agg(jsonb_build_array(table_name,column_name,data_type,is_nullable,column_default) order by table_name,ordinal_position) from information_schema.columns where table_schema='public'),
 'constraints',(select jsonb_agg(jsonb_build_array(c.relname,k.conname,pg_get_constraintdef(k.oid)) order by c.relname,k.conname) from pg_constraint k join pg_class c on c.oid=k.conrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname='public'),
 'functions',(select jsonb_agg(jsonb_build_array(p.proname,pg_get_function_identity_arguments(p.oid),pg_get_functiondef(p.oid),p.proacl::text) order by p.proname,pg_get_function_identity_arguments(p.oid)) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.prokind='f')
 ) AS schema""")[0]['schema']
        schema_before=schema_snapshot()
        canonical=ROOT/'work/hosted-testing-upgrade-report.json'
        canonical_hash=hashlib.sha256(canonical.read_bytes()).hexdigest() if canonical.exists() else None
        with tempfile.TemporaryDirectory(prefix='attendance-upgrade-',dir=ROOT/'work') as directory:
            bundle=Path(directory);tool=bundle/'scripts/deploy/upgrade-testing-backend.py';tool.parent.mkdir(parents=True)
            shutil.copy2(ROOT/'scripts/deploy/upgrade-testing-backend.py',tool)
            shutil.copytree(ROOT/'supabase/migrations',bundle/'supabase/migrations')
            candidate=bundle/'supabase/migrations'/paths[-1].name;original=candidate.read_text()
            candidate.write_text(original+'\nSELECT 1/0;\n')
            class Response(io.BytesIO):
                def __enter__(self):return self
                def __exit__(self,*args):self.close()
            requests=[]
            def local_transport(request,**_kwargs):
                assert request.full_url=='https://api.supabase.com/v1/projects/fmavpazczahxeusqbxuh/database/query'
                assert request.get_header('Authorization')=='Bearer local-rehearsal-only'
                text=json.loads(request.data)['query'];requests.append('select' if text.lstrip().lower().startswith('select') else 'transaction')
                result=query(text) if text.lstrip().lower().startswith('select') else (sql(text) and [])
                return Response(json.dumps(result or []).encode())
            def invoke():
                output=io.StringIO()
                with patch('urllib.request.urlopen',side_effect=local_transport),patch.dict(os.environ,{'SUPABASE_ACCESS_TOKEN':'local-rehearsal-only'}),patch.object(sys,'argv',[str(tool),'--execute']),contextlib.redirect_stdout(output):
                    try:return runpy.run_path(str(tool),run_name='__main__')
                    finally:(OUT/'tool-local-adapter.log').write_text('LOCAL ONLY; management transport replaced with isolated PostgreSQL\n'+output.getvalue())
            try:invoke()
            except subprocess.CalledProcessError as error:
                if 'division by zero' not in (error.stderr or ''):raise
            else:raise AssertionError('Injected migration failure unexpectedly succeeded')
            failed=json.loads((bundle/'work/hosted-testing-upgrade-report.json').read_text())
            assert failed['status']=='failed' and schema_snapshot()==schema_before
            assert len(query('select version from supabase_migrations.schema_migrations'))==52
            shutil.copy2(bundle/'work/hosted-testing-upgrade-report.json',OUT/'injected-failure-receipt.json')
            candidate.write_text(original);state=invoke()
            result=json.loads((bundle/'work/hosted-testing-upgrade-report.json').read_text())
            assert result['status']=='passed' and len(result['final_versions'])==53 and result['baseline_records']==failed['baseline_records']==result['after_records']
            with patch('urllib.request.urlopen',side_effect=local_transport):
                assert state['snapshot']()==result['expected_post_activation_records']==result['post_activation_records']
            assert len(result['intentional_control_changes'])==4
            assert query("select count(*) AS n from information_schema.tables where table_schema='public' and table_type='BASE TABLE'")==[{'n':41}]
            assert query("select count(*) AS n from public.schedule_sessions where status<>'scheduled' or version<>1 or updated_at is null")==[{'n':0}]
            assert query('select (select count(*) from public.attendance_records)+(select count(*) from public.parent_items)+(select count(*) from public.parent_signals) AS n')==[{'n':0}]
            shutil.copy2(bundle/'work/hosted-testing-upgrade-report.json',OUT/'success-receipt.json')
            assert (hashlib.sha256(canonical.read_bytes()).hexdigest() if canonical.exists() else None)==canonical_hash
            summary={'status':'passed','kind':'LOCAL PostgreSQL17; synthetic Auth; management transport replaced; NO hosted requests','rollback':'schema, original records and52 history entries preserved after late injected failure','upgrade':'53 history entries,41 tables, original34-table/Auth snapshot preserved except four explicitly audited enabled flags','invented_attendance_items_signals':0,'migration_sha256':hashlib.sha256(original.encode()).hexdigest(),'outbound_http_requests':0}
            # Seed performance records only AFTER all preservation/no-invention assertions.
            plans=runpy.run_path(str(ROOT/'scripts/ci/attendance-query-plans.py'))
            plans['collect'](sql,original,OUT,A)
            summary['query_plans']='five shipped storage SELECTs, actual EXPLAIN ANALYZE/BUFFERS in query-plans.json'
            (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        print('PASS: LOCAL052→053 rollback/schema/data/history and success preservation; four control changes audited; zero hosted requests')
    finally:
        if created:
            inspection=docker('inspect',created,check=False)
            if inspection.returncode==0:
                own=json.loads(inspection.stdout)[0]
                assert own['Id']==created and own['Config']['Labels'].get('parentplus.rehearsal')=='attendance-053' and own['Config']['Labels'].get('parentplus.workdir')==str(ROOT)
                docker('rm','-f',created)


if __name__=='__main__':
    # Any accidentally unadapted call fails locally instead of reaching a service.
    with patch('urllib.request.urlopen',side_effect=RuntimeError('Network transport prohibited in this local rehearsal')):
        main()
