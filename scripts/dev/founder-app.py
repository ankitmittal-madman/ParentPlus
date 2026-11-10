#!/usr/bin/env python3
"""Run the founder sandbox against this checkout's actual local database."""
import argparse
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess

ROOT = Path(__file__).resolve().parents[2]
# Hold one lease for local feature-control changes across manual and test runners.
import fcntl
(ROOT / 'work').mkdir(exist_ok=True)
lease = (ROOT / 'work/local-feature-controls.lock').open('a')
try:
    fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    raise SystemExit('STOP: another local founder/test runner owns the feature controls; keep the existing app running or stop it before starting this runner')
parser = argparse.ArgumentParser()
parser.add_argument('--test', action='store_true', help='run the founder browser suite instead of the manual app')
args = parser.parse_args()
if os.environ.get('NEXT_PUBLIC_SUPABASE_URL') not in (None, '', 'http://127.0.0.1:54321'):
    raise SystemExit('STOP: founder sandbox refuses hosted Supabase')
for name in ['supabase_db_ParentPlus', 'supabase_auth_ParentPlus', 'supabase_kong_ParentPlus']:
    item = json.loads(subprocess.check_output(['docker', '--host=unix:///var/run/docker.sock', 'inspect', name], text=True))[0]
    labels = item['Config'].get('Labels', {})
    if labels.get('com.supabase.cli.project') != 'ParentPlus' or labels.get('com.supabase.cli.workdir') != str(ROOT):
        raise SystemExit('STOP: local Supabase belongs to another checkout')
values = {}
for line in (ROOT / 'work/local-supabase.env').read_text().splitlines():
    if '=' in line:
        key, value = line.split('=', 1)
        values[key] = shlex.split(value)[0]
if values.get('API_URL') != 'http://127.0.0.1:54321' or not values.get('SERVICE_ROLE_KEY'):
    raise SystemExit('STOP: local Supabase configuration is unavailable')
env = {k: v for k, v in os.environ.items() if not k.startswith(('SUPABASE_', 'NEXT_PUBLIC_SUPABASE_', 'PARENTPLUS_LOCAL_'))}
env.update({
    'NEXT_TELEMETRY_DISABLED': '1', 'XDG_CONFIG_HOME': str(ROOT / 'work/xdg-config'),
    'NEXT_PUBLIC_SUPABASE_URL': values['API_URL'], 'NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY': values['ANON_KEY'],
    'PARENTPLUS_LOCAL_SERVICE_KEY': values['SERVICE_ROLE_KEY'],
    'PARENTPLUS_FOUNDER_MODE': 'true', 'NEXT_PUBLIC_FOUNDER_MODE': 'true',
    'NEXT_PUBLIC_ENABLE_LIVE_OTP': 'true', 'NEXT_PUBLIC_ENABLE_ACCOUNT_SIGNUP': 'true',
    'NEXT_PUBLIC_ENABLE_PARENT_PROFILE_LINK': 'true', 'PARENTPLUS_ENABLE_PARENT_CHILD_LIST': 'true',
    'PARENTPLUS_ENABLE_CHILD_CREATION': 'true', 'PARENTPLUS_ENABLE_CLASS_SETUP': 'true',
    'PARENTPLUS_ENABLE_WORKSPACE_CREATION': 'true', 'NEXT_PUBLIC_ENABLE_WORKSPACE_ONBOARDING': 'true',
})
def sql(query):
    return subprocess.check_output(['docker', '--host=unix:///var/run/docker.sock', 'exec', 'supabase_db_ParentPlus', 'psql', '-XAt', '-v', 'ON_ERROR_STOP=1', '-U', 'postgres', '-d', 'postgres', '-c', query], text=True).strip()
tables = ['parent_child_read_controls', 'child_creation_controls', 'class_setup_controls', 'workspace_creation_controls']
previous = {table: sql(f'select enabled from public.{table} where id') for table in tables}
if any(value not in ('t', 'f') for value in previous.values()):
    raise SystemExit('STOP: local feature-control state is unknown')
process = None
def stop(_signum, _frame):
    raise KeyboardInterrupt
signal.signal(signal.SIGTERM, stop)
try:
    for table in tables: sql(f'update public.{table} set enabled=true where id')
    command = ['node_modules/.bin/playwright', 'test', '--config', 'playwright.founder.config.ts'] if args.test else ['npm', 'run', 'dev', '--', '--hostname', '127.0.0.1', '--port', '3193']
    print('Founder sandbox: http://127.0.0.1:3193/founder — fictional .test email, OTP 123456', flush=True)
    process = subprocess.Popen(command, cwd=ROOT / 'apps/web', env=env, start_new_session=True)
    result = process.wait()
except KeyboardInterrupt:
    result = 0
finally:
    if process and process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL); process.wait()
    for table, value in previous.items(): sql(f"update public.{table} set enabled={'true' if value == 't' else 'false'} where id")
raise SystemExit(result)
