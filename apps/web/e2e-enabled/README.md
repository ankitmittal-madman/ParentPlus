# Isolated enabled parent browser checks

Run from the repository root after installing the web dependencies and Chromium:

```sh
bash scripts/ci/enabled-parent-browser.sh
```

Set `PARENTPLUS_CHROMIUM_PATH` to an existing local Chromium executable if the Playwright-managed browser is unavailable. The runner needs Linux `unshare`, network namespace support, `ip`, Python 3, Node.js and enough temporary space to copy the web dependencies. It first tries an unprivileged user namespace. Where that is unavailable, it can use a short passwordless-sudo bootstrap to create a network namespace and enable loopback; it drops to the original non-root user and group, clears capabilities and verifies the drop before running repository code. It fails rather than skipping the suite if isolation, privilege verification or dependencies are unavailable.

The runner copies the web app to a temporary directory, excludes root `.env` files, scrubs the process environment, then starts the build, Next server, fake provider and browser inside a network namespace with only loopback IP interfaces and routes. The fake session, identities and profile names are synthetic. No actual email is sent. It does not isolate filesystem access or establish that host Unix-domain sockets are inaccessible.

The suite exercises real Chromium-to-Next wiring against a deliberately simplified local provider. It does not verify actual Supabase, signed JWTs, database authorization, database concurrency or hosted behaviour. The existing disabled-feature browser suite remains separate. The JUnit report is written to `apps/web/test-results/playwright-enabled-junit.xml` only after success, and the quality gate requires the exact cases and report digest.
