#!/usr/bin/env bash
set -euo pipefail
if [ "${PARENTPLUS_SYNTHETIC_BROWSER:-}" != '1' ] || [ "$#" -ne 1 ] || [ ! -d "$1" ]; then
  echo 'STOP: Isolated synthetic browser configuration required' >&2
  exit 1
fi
printf '%s\n' network > "$1/test-phase"
ip link set lo up
python3 - <<'PY'
import json
import subprocess
links = json.loads(subprocess.check_output(['ip', '-j', 'link', 'show'], text=True))
if {link['ifname'] for link in links} != {'lo'}:
    raise SystemExit('STOP: Browser namespace has non-loopback interfaces')
for family in ('-4', '-6'):
    routes = json.loads(subprocess.check_output(['ip', '-j', family, 'route', 'show', 'table', 'all'], text=True))
    if any(route.get('dev') not in (None, 'lo') or route.get('dst') == 'default' for route in routes):
        raise SystemExit('STOP: Browser namespace has a non-loopback route')
PY
cd "$1"
printf '%s\n' build > test-phase
./node_modules/.bin/next build
printf '%s\n' startup > test-phase
node e2e-enabled/fake-supabase.mjs >test-fake.log 2>&1 &
fake_pid=$!
./node_modules/.bin/next start --hostname 127.0.0.1 --port 3190 >test-next.log 2>&1 &
next_pid=$!
cleanup() {
  kill "$fake_pid" "$next_pid" 2>/dev/null || true
  wait "$fake_pid" "$next_pid" 2>/dev/null || true
}
trap cleanup EXIT
ready=0
for attempt in $(seq 1 60); do
  if ! kill -0 "$fake_pid" "$next_pid" 2>/dev/null; then
    echo 'STOP: Synthetic service exited before becoming ready' >&2
    exit 1
  fi
  if node -e "Promise.all([fetch('http://127.0.0.1:3190/parent/children'),fetch('http://127.0.0.1:3191/__test/events')]).then(r=>process.exit(r.every(x=>x.ok)?0:1)).catch(()=>process.exit(1))"; then
    ready=1
    break
  fi
  sleep 1
done
if [ "$ready" -ne 1 ]; then
  echo 'STOP: Synthetic services did not become ready' >&2
  exit 1
fi
printf '%s\n' browser > test-phase
timeout 90s ./node_modules/.bin/playwright test --config=playwright.enabled.config.mjs
