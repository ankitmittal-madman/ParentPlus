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
  chromium_path="$(cd "$web_root" && node -e 'process.stdout.write(require("@playwright/test").chromium.executablePath())')"
fi
if [ ! -x "$chromium_path" ]; then
  echo "STOP: Local Chromium executable is unavailable" >&2
  exit 1
fi

# Copy an application snapshot excluding root env files and build/test caches.
# The Next build cannot follow an external node_modules symlink with Turbopack.
tar -C "$web_root" --exclude='./node_modules' --exclude='./.next' --exclude='./.env*' \
  --exclude='./test-results' --exclude='./playwright-report' -cf - . | tar -C "$test_dir" -xf -
cp -a --reflink=auto "$web_root/node_modules" "$test_dir/node_modules"

# A fresh network namespace has no external interfaces; all processes, including
# Next server actions and Chromium, run there with a scrubbed environment.
unshare -Urn env -i PATH="$PATH" NEXT_TELEMETRY_DISABLED=1 NODE_OPTIONS=--dns-result-order=ipv4first \
  PARENTPLUS_SYNTHETIC_BROWSER=1 PARENTPLUS_CHROMIUM_PATH="$chromium_path" \
  NEXT_PUBLIC_ENABLE_LIVE_OTP=true NEXT_PUBLIC_ENABLE_ACCOUNT_SIGNUP=false \
  NEXT_PUBLIC_SUPABASE_URL=http://localhost:3191 NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=synthetic-public-key \
  PARENTPLUS_ENABLE_PARENT_CHILD_LIST=true PARENTPLUS_ENABLE_CHILD_CREATION=true \
  bash "$repo_root/scripts/ci/enabled-parent-browser-inner.sh" "$test_dir"

mkdir -p "$web_root/test-results"
cp "$test_dir/test-results/playwright-enabled-junit.xml" "$web_root/test-results/playwright-enabled-junit.xml"
echo 'PASS: Isolated enabled parent browser checks completed'
