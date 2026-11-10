# Local Supabase and browser journeys

All commands use synthetic local data. Never run hosted migrations, reset a
hosted project, or copy service keys into the frontend.

From the repository root:

```sh
bash scripts/dev/local-supabase.sh start
python3 scripts/dev/local-e2e.py
bash scripts/dev/local-supabase.sh status
```

Prerequisites: local Docker socket, Node/npm, Python 3, and Chromium (default
`/usr/bin/chromium`, override with `PARENTPLUS_CHROMIUM_PATH`). Frontend packages
must match `apps/web/package-lock.json` (`npm ci` in that directory). The start
script pins Supabase CLI 3.1.0 and uses slim images to avoid VFS disk exhaustion.
It excludes services the auth/database journeys do not need. Registry redirects
may need additional permitted domains; the CLI's permitted GHCR fallback worked
in the development environment.

Startup saves local credentials privately under ignored `work/`; do not share
`work/supabase-start.log` or `work/local-supabase.env`. The Auth repair recreates
only the local Auth container whose project and checkout labels match this
repository, preserving its image, mounts and network configuration. It adds
exact internal service names to NO_PROXY and makes BusyBox's fixed loopback
health request bypass the inherited proxy. It then requires healthy Auth and a
successful API health response; it does not treat ignored startup health as proof.

The browser runner verifies exact local endpoints and checkout-owned containers,
removes hosted Supabase environment variables, and enables application flags only
for its child process. Tests enable the local database controls and restore their
previous values afterward. They use actual Auth email codes from local Mailpit,
user sessions, PostgREST and PostgreSQL. No service key is used by the app or tests.
Browser requests outside the local app/API are blocked; traces/videos/screenshots
that could retain OTPs or cookies are disabled. Test reports are ignored under
`apps/web/test-results/`.

Synthetic accounts, profiles and schedules are retained in the local database
for inspection. Tests use unique accounts and do not reset or delete existing
records. The parent journey does not connect children to academies or verify legal
guardianship; the coach journey creates workspace/course/batch/weekly sessions.
Production enablement, retention decisions, hosted rollout and cross-device
lost-request-key discovery remain outside this verification.

`bash scripts/dev/local-supabase.sh stop` stops this project's services and retains
local data. Never add a reset flag to recover a failed journey.

## Manual founder testing

Run `python3 scripts/dev/founder-app.py` after local Supabase startup, then open
`http://127.0.0.1:3193/founder`. Use any fictional `.test` email (for example
`parent@example.test` or `coach@example.test`) and OTP `123456`. No mailbox step is
needed. Sign-in establishes an ordinary local Supabase session so product reads
and writes still reach the actual database. The local service key stays server-side.

The launcher enables the implemented features and their local database controls
until it exits. Stop it with Ctrl+C to restore prior control values; existing test
records are retained. The founder page shows saved-record counts and permits
synthetic account membership changes, including restoring access after suspension.
The console is explicitly local/development-only and cannot operate against hosted
endpoints or production. `python3 scripts/dev/founder-app.py --test` runs its real
browser-to-database journey, including founder access overrides.

Students/enrollment, attendance, diary and fees remain incomplete product workflows;
the sandbox does not turn their placeholder screens into completed features.

Only one manual founder app or real local browser runner may own feature controls
at a time. Stop the manual app before starting those automated checks; a second
launcher refuses safely and leaves the running app unchanged.
