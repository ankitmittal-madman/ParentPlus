#!/usr/bin/env python3
"""Repair proxy handling only in this checkout's disposable local Auth container.

Preserve image, mounts, registry settings, remote proxy variables and network.
Extend NO_PROXY only for exact local service names; BusyBox health uses -Y off
only for its fixed loopback request. No hosted endpoint or daemon config changes.
"""
import copy
import http.client
import json
from pathlib import Path
import socket

NAME = 'supabase_auth_ParentPlus'
ROOT = str(Path(__file__).resolve().parents[2])
class LocalDocker(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect('/var/run/docker.sock')

def api(method, path, value=None, accepted=(200, 201, 204, 304)):
    client = LocalDocker('localhost', timeout=30)
    body = None if value is None else json.dumps(value).encode()
    client.request(method, '/v1.48' + path, body, {'Content-Type': 'application/json'})
    response = client.getresponse()
    data = response.read()
    client.close()
    if response.status not in accepted:
        raise RuntimeError(f'Local Docker {method} failed: status {response.status}')
    return json.loads(data) if data else None

old = api('GET', f'/containers/{NAME}/json')
labels = old['Config'].get('Labels', {})
if labels.get('com.supabase.cli.project') != 'ParentPlus' or labels.get('com.supabase.cli.workdir') != ROOT:
    raise SystemExit('STOP: Auth container belongs to a different local checkout')
config = copy.deepcopy(old['Config'])
proxy = {}
for entry in config.get('Env', []):
    key, _, value = entry.partition('=')
    proxy[key] = value
local_hosts = ['localhost', '127.0.0.1', '::1', 'supabase_kong_ParentPlus', 'supabase_inbucket_ParentPlus', 'supabase_db_ParentPlus']
for key in ['NO_PROXY', 'no_proxy']:
    hosts = proxy.get(key, '').split(',')
    proxy[key] = ','.join(dict.fromkeys(h for h in hosts + local_hosts if h))
config['Env'] = [f'{k}={v}' for k, v in proxy.items()]
health = config.get('Healthcheck', {}).get('Test')
if health not in (['CMD-SHELL', 'wget -q --spider http://127.0.0.1:9999/health'], ['CMD-SHELL', 'wget -Y off -q --spider http://127.0.0.1:9999/health']):
    raise SystemExit('STOP: unexpected Auth health probe')
config['Healthcheck']['Test'] = ['CMD-SHELL', 'wget -Y off -q --spider http://127.0.0.1:9999/health']
if config == old['Config']:
    print('Local Auth proxy settings already repaired.')
    raise SystemExit(0)

def create(saved):
    body = copy.deepcopy(saved)
    body['HostConfig'] = old['HostConfig']
    body['NetworkingConfig'] = {'EndpointsConfig': {n: {'Aliases': v.get('Aliases') or []} for n, v in old['NetworkSettings']['Networks'].items()}}
    api('POST', f'/containers/create?name={NAME}', body)
    api('POST', f'/containers/{NAME}/start')

api('POST', f'/containers/{NAME}/stop?t=10')
api('DELETE', f'/containers/{NAME}')
try:
    create(config)
except Exception:
    # Restore the prior container configuration if replacement failed.
    try: api('DELETE', f'/containers/{NAME}?force=true', accepted=(204, 404))
    finally: create(old['Config'])
    raise
print('Repaired exact local Auth proxy bypasses and loopback health command.')
