#!/usr/bin/env python3
"""Upgrade the founder-selected existing TEST backend, preserving original records.

Default is inspect-only. --execute applies only missing ordered repository
migrations, atomically with each migration-history receipt. Never resets data.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
# Establish the audit location before any hosted operation can execute.
(ROOT/'work').mkdir(mode=0o700,exist_ok=True)
PROJECT = 'fmavpazczahxeusqbxuh'
BASE_TABLES = ['profiles', 'workspaces', 'workspace_memberships', 'children', 'guardianships', 'connection_requests', 'workspace_children', 'connection_events']
parser = argparse.ArgumentParser()
parser.add_argument('--execute', action='store_true')
args = parser.parse_args()
token = os.environ.get('SUPABASE_ACCESS_TOKEN')
if not token: raise SystemExit('Management credential unavailable; never paste it into chat')
def query(sql):
    request = urllib.request.Request(f'https://api.supabase.com/v1/projects/{PROJECT}/database/query', data=json.dumps({'query':sql}).encode(), headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(request,timeout=90) as response: return json.load(response)
def literal(value): return "'" + value.replace("'", "''") + "'"
def identifier(value):
    if not re.fullmatch('[a-z_][a-z0-9_]*',value): raise ValueError('Unexpected schema identifier')
    return '"'+value+'"'
migrations=sorted((ROOT/'supabase/migrations').glob('*.sql'))
if len(migrations)!=51: raise SystemExit('STOP: migration inventory changed; review before applying')
versions=[p.name.split('_',1)[0] for p in migrations]
history=[r['version'] for r in query('select version from supabase_migrations.schema_migrations order by version')]
if not 13 <= len(history) <=51 or history!=versions[:len(history)]: raise SystemExit('STOP: hosted history differs from the reviewed ordered baseline')
columns={t:[r['column_name'] for r in query(f"select column_name from information_schema.columns where table_schema='public' and table_name={literal(t)} order by ordinal_position")] for t in BASE_TABLES}
if any(not c for c in columns.values()): raise SystemExit('STOP: expected baseline tables are missing')
def snapshot():
    result={}
    for table,fields in columns.items():
        pairs=','.join(literal(c)+',t.'+identifier(c) for c in fields)
        row=query(f"select count(*) as records, md5(coalesce(jsonb_agg(jsonb_build_object({pairs}) order by t.id)::text,'[]')) as fingerprint from public.{identifier(table)} t")[0]
        result[table]=row
    result['auth_users']=query("select count(*) as records,md5(coalesce(jsonb_agg(jsonb_build_object('id',id,'email',email,'created_at',created_at) order by id)::text,'[]')) as fingerprint from auth.users")[0]
    return result
before=snapshot()
report={'project_ref':PROJECT,'baseline_versions':history,'baseline_records':before,'migrations':[],'executed':args.execute}
print('Target: founder-selected existing TEST project',PROJECT,flush=True)
print('Current migration count:',len(history),'pending:',51-len(history),flush=True)
print('Original row counts:',{k:v['records'] for k,v in before.items()},flush=True)
if args.execute:
    try:
        for path in migrations[len(history):]:
            version,name=path.stem.split('_',1)
            original=path.read_text()
            body=re.sub(r'^\s*(?:begin|commit);\s*$', '', original, flags=re.I|re.M)
            sql="begin; set local lock_timeout='10s'; set local statement_timeout='60s'; select pg_advisory_xact_lock(hashtextextended('parentplus:testing-upgrade',0));\n"+body+f"\ninsert into supabase_migrations.schema_migrations(version,name,statements) values ({literal(version)},{literal(name)},array[{literal(original)}]);\ncommit;"
            query(sql)
            report['migrations'].append({'version':version,'name':name,'sha256':hashlib.sha256(original.encode()).hexdigest()})
            print('Applied',path.name,flush=True)
        after=snapshot();report['after_records']=after
        if after!=before: raise RuntimeError('STOP: baseline record fingerprints changed; investigate without resetting data')
        final=[r['version'] for r in query('select version from supabase_migrations.schema_migrations order by version')]
        if final!=versions: raise RuntimeError('Migration history did not reach the reviewed version set')
        query('begin; update public.parent_child_read_controls set enabled=true where id; update public.child_creation_controls set enabled=true where id; update public.class_setup_controls set enabled=true where id; update public.workspace_creation_controls set enabled=true where id; commit;')
        report['status']='passed';report['final_versions']=final
        print('PASS: all51 migrations recorded; original row fingerprints preserved; founder feature controls enabled',flush=True)
    finally:
        (ROOT/'work/hosted-testing-upgrade-report.json').write_text(json.dumps(report,indent=2)+'\n')
else: print('Inspection only: use --execute only with the founder-approved testing target',flush=True)
