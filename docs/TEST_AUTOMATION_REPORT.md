# ParentPlus — Test Automation and Simulation Report

Prepared: 2026-11-03. This report explains the automated checks and their scope;
it is not a replacement for the source-bound results of a particular run.

## What the checks simulate

| Check | Example scenario | What it establishes | Limitation |
| --- | --- | --- | --- |
| Browser checks | Invalid email, disabled OTP and the synthetic schedule preview in Chromium | Three limited browser scenarios against a local server | Does not test live delivery, valid sign-in, real scheduling or protected routes |
| Local schedule recurrence | One-off and weekly dates, time zones, DST gaps and overlaps, resource limits | Calendar calculation in a pure local utility | Does not create schedules or enforce backend permissions |
| Synthetic schedule preview | Clearly labelled example schedule, course, batch and session time | Presentation and labelled sample content | Does not test real schedule creation, enrolment, access or persistent data |
| Frontend components and OTP helpers | Invalid email, rejected code, duplicate submission, changing email, session check errors, simulated auth-event and focus-return races, sign-out errors and accessible error feedback | Expected UI and helper behavior with synthetic inputs and mocked providers | Does not send a real email or prove a real provider session |
| Database security | Anonymous access denied, another user's profile hidden, cross-workspace access restricted | Authorization behavior exercised in a disposable PostgreSQL test database | Does not prove hosted Supabase configuration or real signed-JWT integration |
| Database concurrency | Concurrent workspace, child, connection and approval requests; revocation/suspension races | Selected race and idempotency behavior with synthetic records | Does not cover every race or production workload |
| Quality engine | Missing scenario mapping, skipped/failed checks, stale reports and unsafe selection | Deterministic selection and evidence validation rules for tested cases | A selected plan is not evidence of a test run; a local receipt relies on honest execution |
| Frontend lint, types and build | Static checks and production build | Code can be checked and built in the tested environment | Not browser E2E, accessibility certification or production deployment |

The executable scenario identities and their requirement mappings are maintained in
[the registry](../quality/requirements.json). New tests must be mapped and verified
by the existing [quality-gate workflow](INTELLIGENT_QUALITY_GATE.md).

## Automation status

The proposed local change adds browser tests to the frontend job before its success receipt; hosted execution of that change is not yet verified. The GitHub orchestrator selects suites on push, pull request, merge-group and manual
runs; it validates selected evidence before reporting the gate. Authentication changes
select frontend and database security suites. The verified [main-branch run](https://github.com/ankitmittal-madman/ParentPlus/actions/runs/41639620015)
for commit `ff41e3bdeaa1f299d8eec7a631c13f798add3b44` passed selection, frontend,
database and final gate jobs. That historical hosted run does not test later local
uncommitted changes. Branch-protection enforcement has not been verified.

The prior local run of the reconstructed screen passed 28 frontend cases, 39
database cases, four standalone concurrency cases and 49 quality-engine cases;
lint, typecheck and a containerised production build passed. That is historical
for the earlier working snapshot. For current results, inspect the source-bound
local quality summary and receipts under ignored `test-results/quality/` and
`test-results/evidence/`; those files may not survive environment replacement.

## Remaining product and release gaps

The two browser login checks do not cover the full end-to-end journey. Real OTP delivery, template compatibility, live provider
sessions and sign-out, signed-JWT/hosted authorisation, account enumeration and
real family data flows remain unverified. The registry separately tracks planned or
deferred guardian verification, invitation, enrollment, attendance, private media,
retention, guardian history, phone OTP and learning-delivery gaps. The existence of
automation does not mean every product journey is implemented or release-ready.
