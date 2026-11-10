# Local first-use verification — 2026-11-09

Branch `work`, baseline/current HEAD
`010fd412d034f3e8e7545c235b824e9e6ac36bdb`. All task changes are uncommitted.
The initial clean checkout at `ff41e3b` was missing the previous work. After
history/ancestry checks it was fast-forwarded to the supplied recovery base;
all seven files in the complete recovery patch were reconciled. Preliminary
session edits are preserved in the named pre-recovery stash.

## Verified scope

- Parent: explicit account creation, rejected incorrect code, genuine local email
  OTP, child creation with provisional/self-declared guardianship, reload recovery,
  confirmation, own-profile listing, unrelated-account isolation and sign-out.
- Independent coach and academy owner: signup/OTP, no-membership gate, workspace
  creation through the UI, same-request reload recovery, course/batch/three weekly
  sessions in Asia/Kolkata, reload recovery, acknowledgement without extra sessions,
  membership suspension and anonymous access denial.
- Local setup: real Auth/Mailpit/PostgREST/PostgreSQL, all 49 migrations and verified
  health. Fixed exact local proxy/template-read failures without changing hosted
  settings or disabling remote TLS checks. Slim images avoid VFS disk exhaustion.

## Evidence and reproducible commands

| Check | Observed result |
| --- | --- |
| Frontend unit/integration suite | 296 passed across 32 files |
| ESLint, TypeScript, production build | Passed |
| Network-isolated PostgreSQL gate | 421 unit cases + four standalone scenarios; 425 JUnit cases and cleanup passed |
| Real local Supabase browser suite | Three journeys passed |
| Production-build browser suite, OTP disabled | Six passed |
| Namespace-isolated synthetic-provider browser suite | Six passed; outside command sandbox, with isolation checks retained |
| Recovered 001–013-to-049 upgrade rehearsal | Selected fictional records preserved; creation controls disabled |
| Hosted endpoint guard | Rejected before local fixture access |
| Independent review | One important marker race fixed with failing/passing regression; academy coverage added |

Use `scripts/dev/README.md` for setup. Real-provider command:
`python3 scripts/dev/local-e2e.py`. Other commands:
`npm test`, `npm run lint`, `npm run typecheck`, `npm run build`,
`npm run test:e2e` from `apps/web`; and
`bash scripts/ci/database-quality.sh`,
`bash scripts/ci/rehearse-first-use-upgrade.sh`,
`PARENTPLUS_CHROMIUM_PATH=/usr/bin/chromium bash scripts/ci/enabled-parent-browser.sh`
from the root. Browser/build commands need `NEXT_TELEMETRY_DISABLED=1` and, in a
restricted home filesystem, a writable `XDG_CONFIG_HOME`. Default browser/build
checks use `NEXT_PUBLIC_ENABLE_LIVE_OTP=false`.

The final full quality plan and receipts bind a nonignored source fingerprint
under `test-results/quality/local-first-use/`; ignored reports are local and not
portable by this document alone. The new local E2E JUnit report is additional
acceptance evidence, not automatically enforced by the existing v1 selector.
Do not infer hosted CI from these executions.

## Scope and review

Restored files: login page/test, handoff/progress/evidence, first-use rollout doc
and upgrade-rehearsal script. New/changed implementation includes loopback URL
validation, explicit workspace-membership FK selections, default-off coach
onboarding actions/form/route/navigation, real local browser configuration and
journeys, local setup/proxy repair/endpoint guards, local OTP template/config,
unit regressions and requirement mappings. Canonical architecture, scenario,
security and progress documents were reconciled. Dependency lockfiles and the
49 existing migrations were not changed.

Independent reviewer `review_local_journeys` identified a delayed status response
that could replace another tab's durable request key. Its regression failed
before the fix and passed after Web Lock allocation plus a fresh storage comparison.
Browser environments without locking fail closed. The minor academy-type coverage
gap was closed by the third real local browser journey. Fix verification is by
the implementer; no second independent review is claimed.

## Boundaries

No hosted Supabase mutation, reset, migration, deployment, commit or push occurred.
No real family data was used. Synthetic local records and mailbox messages remain
for inspection; tests restore prior control values and do not delete existing data.
The original stopped `parentplus-pg-test` container remains intact. Default app
flags and all four local database controls remain off after testing.

Workspace recovery covers a retained same-device request key. Lost-key discovery
across devices, global duplicate-workspace reconciliation, account lifecycle,
retention, guardian disputes, invitations/connections/enrollment and later learning
features are separate work. Local first-use success does not approve hosted rollout
or complete M2/M3, child privacy review or production readiness.
