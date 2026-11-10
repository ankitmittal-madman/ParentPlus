# ParentPlus — Quality Evidence Index

## Verified enrolment checkpoint — 10 November 2026

Code commit `8f0ae0ef178e8e1909504fdb8c5d27430ac34c48` records the reviewed51-file
change. Pre-commit final-v6 source fingerprint
`3055e142afc0d08958b7e6d95633fce549995bc07f41aaf16db0084e83b52a0c`
passed the combined source-bound gate; this documentation follow-up is separate.
Reports: ignored `test-results/quality/enrolment-final-v6/` (plan),
`enrolment-verified-v6/` (passed gate) and
`test-results/evidence/enrolment-final-v6/` (current reports/receipts).

| Executed check | Result |
|---|---|
| Frontend |384 cases/43 files; lint, TypeScript and production build passed|
| Isolated PostgreSQL |490 unit/integration +4 standalone =494; zero failed/error/skipped; cleanup verified|
| Complete real-local browser report |43 scenarios ×2 viewports =86/86;99 mapped controls; zero action gaps;86 embedded screenshots|
| Other browsers |6 signed-out +6 isolated synthetic-provider +3 real-local email OTP +1 dummy-OTP founder journey passed|
| Tooling |58 engine,17 offline operations,3 browser observer cases passed; workbook ZIP/XML integrity passed|

Full founder report `run-20261110T125133Z-daf7fd` has the same source fingerprint
as final-v6; HTML/Excel/summary copies are in ignored
`work/deliverables/parentplus-enrolment/`. Prior83/86 and85/86 reports remain failed
evidence. Their defects were ambiguous student text, premature founder navigation
and a first-POST fault targeting a background read; the corrected tests retain
actual clicks and immutable retry payload/UUID assertions. Namespace failures
were corrected with an exact synthetic-provider read allowlist and explicit class
refresh. Actual hosted metadata preflight stopped before writes because PG arrays
arrived as text; jsonb_agg plus strict validation reproduced RED and passed17 ops
and a fresh read-only hosted inspect. No assertions, case minima or skips were
weakened. Independent final/scoped reviews passed with no blocking finding.
M1 remains a nonblocking frontend fixture improvement: use unique IDs to isolate
50/100 output-limit proof; SQL bounds are covered and production guards remain.

Migration052 was deployed from an immutable archive of code8f0ae0e to the existing
founder-selected TEST project. All52 history entries and34 public tables were
verified. Original31 public-table and Auth(id/email/created_at) snapshots matched
before/after and again after feature-control activation. Prior receipt preserved;
current private receipt `work/hosted-testing-upgrade-report.json` includes source
commit and post-activation preservation. No reset or existing record rewrite.
GitHub push/CI/merge/Vercel are pending at this entry's preparation; no hosted
browser, real-device install, offline cache or full-app completion is claimed.

## Enrolment loop — focused verification before full gate, 10 November 2026

Backend:49 focused enrolment cases passed on fresh052, with observed blocking
histories. Initial missing-RPC tests failed RED on051. Fresh initialization,
001–013→052 rehearsal and own-fixture cleanup passed. Inventory490 unit+4 standalone
cases;420s full-run budget accommodates new histories without reducing assertions.

Frontend384 passed after I1 fix; covering55, lint/types/inventory passed. Independent
DB review passed. UI review found definite stale/saved-state conflicts froze the
screen; RED reproduction, allowlisted redacted conflict recovery and scoped review
passed. Unknown writes still retain original actor/payload/UUID. M1 Minor remains:
duplicate-row fixture does not independently prove50/100 bounds (code enforces them).

Real local ENROL001–004 passed8 desktop/mobile executions pre-I1 fix; ENROL005
passed2 post-fix with two managers and no stubbed mutation/response: staleversion1
rejected after another actor advances to2; fresh explicit action uses version2/new
UUID. Focused reports mark unselected scenarios NOT RUN; they are not full86-run proof.

PWA001 passed2 browser executions; initial RED was missing manifest, then the obsolete
Apple-meta assertion was aligned with installed Next16's mobile-web-app-capable.
Real-device installation remains unverified. Existing navigation2 tests passed after
SVG/raised-Post styling. Ops15 passed, including RED→GREEN later-table preservation
and changed-record detection. Exact snapshot SQL also read31 local public tables+
Auth successfully, including composite keys, without printing data values.

Local052/history receipt were applied atomically; all31 original public-table/Auth
fingerprints matched. Upgrade preservation now freezes all original public columns
and snapshots canonical rows in one SELECT, then notifies the API schema cache.
Hosted remains051 at preparation; no hosted052 execution is claimed. Full integrated
source gate and publication are pending; earlier results below remain historical.

## Verified academy invitation checkpoint — 2026-11-10

Feature code is committed locally as `ed134cadaa83267ccfc9a9803bffd8d5a924617a`;
original references are in `e3a8c716160b582473f9e61ac5133bdd167b43b7`.
This entry records the verified code checkpoint, not live branch/deployment status.

Owners/admins can share a 14-day single-use invitation from Students. A separate
parent uses the existing dummy OTP, selects an eligible profile they created and
explicitly confirms the academy connection. Both accounts can reload and inspect
the saved relationship through Supabase. New feature controls support EN/HI with
remembered preference. This is the first M2-02/S2-04 and M2-49 slice, not their
full completion: batch enrolment/filtering, second guardians, attendance, diary,
contact permissions, fees and full child snapshots remain future work. A connection
never implies legal verification or media/pickup/fee permission.

Final local source fingerprint:
`66bb44de036e3e61f44b944955479a39905afc4656769c02b8d0946eea14a358`.
The complete quality gate passed with333 frontend,441 database unit and4 standalone
concurrency cases,6 disabled and6 isolated synthetic-provider browser cases,
lint/typecheck/build, and zero residual database records. The source-matched
founder report passed74/74 scenario/viewports (37 scenarios,81 mapped controls)
with zero action gaps and74 embedded screenshots. Its genuine Excel workbook has
six sheets. Operations regressions13, instrumentation browser regressions3 and
quality engine regressions58 also passed. A baseline001–013 upgrade rehearsal
through051 preserved its fictional records. Registry coverage is executable;
future product gaps are kept explicit.

Ignored local evidence: `test-results/quality/family-invitations-cleanup/`,
`test-results/qa/run-20261110T095841Z-4cf29f/` and `/tmp/parentplus-family-*.log`.
These may not survive another workspace; hosted evidence must be checked separately.
The separate founder dummy journey1 and real-local-OTP journeys3 passed before
the final test-fixture-only correction; those reports are historical to their
source and are not re-attested to the final fingerprint.

Independent review found no Critical defect. Its two Important findings were
closed: added observed lock histories for expiry, restriction and different-invite
same-child concurrency; redacted invitation secrets in shareable failure text and
console logs, with an actual failed-navigation harness and HTML/Excel regression.
Additional component tests cover double clicks, uncertain acceptance arguments
and late auth/focus responses. The first complete DB run passed cases but failed
cleanup because14 race fixtures left workspace tombstone receipts. A focused
assertion reproduced RED; fixture-only cleanup corrected it; the fresh full gate
passed with cleanup0. No app data or hosted records were reset by that correction.

The founder authorised commit, push, merge and existing TEST-backend use. The
pre-recovery stash remains preserved. The existing hosted TEST project was upgraded through051 with atomic history
receipt and unchanged original fingerprints across eight application tables plus
Auth. This is not hosted browser evidence. Publication/deployment outcomes are
recorded separately after inspection; a local green gate is not deployed proof.

## Family invitation review and focused checks — 2026-11-10

Fresh independent source review found no Critical defect and identified missing
concurrency histories plus possible invitation-token leakage in failure reports.
The implementation now has 18 isolated SQL cases including observed blocking for
revocation/restriction in both orders, same-token retries, different-invite
same-child acceptance, four expiry lock positions and paginated roster reads.
Focused executions passed. New component/server tests cover identity changes,
late replies, real double clicks and uncertain retry arguments. A rejected
server-action transport was reproduced RED and corrected to preserve explicit
same-request recovery rather than a generic failure message.

The first full database run passed all445 cases but FAILED its cleanup audit:
14 synthetic workspace tombstone receipts remained after the14 new race histories.
A focused reproduction showed one deleted workspace leaving one receipt; an added
cleanup assertion failed RED. The fixture now deletes only its own receipt, and
that regression passes GREEN. This changes test cleanup, not application behaviour.
A complete fresh database gate is required after this fix; no passing gate is
claimed for the first run.

The reporter and console runner redact 64-hex invitation secrets in textual
browser failures. A new offline regression checks HTML, Excel and summary output;
the browser instrumentation harness reproduces a failed navigation diagnostic.
Invite inputs are masked in QA screenshots. Raw Playwright diagnostics stay private
and excluded from upload. Full-suite evidence for the final source is pending;
see the later execution receipt rather than treating these checks as hosted proof.

## Published browser quality checkpoint — 2026-11-10

The founder approved committing/pushing the reviewed testing package and publishing
the testing fix. Code checkpoint `431c0e7d22ba4613a0d9e1542381740013a5978b` is on GitHub main.
All27 approved files were committed; preceding work and the pre-recovery stash
were preserved. Vercel reported deployment completed for this commit.

First independent GitHub browser workflow
[42783630419](https://github.com/ankitmittal-madman/ParentPlus/actions/runs/42783630419)
completed successfully and uploaded
[report artifact13747596711](https://github.com/ankitmittal-madman/ParentPlus/actions/runs/42783630419/artifacts/13747596711).
The workflow enforces66 scenario/viewports and62 controls across both viewports.
The separate full quality workflow
[42783630836](https://github.com/ankitmittal-madman/ParentPlus/actions/runs/42783630836)
passed its plan, frontend, database and final evidence jobs. The GitLab mirror
also succeeded. These are inspected hosted outcomes, separate from local checks.
Artifact metadata confirms the upload; this workspace cannot download the Azure
artifact-storage redirect, so the hosted report bytes were not personally read.

The published workflow is configured for PRs, main pushes, manual runs and daily
00:30UTC/06:00IST. A scheduled trigger has not yet been observed; do not claim
a nightly run occurred. Artifacts retain14days. Download/extract the report in
GitHub to open index.html and ParentPlus-Test-Scenarios.xlsx together.

Migration050 was applied to the EXISTING founder-selected hosted TEST project
fmavpazczahxeusqbxuh. The atomic migration receipt and all50 history entries were
verified. Original row fingerprints across the eight baseline application tables
and Auth accounts matched before/after. A read-only check confirms exact v2
receipt validation is installed, the app recovery RPC is available, and direct
authenticated access to its private helper remains revoked. No reset or record
rewrite occurred. Hosted browser use of the second-class fix remains untested
from this network; the founder's earlier manual confirmation covered the entry
journeys, not this new regression.

Local pre-commit evidence at source fingerprint
`f06d26d86f1a5f9eeacc7a0ae849ad50c42d6b78a335b5c999880041650af370`
passed:316 frontend,427 database,66 new browser,16 existing browser,2 observer,
12 offline operations and58 engine cases; lint/type/build, upgrade rehearsal
and source-bound gate. Reports: ignored test-results/quality/browser-quality-v2/
and work/deliverables/parentplus-browser-quality/. The following documentation
checkpoint does not relabel those local reports as a new source execution.

This remains founder testing. Connection/enrollment is the next product slice;
attendance, diary, fees and the live dashboard remain incomplete. Earlier
pre-publication notes below are historical records.


## Browser quality development — 2026-11-10

Independent review identified two P2 reporting gaps: attribute-only control
reveal could escape discovery, and an empty catalog could pass with zero results.
Both were reproduced and corrected. Added standalone real-Chromium observer
regressions plus empty/mismatched catalog, unmapped control and interrupted-JSON
report checks. The observer now tracks visibility attributes and checks actual
visibility; action coverage requires a mapped passing click on both viewports.
A diagnostic NAV-001 rerun passed2/2 after checking native menu open state; its
full-catalog report correctly remains failed with64 other cases NOT RUN. The
earlier broader run passed64/66 with only that menu-test assumption failing.
The second-class SQL regression and full427-case database suite passed before
these report-only review fixes. Final complete source-bound reruns follow.


Founder manually confirmed the deployed parent/coach entry journeys work for an
initial check. GitHub quality run42761558562 for523efba completed successfully.
New work adds33 catalogued browser scenarios across desktop/mobile (66 runs),
Excel/HTML reports with synthetic screenshots and an additive daily/PR/push/manual
GitHub workflow. See [Browser Testing](BROWSER_TESTING.md). Workflow publication
and active scheduled execution are pending; this source remains uncommitted.

The tests found a genuine second-class recovery defect. A forward-only050 fix
recognises exact v2 provenance while retaining existing access/legacy checks. Its
isolated SQL reproduction failed against029 and passed against050; missing or
mismatched receipts remain rejected. Applied050 only to checkout-owned local
Supabase. Hosted testing remains at the previously applied049 until a separate
publish/upgrade step. No existing rows were rewritten or reset.

Exploratory evidence includes a62/66 browser run; its four remaining test-harness
assumptions were corrected. Final source-bound QA/full regression and independent
review follow; those exploratory reports are not re-attested as current success.
Prior commits and pre-recovery stash are preserved. Connection/enrollment remains
the next product slice after this testing checkpoint; attendance, diary, fees and
the live dashboard remain incomplete.


## Current-source founder testing verification — 2026-11-10

Implementation checkpoint: df2b976 (full SHA available from Git). The complete
pre-commit snapshot passed the source-bound gate at fingerprint
`ba19f7c9d4fd36e59d1a32a9f45553d213b6a4094b3d6591e03c57e9befb5930`.
This following documentation update does not reuse those receipts as a new run.

Verified results:316 frontend cases across37 files;425 isolated database cases
(421 unit/integration +4 concurrency), zero failed/error/skipped cases;58 quality
engine regressions;1 supplemental offline operations regression. Lint, TypeScript,
normal production build and Vercel-style testing production build passed. Browser
coverage:6 disabled-provider +6 isolated synthetic-provider +3 real local OTP
journeys +1 dummy-OTP real local DB journey. The last two suites are supplemental
to the v1 gate and are not silently counted in its frontend inventory.

A production-build browser smoke check confirmed the founder banner, dummy-email
request and wrong-code rejection. A server-key sentinel was absent from browser
assets. This did not attempt hosted session exchange.

Independent hosted-testing review found no critical/high defect. The missing
receipt-directory defect was reproduced, fixed before hosted operations, and its
offline regression passed. Obsolete separate-backend/marker documentation was
reconciled to the latest founder instruction. Earlier reviews covered pagination
and cross-tab recovery fixes.

Ignored receipts/reports: `test-results/quality/hosted-founder-testing/` (plan,
verification, source-bound reports, supplemental report hashes). Hosted migration
receipt: `work/hosted-testing-upgrade-report.json`, status passed,49 migrations,
original row fingerprints preserved. Private credentials are excluded from Git.

Founder confirmed Vercel key in Preview/Production. Deployment is authorised and
publication is next. Actual Vercel result, hosted login/session exchange and
hosted CI are not established by these local checks. Workspace network policy
currently blocks direct Vercel/project-API requests; GitHub deployment status can
be inspected. Preserve the pre-recovery stash. Launch and unfinished product
areas (enrollment, attendance, diary, fees) are not claimed complete.


## Hosted founder testing preparation — 2026-11-10

The founder explicitly selected the EXISTING Supabase project
`fmavpazczahxeusqbxuh` as the testing backend, superseding the earlier instruction
to leave hosted Supabase unchanged and the separate-project proposal. No new
account or paid service is needed. The existing GitHub→Vercel route is authorised
for deployment; unavailable Vercel integration must not be chased.

The hosted test database was upgraded from001–013 through049 with atomic migration
receipts after a synthetic upgrade rehearsal. Original row fingerprints across
eight application tables and Auth accounts were unchanged. Four implemented-feature
controls are enabled. No database reset, deletion or Auth provider change occurred.
See ignored `work/hosted-testing-upgrade-report.json` for the operation receipt.

Prepared Vercel testing defaults enable fictional .test email/123456 login and
implemented parent/coach features. The selected backend is pinned. The private
service credential remains runtime-only. The founder screenshot confirms
`PARENTPLUS_TEST_SERVICE_KEY` exists in Preview and Production; its value has not
been inspected. Current-source regression and actual deployment checks are pending.
No claim of published login success is made. Earlier local-only evidence below is
historical. Students/enrollment, attendance, diary and fees remain incomplete.


## Founder dummy-OTP sandbox — 2026-11-09

The additional founder browser scenario passed against actual local Auth and
PostgreSQL with dummy .test email/code 123456, UI-created child/workspace/weekly
classes and founder-driven suspension/restoration. This avoids external identity
verification and mailbox steps; it does not mock database persistence or ordinary
user sessions. Twelve new unit cases plus focused existing auth regressions passed;
lint and TypeScript passed. Full current-source reports/receipts use the separate
`test-results/quality/founder-testing/` plan; previous first-use receipts are historical.
Independent review found account/workspace selectors stopped after 100 rows. A
new regression failed before pagination and passed afterward. The launcher now
holds a shared feature-control lease; a competing launch was verified to fail
before any control changes. Browser assertions read back the saved child and
exactly three persisted weekly sessions after restored access.
No hosted data/configuration was changed. Local founder controls are a deliberate
development-only administrative capability authorised by DEC-021.


## Real local first-use verification — 2026-11-09

Recovery base: `010fd412d034f3e8e7545c235b824e9e6ac36bdb`, branch `work`, with
uncommitted recovered and new scope. Current-source receipts/fingerprint are
produced by the full final plan under `test-results/quality/local-first-use/`;
reports are ignored and are not portable evidence simply because this doc exists.

Observed local runs passed 296 frontend cases across 32 files, lint, TypeScript,
production build, 421 isolated database cases, four standalone concurrency
scenarios, all 425 database JUnit cases and cleanup. The recovered 001–013-to-049
synthetic upgrade rehearsal passed. Actual local Supabase applied all 49 migrations.

Three Chromium journeys passed with real local Auth emails, signed user sessions,
Mailpit, PostgREST and PostgreSQL: parent, independent coach, academy owner. Six
production-build browser checks with OTP disabled passed. The six synthetic-provider
recovery scenarios passed inside their required loopback-only namespace after
retrying outside the command sandbox; its isolation checks were retained.
New E2E JUnit is `apps/web/test-results/local-e2e-junit.xml`; existing browser and
unit reports retain their original names. The v1 quality gate does not collect the
new local E2E scenarios automatically, so their separate invocation remains required.

Independent read-only review found the cross-tab marker race; a regression failed
before correction and passed with browser-lock allocation and a fresh marker
comparison. The reviewer also noted missing academy-type coverage; the real suite
now covers both workspace types. Fix verification was by the implementer, not a
second independent reviewer. The real join ambiguity reproduced as PostgREST
PGRST201 before the FK-qualified query correction.

No hosted database or hosted CI was contacted for validation. Local feature
controls were restored, synthetic rows remain for inspection, and no existing
records/containers were reset. See [full scope and limits](LOCAL_FIRST_USE_VERIFICATION.md).


This is the canonical index of verification provenance and known availability,
not a replacement for raw results, the requirements registry or historical audits.
Update after quality checks. Distinguish a plan, an execution, an approval, a local
commit and a hosted result. No connector or CI result is inferred from a document.

## Signed-in coach navigation — local verification, 2026-11-08

The frontend suite passed 284 tests across 29 files. Focused login and coach
access tests passed 57 tests across two files. ESLint on the modified login
files and the application typecheck passed. The new login test verifies the
coach-area link after a mocked confirmed session and its absence during and
after sign-out; an existing signed-out test verifies that it is hidden. Server
membership checks are exercised separately using mocks. This is not real
provider, hosted or browser verification, and does not establish workspace
creation or first-use journey completion.

The isolated local PostgreSQL gate also applied all 49 migrations from an empty
database, passed 421 database tests and four additional concurrency scenarios,
validated 425 JUnit cases and verified cleanup. This is fresh-baseline evidence,
not a rehearsal of the current hosted database upgrade or approval for rollout.

Separately, a network-isolated PostgreSQL 17 rehearsal of the reported 001–013
baseline with selected fictional workspace, membership, child and guardianship
records applied 014–049 and checked those records survived with creation
controls disabled. Auth was a synthetic fixture, not Supabase Auth. The hosted
state, other data shapes, partial failure, backup and real JWTs were not tested.

## Class setup with weekly sessions — local verification, 2026-11-07

Fresh network-isolated PostgreSQL 17 initialization applied all 49 migrations.
The full database suite passed 421 unit tests and four standalone concurrency
scenarios; JUnit validation passed all 425 cases and the cleanup audit found
zero residual records. Coverage includes bounded weekly creation in the
academy time zone, explicit zone selection, atomic rollback for daylight-saving
gaps and folds, denial of the legacy partial-completion RPC, permission and
default-off checks, same-schedule retry, and concurrent duplicate completion.
The frontend suite passed 283 tests across 29 files. ESLint, Next.js route type
generation/typecheck, production build and six standard Chromium browser cases
passed. Quality-gate self-test passed 58 cases.

The enabled synthetic-provider browser runner was attempted with local
Chromium, but this environment cannot safely create the required network
namespace. Therefore the source-bound full frontend receipt cannot be
generated. These are local synthetic checks; no hosted migration or data was
changed, and class setup remains default-off. An independent review found the
legacy completion RPC bypass and silent browser-time-zone default; this patch
revokes the old RPC, requires explicit zone selection, and adds regression
tests. Follow-up review is pending. Schedule editing/cancellation and retention
policy remain open. Raw JUnit files are ignored local artefacts under
`test-results/database/` and `apps/web/test-results/`.

## Coach route access — local verification, 2026-11-07

Against its earlier local integration source, the web suite passed 273 tests
across 28 files; ESLint, Next.js type generation/typecheck and the production
build passed. Six Chromium browser cases passed with live OTP disabled, including
anonymous redirects from the coach home and schedule. The quality-gate self-test
passed 58 cases. Isolated PostgreSQL applied all 47 migrations, passed 412
database unit tests and four concurrency scenarios, and verified cleanup. The
database suite includes a check that app roles cannot create unreserved
courses/batches even if the old flag is enabled.

The isolated synthetic-provider browser runner did not run because user/network
namespace creation is unavailable in this environment; its safety checks were
not bypassed. Therefore a complete frontend execution receipt and full gate
verification are unavailable. Live email delivery, a real signed JWT/provider,
hosted CI, hosted migrations and deployment were not verified. An independent
code reviewer was not available in this session. The class setup flow remains
disabled pending the documented cross-manager reservation/recovery race fix.

## Recorded local implementation verification

| Field | Recorded value |
| --- | --- |
| Execution record baseline | ac2b1f9af85b531142310fcd851a24c17390f4ae, before the quality-gate commit |
| Source fingerprint | 70088b03963e79bd2993f5ffef801e3257eb28b48d09992d5b96ae3deb7447f7 |
| Subsequent local checkpoint | 5b068b995957414a47dd2f47e8b6eb4147958563 |
| Provenance reconciliation | This session reconstructed the committed 5b068b9 file fingerprint and confirmed it matches the execution record |
| Raw record | test-results/quality/audit/verified/quality-gate.json; ignored local artefact, not guaranteed present in another checkout |
| Independent review | Recorded in the versioned audit below; it is a prior review, not a new review of these documentation additions |

| Recorded check | Outcome | Limit |
| --- | --- | --- |
| Strict quality-engine tests | 49 passed | Prior execution; no claim the new docs have a fresh full-gate pass |
| Frontend | 24 tests, lint, type check and build passed | Mocks/component tests; not live OTP or E2E |
| Database | 39 unit cases and four standalone scenarios passed | Synthetic auth, isolated PostgreSQL; not hosted JWT/production authorization |
| Database setup/cleanup | 13 migrations applied locally; no residual test data | Not a migration deployment approval |
| Adversarial evidence checks | Source/receipt/report mismatch cases rejected | Local caller declarations still require an honest process and review |

Detailed findings, gap dispositions and original validation are owned by
[the independent audit](INTELLIGENT_QUALITY_GATE_AUDIT.md). The
[initial implementation report](INTELLIGENT_QUALITY_GATE_REPORT.md) is historical.
The [gate guide](INTELLIGENT_QUALITY_GATE.md) owns commands and evidence formats.
Counts here describe that recorded run; executable inventory is authoritative for
future counts, not a permanent numeric threshold in this document.

## Current documentation foundation

Scope is listed in [the handoff](AGENT_HANDOFF.md). Local documentation validation
on 2026-11-03 checked 14 Markdown files and 78 local file/directory links, preserved
the existing root/communication instructions and historical contract text, and
confirmed protected implementation files were unchanged. Whitespace and exact
Git-scope checks passed. These are local checks, not an installed CI checker.

A fresh strict engine self-test passed 49 cases. Registry/policy validation also
succeeded and produced a selection plan; it selected quality, frontend and database.
The latter two suites were not executed for this foundation. Temporary local
validation output is under /tmp/parentplus-context-foundation-checks; it is not a
portable GitHub artefact or a complete passing quality-gate record.

A separate read-only reviewer inspected the documentation and found an Important
Claude bootstrap-path omission. The entrypoint now explicitly names the shared
bootstrap and Claude adapter; both files exist and their links were checked. The
wording fix is verified locally, not by observing a future Claude session. Minor
duplicated Git-state and package-version details were reduced. Application and
future cross-agent behavior are outside that review's execution scope.

The current draft's source snapshot differs from the recorded implementation
snapshot above. Do not copy its old reports into a new receipt or claim they
validate this draft.

Application/database execution and hosted CI have not been rerun for this
foundation. Existing policy still selects broader regressions for root agent
instruction changes; that policy is unchanged. A local selection plan would not
establish those selected suites passed. The proposed documentation CI checker is
not implemented in this phase.

## Availability and sharing

- Versioned audit/report summaries survive an approved commit and publication. Raw test-results directories are ignored; another assistant must report them unavailable unless supplied or retrieved through authorized access.
- Existing workflow definitions retain hosted artefacts for 14 days. Their presence, URL, run/attempt and conclusion must be inspected; no hosted run URL is currently attested here.
- Preserve a sanitized durable summary of important run outcomes and source identity. Do not publish secrets, personal data, full environment dumps or private chats as evidence.
- A bundle of local results must identify branch, preparation baseline, source fingerprint, environment, dirty scope and omissions; it is not automatically the GitHub-published state.

## Future record contract

For each meaningful check, record date/environment, what ran, command or runner,
source baseline and fingerprint, result and actual case counts, skipped/failed/
expected-failure/unrun outcomes, artefact location/access/retention, review scope
and outstanding risks. Add real hosted run/attempt/commit links only after they
are inspected. Keep this index concise and link detailed feature reports.

Do not close broad security checklist items just because a narrower test passed.
The ten product gaps and their conditional release blockers remain in the audit
and registry; the documentation foundation changes none of their statuses.

## Reconstructed email verification screen — local scope

The reconstructed uncommitted slice uses mocked UI verification and keeps live OTP disabled by default. New scenarios cover accepted/rejected verification, field-associated errors, changing the email and concurrent submission; the successful state also receives keyboard focus. The initial focused tests failed because the code field was absent; the separate focus regression failed before its fix. Inspect the current local quality plan and reports for exact snapshot results; earlier environment results do not attest to this reconstructed work.

An independent reviewer identified incomplete session-aware continuation and sign-out, provider template compatibility, and potential account enumeration when provider responses differ for unknown accounts. These remain open for the live sign-in slice; no hosted provider was contacted. Complete sign-in browser E2E and real-provider sign-in remain release gaps.

## Browser test and evidence extension — local scope

The initial two Playwright scenarios exercise the login page through a real local Chromium browser with OTP disabled: invalid email and the disabled-provider response. Browser page requests outside the fixed localhost origin are intercepted, but this is not an operating-system network sandbox. The frontend CI workflow was changed locally to install Chromium and run these checks before attesting; the change has not been verified on GitHub.

An independent reviewer identified that skipped browser tests could otherwise appear as a successful frontend job. The quality gate now requires a Playwright JUnit report containing exactly the required cases, including the synthetic schedule preview, with no skipped, failed or missing results, and binds its digest in the frontend receipt. Regression tests exercise absent, skipped, wrong-case and altered evidence. A reviewer rechecked the correction and reported no remaining blocking finding in that scope. Inspect the current source-bound summary for the full run; hosted CI for this change, complete sign-in, live OTP and session behavior remain unverified.

## Local sign-out — current scope

The local screen and helper cover current-session sign-out after successful verification, generic failure handling and duplicate-submission protection using mocked provider responses. An independent reviewer found the SDK can remove local state before returning a provider error. A synthetic-fetch test using the actual SDK reproduced this; the screen now reports uncertainty rather than claiming an active session, and successful sign-out restores keyboard focus. The reviewer rechecked the correction and found no further important issue in this local slice. Inspect the source-bound local gate for current results. A local sign-out request is not proof of global device revocation, live provider behavior, session restoration or access authorization.

## Session restoration — current local scope

The local login screen uses provider `getUser` to choose between a signed-in display, sign-in form for a missing session, and a fail-closed retry for provider or configuration failures. Tests use mocked results and disabled mode makes no provider call. An independent reviewer identified that provider identity alone does not prove email verification; the screen now uses neutral signed-in wording, and retry focus was corrected. Inspect the current source-bound gate and final review for exact results. Cross-tab changes, expiry over time, live provider integration and server-side authorization remain unverified release gaps.

## Synthetic schedule preview — local scope

The schedule component and local Chromium tests cover the example-data notice and labelled list of course, batch and example session time. They do not establish backend scheduling, child access, enrollment or browser E2E for real scheduling. Inspect current local quality evidence and independent review for this source snapshot.

## Session-change safety — current local scope

Auth event handling is tested with synthetic notifications and deferred promises, including stale session/OTP results, sign-out failures during account changes, prior-email clearing, provider revalidation and unsubscribe. Independent review found account-switch and stale-email races; regression tests reproduced them and the revised implementation was rechecked. Exact current results belong to the source-bound gate summary. Mocked notifications do not establish live cross-tab delivery, remote revocation, timely expiry, or authorization of protected data.

## Session resume revalidation — local scope

When live authentication is enabled, returning focus or visibility triggers a recheck; disabled mode does not check. A signed-out user’s OTP entry or in-flight request is preserved if the provider confirms signed-out state. Tests use deferred promises for events overtaking older checks. Tests use synthetic focus events and mocked provider responses. Current source-bound gate evidence and independent review determine the result for the working snapshot. This is not continuous expiry monitoring, verified real cross-tab delivery, remote revocation or authorization to child/workspace data.

## Scheduling recurrence foundation — local scope

A pure local utility and tests cover one-off and bounded weekly recurrence, IANA time zones, daylight-saving gaps and overlaps, offset changes, elapsed duration, invalid input and occurrence boundaries. An independent reviewer found no material defect in the initial implementation and requested additional boundary coverage, which was added. The utility is not a backend authorization mechanism and is not integrated with persistent schedules. Inspect the current source-bound gate and independent re-review for exact results; hosted, UI and database scheduling behavior remains unimplemented.
