#!/usr/bin/env bash
# Isolated synthetic-provider browser checks; never point this at a real service.
set -euo pipefail
cd "$(dirname "$0")/../.."
repo_root="$PWD"
web_root="$repo_root/apps/web"
test_dir="$(mktemp -d /tmp/parentplus-enabled-browser.XXXXXXXX)"
trap 'rm -rf -- "$test_dir"' EXIT

chromium_path="${PARENTPLUS_CHROMIUM_PATH:-}"
if [ -z "$chromium_path" ]; then
  if ! chromium_path="$(cd "$web_root" && node -e 'process.stdout.write(require("@playwright/test").chromium.executablePath())')"; then
    echo '::error title=Isolated browser prerequisites::The Chromium executable could not be located.'
    echo 'STOP: could not locate local Chromium' >&2
    exit 1
  fi
fi
if [ ! -x "$chromium_path" ]; then
  echo '::error title=Isolated browser prerequisites::The local Chromium executable is unavailable.'
  echo "STOP: Local Chromium executable is unavailable" >&2
  exit 1
fi
namespace_mode=user
runner_uid="$(/usr/bin/id -u)"
runner_gid="$(/usr/bin/id -g)"
if [ "$runner_uid" -eq 0 ] || [ "$runner_gid" -eq 0 ]; then
  echo '::error title=Isolated browser prerequisites::The browser runner requires a non-root user and group.'
  echo 'STOP: browser runner cannot run as root' >&2
  exit 1
fi
if ! unshare -Urn true >/dev/null 2>&1; then
  namespace_mode=unavailable
  # Only fixed system commands run before privileges are dropped.
  if [ "${PARENTPLUS_SKIP_PRIVILEGED_FALLBACK:-}" != '1' ] && [ "$runner_uid" -ne 0 ] &&
     [ -x /usr/bin/sudo ] && [ -x /usr/bin/unshare ] && [ -x /usr/sbin/ip ] && [ -x /usr/bin/setpriv ] &&
     /usr/bin/sudo -n /usr/bin/unshare -n -- /usr/bin/true >/dev/null 2>&1; then
    namespace_mode=privileged-bootstrap
  fi
  if [ "$namespace_mode" = unavailable ]; then
    echo '::error title=Isolated browser prerequisites::The required network namespace could not be created safely.'
    echo 'STOP: network namespace is unavailable; enabled browser checks cannot run safely' >&2
    exit 1
  fi
fi

# Copy an application snapshot excluding root env files and build/test caches.
# The Next build cannot follow an external node_modules symlink with Turbopack.
if ! tar -C "$web_root" --exclude='./node_modules' --exclude='./.next' --exclude='./.env*' \
  --exclude='./test-results' --exclude='./playwright-report' -cf - . | tar -C "$test_dir" -xf -; then
  echo '::error title=Isolated browser preparation::Copying the application snapshot failed.'
  exit 1
fi
if ! cp -a --reflink=auto "$web_root/node_modules" "$test_dir/node_modules"; then
  echo '::error title=Isolated browser preparation::Copying browser test dependencies failed.'
  exit 1
fi

# A fresh network namespace has no external interfaces; all processes, including
# Next server actions and Chromium, run there with a scrubbed environment.
printf '%s\n' namespace > "$test_dir/test-phase"
clean_env=(PATH="$PATH" NEXT_TELEMETRY_DISABLED=1 NODE_OPTIONS=--dns-result-order=ipv4first
  PARENTPLUS_SYNTHETIC_BROWSER=1 PARENTPLUS_CHROMIUM_PATH="$chromium_path"
  NEXT_PUBLIC_ENABLE_LIVE_OTP=true NEXT_PUBLIC_ENABLE_ACCOUNT_SIGNUP=false
  NEXT_PUBLIC_SUPABASE_URL=http://localhost:3191 NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=synthetic-public-key
  PARENTPLUS_ENABLE_PARENT_CHILD_LIST=true PARENTPLUS_ENABLE_CHILD_CREATION=true)
inner_script="$repo_root/scripts/ci/enabled-parent-browser-inner.sh"
run_namespace() {
  if [ "$namespace_mode" = user ]; then
    unshare -Urn /usr/bin/env -i "${clean_env[@]}" /bin/bash "$inner_script" "$test_dir"
  else
    # No checkout code or interpolated shell text executes as root.
    /usr/bin/sudo -n /usr/bin/unshare -n -- /usr/bin/env -i /bin/bash --noprofile --norc -c '
      set -eu
      /usr/sbin/ip link set lo up
      target_uid="$1"; target_gid="$2"; shift 2
      exec /usr/bin/setpriv --reuid "$target_uid" --regid "$target_gid" --clear-groups \
        --bounding-set=-all --inh-caps=-all --ambient-caps=-all --no-new-privs "$@"
    ' parentplus "$runner_uid" "$runner_gid" /usr/bin/env -i "${clean_env[@]}" \
      PARENTPLUS_VERIFY_DROPPED_UID="$runner_uid" PARENTPLUS_VERIFY_DROPPED_GID="$runner_gid" \
      /bin/bash "$inner_script" "$test_dir"
  fi
}
if ! run_namespace; then
  phase="$(cat "$test_dir/test-phase" 2>/dev/null || printf '%s' unknown)"
  case "$phase" in namespace|privilege|network|build|startup|browser) ;; *) phase=unknown ;; esac
  echo "::error title=Isolated browser checks::The synthetic browser run failed during the $phase phase."
  echo "STOP: isolated browser run failed during $phase" >&2
  exit 1
fi

mkdir -p "$web_root/test-results"
cp "$test_dir/test-results/playwright-enabled-junit.xml" "$web_root/test-results/playwright-enabled-junit.xml"
echo 'PASS: Isolated enabled parent browser checks completed'
