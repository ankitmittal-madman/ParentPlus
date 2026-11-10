#!/usr/bin/env python3
"""Run the real-provider browser suite against the fixed local Supabase stack."""
import os
from pathlib import Path
import shlex
import subprocess
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
# Hold one lease for local feature-control changes across manual and test runners.
import fcntl
(ROOT / 'work').mkdir(exist_ok=True)
lease = (ROOT / 'work/local-feature-controls.lock').open('a')
try:
    fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    raise SystemExit('STOP: another local founder/test runner owns the feature controls; keep the existing app running or stop it before starting this runner')
# Reject inherited hosted endpoints before loading or changing anything.
if os.environ.get('NEXT_PUBLIC_SUPABASE_URL') not in (None, '', 'http://127.0.0.1:54321'):
    raise SystemExit('STOP: local E2E refuses a nonlocal Supabase URL')
# Tie all privileged fixture writes to this checkout's local Docker services.
import json
for container in ['supabase_db_ParentPlus', 'supabase_auth_ParentPlus', 'supabase_kong_ParentPlus']:
    metadata = json.loads(subprocess.check_output(['docker', '--host=unix:///var/run/docker.sock', 'inspect', container], text=True))[0]
    labels = metadata['Config'].get('Labels', {})
    if labels.get('com.supabase.cli.project') != 'ParentPlus' or labels.get('com.supabase.cli.workdir') != str(ROOT):
        raise SystemExit('STOP: local Supabase belongs to another checkout')
values = {}
for line in (ROOT / 'work/local-supabase.env').read_text().splitlines():
    if '=' in line:
        key, value = line.split('=', 1)
        values[key] = shlex.split(value)[0]
if values.get('API_URL') != 'http://127.0.0.1:54321':
    raise SystemExit('STOP: unexpected local API endpoint')
if values.get('MAILPIT_URL') != 'http://127.0.0.1:54324':
    raise SystemExit('STOP: unexpected local mailbox endpoint')
parsed = urlparse(values.get('DB_URL', ''))
if parsed.hostname != '127.0.0.1' or parsed.port != 54322:
    raise SystemExit('STOP: unexpected local database endpoint')
env = {k: v for k, v in os.environ.items() if not k.startswith('SUPABASE_') and k not in ('DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_TLS', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH')}
env.update({
    'NEXT_TELEMETRY_DISABLED': '1',
    'XDG_CONFIG_HOME': str(ROOT / 'work/xdg-config'),
    'PARENTPLUS_LOCAL_E2E': '1',
    'NEXT_PUBLIC_SUPABASE_URL': values['API_URL'],
    'NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY': values['ANON_KEY'],
    'NEXT_PUBLIC_ENABLE_LIVE_OTP': 'true',
    'NEXT_PUBLIC_ENABLE_ACCOUNT_SIGNUP': 'true',
    'NEXT_PUBLIC_ENABLE_PARENT_PROFILE_LINK': 'true',
    'PARENTPLUS_ENABLE_PARENT_CHILD_LIST': 'true',
    'PARENTPLUS_ENABLE_CHILD_CREATION': 'true',
    'PARENTPLUS_ENABLE_CLASS_SETUP': 'true',
    'PARENTPLUS_ENABLE_WORKSPACE_CREATION': 'true',
    'NEXT_PUBLIC_ENABLE_WORKSPACE_ONBOARDING': 'true',
})
raise SystemExit(subprocess.run(['node_modules/.bin/playwright', 'test', '--config', 'playwright.local.config.ts'], cwd=ROOT / 'apps/web', env=env).returncode)
