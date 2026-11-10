#!/usr/bin/env bash
# Local-only development stack. Never invokes link, push, reset, deploy or hosted APIs.
set -euo pipefail
cd "$(dirname "$0")/../.."
umask 077
mkdir -p work
# The template contains no secrets and must be readable by the Kong user.
chmod 644 supabase/templates/local-otp.html
export SUPABASE_HOME="$PWD/work/supabase-cli"
export SUPABASE_USE_SLIM_IMAGES=true
export npm_config_cache="${npm_config_cache:-$PWD/work/npm-cache}"
export DOCKER_HOST=unix:///var/run/docker.sock
unset SUPABASE_ACCESS_TOKEN DOCKER_CONTEXT DOCKER_TLS DOCKER_TLS_VERIFY DOCKER_CERT_PATH
cli() { npm exec --yes --package=supabase@3.1.0 -- supabase "$@"; }
case "${1:-}" in
  start)
    docker --host=unix:///var/run/docker.sock info >/dev/null
    # Docker injects proxy variables; BusyBox wget ignores NO_PROXY on health probes.
    # After startup, repair exact internal/loopback requests and require Auth to be healthy.
    if ! cli start -x realtime,storage-api,imgproxy,postgres-meta,studio,edge-runtime,logflare,vector,supavisor --ignore-health-check >work/supabase-start.log 2>&1; then
      echo 'Local startup failed; inspect work/supabase-start.log privately.' >&2
      exit 1
    fi
    python3 scripts/dev/fix-local-auth-proxy.py
    ready=false
    for ((i=0; i<30; i++)); do
      if [ "$(docker inspect supabase_auth_ParentPlus --format '{{.State.Health.Status}}')" = healthy ] &&
        curl -fsS --max-time 3 http://127.0.0.1:54321/auth/v1/health >/dev/null; then ready=true; break; fi
      sleep 1
    done
    [ "$ready" = true ] || { echo 'STOP: local Auth health was not established'; exit 1; }
    cli status -o env >work/local-supabase.env
    echo 'Local Supabase ready: API 127.0.0.1:54321; mailbox 127.0.0.1:54324.'
    ;;
  status)
    docker ps --filter label=com.supabase.cli.project=ParentPlus --format '{{.Names}} {{.Status}}'
    curl -fsS --max-time 5 http://127.0.0.1:54321/auth/v1/health
    ;;
  stop) cli stop --project-id ParentPlus ;;
  *) echo 'Usage: scripts/dev/local-supabase.sh start|status|stop' >&2; exit 2 ;;
esac
