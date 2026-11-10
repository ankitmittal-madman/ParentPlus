# ParentPlus Build Progress

## Parent Home and session reports — verified local slice, 10 November 2026

Parents can navigate to real saved attendance, weekly facts and their own reports
by child/academy/class/date. Four report types persist separately from attendance;
correction, pause history, same-request recovery and cross-family denial are
covered by signed local browser journeys. EN/HI navigation and safe unknown-item
fallback are implemented. Local checks:528 frontend,602 DB,104 browser executions
passed; the last Hindi action-report mapping has a passing focused retest.
Final-head GitHub/report checks and exact360 capture remain pre-merge checks.
See [checkpoint evidence](quality/2026-11-10-parent-attendance-checkpoint.md).

Diary/media/AI/reminders/fees and broader family operations remain unfinished.
This supersedes preparation statements below; no full-app or launch claim is made.


## Parent attendance Home — reconstructed, verification in progress — 10 November 2026

Published coach/database checkpoint PR6 is merged at c5f2d7a; main quality and
browser workflows succeeded and Vercel reported success. Those results predate
the new parent screen and do not verify its hosted journey.

The replacement workspace initially lacked uncommitted parent work; it was
reported missing, then reconstructed against c5f2d7a. Fresh526frontend cases,
lint, types and build pass. The local Supabase stack is healthy with53migrations;
this recovery made no hosted database changes. Parent Home now has saved
attendance/week facts, own session reports, safe typed-item fallback, EN/HI copy
and profile navigation. These changes remain uncommitted and under review.

The first real-local parent diagnostic passed4/6 executions: complete signed
coach/parent attendance and uncommitted retry passed on desktop/mobile. Committed
report recovery after reload failed on both because the enabled first Check was
invalidated during automatic scope loading. Independent review also found a
Refresh-during-class-load dead end. Both are being fixed with regressions before
current full-suite/browser evidence and publication. Diary, media, reminders,
fees and the remaining founder catalogue are still incomplete.


## Coach attendance source verified; GitHub publication next — 10 November 2026

Local code checkpoint e441a3e delivers real academy-local Today and explicit full
roster marks/save/corrections/recovery.477frontend/602DB and92real-local browser
cases passed; independent review fixes are verified. A report-only missing batch
mapping was reconciled against real recorded clicks, with runtime provenance
preserved. Follow-up catalogue/docs still require fresh GitHub checks before merge.
Existing TEST Supabase is053 with original data signatures preserved. New frontend
Vercel publication is pending. Parent home/quick signals/item fallback/fullAT13
are still next; this is a partial slice of the larger attendance plan.


## Coach attendance checkpoint in preparation — 10 November 2026

The founder requested commit, push and merge of the work completed so far, then
continued development. This splits the larger attendance plan at its reviewed
coach/database boundary; the entire attendance feature is not complete.

Migration053 and real dated Today/coach roster editing are implemented locally.
Independent DB and coach reviews passed after fixes. The existing TEST backend
still has052 at this preparation point. Parent home, quick-signal controls, safe
item rendering and the complete parent–coach attendance journey remain Task3/4.
The new private signal/feed/week RPCs are DB-tested foundations for those screens.
A previous full local DB run passed602 cases; final checkpoint regression,
publication and hosted upgrade outcomes must be read in Quality Evidence.
No attendance is invented/backfilled. The coach explicitly confirms the whole
roster; reports never count as attendance. HTML/Excel now separates all58 canonical
founder requirements from actual browser pass/fail totals.


## Enrolment and app-shell loop — verified checkpoint, 10 November 2026

This loop adds migration052 and explicit child-to-batch enrolment, pause/resume/
completion/withdrawal, parent class visibility and a batch-filtered manager list.
Connection alone creates no enrolment. Trial/re-entry and full child snapshots
remain. New copy is EN/HI; founder dummy sign-in/invitation flows remain working.

The visual foundation uses Coach/Tutor outline icons, a raised teal Post action,
rounded cards and batch chips. Public standalone manifest/PNG/Apple metadata load
in desktop/mobile tests. No service worker/private-data cache is added; real-device
installation and offline capture remain separate verification/features.

Code8f0ae0e passed the full source-bound gate and86/86 real-local browser
executions with zero action gaps. Migration052 is applied locally and to the
existing founder-selected TEST backend with original records preserved. See
Quality Evidence for exact reports/limits. PR5 merged34ed00f; main quality/browser runs42823121131/42823121370 passed and Vercel reported deployment success. Hosted browser use remains unverified here. Attendance development follows the partial checkpoint above.

## Continuous development loop — founder direction, 10 November 2026

The founder requested continued development across the app, using the references
primarily as feature requirements and the Coach/Tutor HTML as the main visual
reference. Codex chooses sound engineering implementation and continues routine
loops without approval pauses. Existing approval/engineering rules and prior
commit/push/merge/testing-backend authorisation remain in force.

Each loop: requirements → real DB contract → working frontend → automated
scenarios/screenshots → independent review → required regression → publish
verified checkpoint → next dependent feature. A provider-dependent capability is
not labelled delivered until its integration is exercised; continue independent
features while the concrete missing account action is requested.

All58 Class Diary feature IDs are tracked below, including later-stage features.
Pilot requirements determine build order; an older P0 fee label does not move fees
ahead of the core attendance/update journey. This is a requirements inventory,
not a completion percentage or assertion that every prototype button works.
Foundation PWA/language/onboarding and test infrastructure remain part of the
roadmap alongside this catalogue. The original documents remain unchanged.

| ID | Founder feature requirement | Reference priority | Build group | Current evidence/status |
|---|---|---|---|---|
| M2-01 | Batches and recurring schedule | P0 | 1 Class setup | Partial: course, batch and one-weekday series saved; richer recurrence/venue/holiday management remains. |
| M2-02 | Guardians and multi-child families | P0 | 1 Class setup | Partial: own child profiles and single-use academy invitations; second guardians and full permissions remain. |
| M2-03 | Enrolment lifecycle (trial, active, paused, left) | P1 | 1 Class setup | Verified active/pause/resume/complete/withdraw with versioned recovery; final v6 gate passed and TEST052 applied with existing data preserved. Trial/re-entry remain; PR5 merged and main CI passed. |
| M2-04 | Next-class reminder (auto-drafted) | P0 | 6 Reminders/schedules | Not implemented; queued in dependency order. |
| M2-05 | Schedule changes (cancel, restore, move, extra class, holiday) | P0 | 6 Reminders/schedules | Not implemented; queued in dependency order. |
| M2-06 | Parent quick signals (running late, missing today, dropped off) | P0 | 2 Attendance/Today | Parent quick-signal UI reconstructed with four report types and real local persistence; first-click reload recovery fix/review and final full regression remain. |
| M2-07 | Holiday and break calendar | P1 | 7 Remaining family/operations features | Not implemented; queued in dependency order. |
| M2-08 | Rain check for outdoor classes | P2 | 7 Remaining family/operations features | Not implemented; queued in dependency order. |
| M2-52 | Family calendar sync and clash flags | P1 | 7 Remaining family/operations features | Not implemented; queued in dependency order. |
| M2-09 | Fast attendance with smart defaults | P0 | 2 Attendance/Today | Partial verified slice: local coach marks/corrections/recovery,477frontend/602DB/92browser cases; TEST053 preserves original data. Parent home/fullAT13 and GitHub publication remain. |
| M2-10 | Auto-attendance from signals (suggest, coach confirms) | P1 | 7 Remaining family/operations features | Not implemented; queued in dependency order. |
| M2-11 | Safe drop-off and pick-up log | P1 | 7 Remaining family/operations features | Not implemented; queued in dependency order. |
| M2-12 | Attendance patterns and drop-out alerts | P1 | 7 Remaining family/operations features | Not implemented; queued in dependency order. |
| M2-13 | Auto-drafted class update (from the session plan) | P0 | 3 Updates/feed | Not implemented; queued in dependency order. |
| M2-14 | Voice-to-update (speak, don't type) | P0 | 5 AI/observations | Not implemented; queued in dependency order. |
| M2-15 | Photo captions from the session plan | P1 | 7 Remaining family/operations features | Not implemented; queued in dependency order. |
| M2-16 | AI polish and parent preview | P0 | 3 Updates/feed | Not implemented; queued in dependency order. |
| M2-17 | End-of-day review queue | P1 | 7 Remaining family/operations features | Not implemented; queued in dependency order. |
| M2-47 | Try-at-home activity | P0 | 3 Updates/feed | Not implemented; queued in dependency order. |
| M2-18 | Spotlight rotation (who to observe today) | P0 | 5 AI/observations | Not implemented; queued in dependency order. |
| M2-19 | Quick child observations | P0 | 5 AI/observations | Not implemented; queued in dependency order. |
| M2-20 | AI-written personal note for each parent | P0 | 3 Updates/feed | Not implemented; queued in dependency order. |
| M2-21 | Child progress timeline | P1 | 7 Remaining family/operations features | Not implemented; queued in dependency order. |
| M2-22 | Focus and growth-area patterns | P1 | 7 Remaining family/operations features | Not implemented; queued in dependency order. |
| M2-23 | Monthly progress report | P1 | 7 Remaining family/operations features | Not implemented; queued in dependency order. |
| M2-24 | Parent reactions and check-ins | P1 | 7 Remaining family/operations features | Not implemented; queued in dependency order. |
| M2-49 | Student directory and child snapshot | P0 | 1 Class setup | Partial: connected-child roster plus local batch enrolment/filtering; attendance/update/fee snapshots remain. |
| M2-25 | Consent manager (per child, per media type) | P0 | 4 Consent/media | Not implemented; queued in dependency order. |
| M2-26 | Quick capture during class | P0 | 4 Consent/media | Not implemented; queued in dependency order. |
| M2-27 | Tag children and share safely | P0 | 4 Consent/media | Not implemented; queued in dependency order. |
| M2-28 | 'Then and now' comparisons | P1 | 7 Remaining family/operations features | Not implemented; queued in dependency order. |
| M2-29 | Memory book | P1 | 7 Remaining family/operations features | Not implemented; queued in dependency order. |
| M2-30 | Media storage and retention rules | P1 | 7 Remaining family/operations features | Not implemented; queued in dependency order. |
| M2-48 | Milestone moments ('firsts') | P0 | 3 Updates/feed | Not implemented; queued in dependency order. |
| M2-31 | Fee plans and automatic dues | P0 | 8 Fees | Not implemented; queued in dependency order. |
| M2-32 | Fee tracker and earnings view | P0 | 8 Fees | Not implemented; queued in dependency order. |
| M2-33 | Pay by UPI link or QR (no fees) | P0 | 8 Fees | Not implemented; queued in dependency order. |
| M2-34 | Gentle reminder ladder (professional, not greedy) | P0 | 8 Fees | Not implemented; queued in dependency order. |
| M2-35 | Digital receipts and fee statements | P0 | 8 Fees | Not implemented; queued in dependency order. |
| M2-36 | Fair adjustments and make-up credits | P1 | 8 Fees | Not implemented; queued in dependency order. |
| M2-37 | Prefill-and-approve engine (AI drafting) | P0 | 5 AI/observations | Not implemented; queued in dependency order. |
| M2-38 | Privacy-safe AI (names removed before sending) | P0 | 5 AI/observations | Not implemented; queued in dependency order. |
| M2-39 | Parent message helper (AI inbox) | P1 | 7 Remaining family/operations features | Not implemented; queued in dependency order. |
| M2-40 | Notification engine and channels | P0 | 6 Reminders/schedules | Not implemented; queued in dependency order. |
| M2-41 | Coach 'Today' and 'Needs you' list | P0 | 2 Attendance/Today | Partial verified slice: real dated Today and enrolled-roster facts; frontend publication and richer Needs you workflow remain. |
| M2-50 | Class announcements | P0 | 3 Updates/feed | Not implemented; queued in dependency order. |
| M2-51 | Parent messaging with quick replies | P1 | 7 Remaining family/operations features | Not implemented; queued in dependency order. |
| M2-42 | Offline capture and sync | P1 | 7 Remaining family/operations features | Not implemented; queued in dependency order. |
| M2-43 | Child safety and health notes | P1 | 7 Remaining family/operations features | Not implemented; queued in dependency order. |
| M2-44 | Academy accounts, rooms and staff roles | P1 | 7 Remaining family/operations features | Not implemented; queued in dependency order. |
| M2-45 | Free-tier stack with swappable adapters | P0 | 5 AI/observations | Not implemented; queued in dependency order. |
| M2-46 | Event bus and links to other modules | P0 | 3 Updates/feed | Not implemented; queued in dependency order. |
| M2-58 | Typed parent items (UI-agnostic delivery contract) | P0 | 3 Updates/feed | Partial: private attendance parcels and safe parent fallback reconstructed; broader diary parcels and final current verification remain. |
| M2-53 | Trial requests: accept, suggest a time, enrol | P1 | 9 Extended features | Not implemented; queued in dependency order. |
| M2-54 | Listing and live availability | P1 | 9 Extended features | Not implemented; queued in dependency order. |
| M2-55 | Featured placement in Explore | P2 | 9 Extended features | Not implemented; queued in dependency order. |
| M2-56 | Coach insights | P1 | 9 Extended features | Not implemented; queued in dependency order. |
| M2-57 | Coach plan and billing | P1 | 9 Extended features | Not implemented; queued in dependency order. |

## Verified academy invitation checkpoint — 2026-11-10

Feature checkpoint `ed134cadaa83267ccfc9a9803bffd8d5a924617a` delivers the first
M2-02/S2-04 and M2-49 slice using real Supabase: manager issues a14-day single-use
invite → a separate parent selects their own eligible child and confirms → both
accounts reload the saved academy connection. Students uses the coach prototype's
colours/rounded cards without invented attendance/fee data. New feature copy is
EN/HI with remembered preference; older screens remain English.

Migration051 is applied to the existing founder-selected TEST project. The upgrade
verified all51 history entries and unchanged original application/Auth row
fingerprints. No reset occurred. This is schema/record-preservation evidence;
hosted invitation browser behaviour remains to be tested.

Batch enrolment/filtering, second guardians, attendance, diary, contact permissions,
fees and full child snapshots remain future. Academy connection never implies
legal verification or media/pickup/fee permission. M3 is in progress, not complete.

See [Quality Evidence](QUALITY_EVIDENCE.md#verified-academy-invitation-checkpoint--2026-11-10)
for exact local results, review fixes and source fingerprint. Publication/deployment
outcomes must be inspected separately. The18 original references are archived at
[the founder reference index](founder-references/2026-11-10/README.md).

## Academy family invitations — implementation checkpoint, 2026-11-10

The 18 founder reference originals are archived in
[the dated reference folder](founder-references/2026-11-10/README.md), committed as
`e3a8c716160b582473f9e61ac5133bdd167b43b7`. Independent archive review verified
manifest sizes/hashes and index links. The existing recovery stash is preserved.

The current feature adds the first M2-02/S2-04 and M2-49 slice: owner/admin
creates a 14-day single-use academy invite; a separate signed-in parent selects
an eligible child profile they created and explicitly confirms; the saved
academy-child connection appears in Students and the parent's connections panel.
This uses real Supabase functions and relationship records. It creates no batch
enrolment, legal verification, pickup/media/fee permission or second guardian.
Those remaining features and full snapshots are not claimed complete.

Migration051 is append-only, keeps invite hashes private and leaves legacy
connection entrypoints revoked. Source guards cover issuer/academy suspension,
guardian revocation, restricted relationships, idempotent retries and expiration
after lock waits. New interface copy has EN/HI selectors and a remembered language
preference; older screens remain English. No launch authentication change is made.
The hosted TEST backend has not yet received this migration at preparation time.

The reviewed design/plan are under `docs/superpowers/` dated2026-11-10. Full
regression, report inspection and hosted Git/deployment verification remain to be
recorded after execution. Earlier checkpoint evidence below is historical and
must not be re-attested to this new source. Founder authorisation in this task
covers commit/push/merge and continued use of the existing testing backend.

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


## Founder-testable local access — 2026-11-09

A local development sandbox now accepts dummy .test emails and code 123456,
creates ordinary local sessions, enables implemented first-use features during
manual testing and gives the founder record-count/membership override controls.
One actual browser-to-database scenario passed child/workspace/course/batch/weekly
session creation followed by suspension and restored access. Twelve new unit
checks cover local-only configuration, wrong codes, safe session exchange and
founder control restrictions. This is first-use testing availability; the full
students/enrollment, attendance, diary and fees milestones remain incomplete.


## Real local parent and coach first-use journeys — 2026-11-09

Local Supabase applies migrations 001–049 and passes real-provider browser
journeys for parent signup/child creation/reload/confirmation/isolation/sign-out,
and independent-coach plus academy-owner workspace/course/batch/weekly-session
creation, reload recovery, acknowledgement and membership suspension.
The coach membership gate now uses an explicit PostgREST FK relationship.
The new workspace-creation screen and its existing database control remain
default off; uncertain outcomes retain the original request key. Browser Web
Locks prevent overlapping tabs from replacing a newly established request.

Local verification: 296 frontend cases, 421 isolated PostgreSQL cases plus four
standalone concurrency scenarios, three real local browser journeys, six
OTP-disabled browser checks, and six namespace-isolated synthetic-provider
browser scenarios. Lint, TypeScript and production build passed. These are local
results; M2/M3 as a whole, hosted rollout and production readiness are not complete.
See [verification scope and limits](LOCAL_FIRST_USE_VERIFICATION.md).


## Signed-in coach navigation — 2026-11-08

The local sign-in page offers a coach-area link after a confirmed session and
hides it during sign-out. The coach route still checks active workspace
membership on the server. Local component tests cover the link and sign-out;
they do not verify a live provider or hosted browser journey. New coach
workspace creation remains unavailable and the link does not create access.

## Hosted database continuity — 2026-11-07

The founder intends to retain the selected ParentPlus Supabase project for test
accounts and eventual real family data. It must not be treated as a disposable
test database. The connected project's schema, migration state, permissions,
identity configuration, backup and real-data readiness are not yet verified.
See [DEC-020](DECISION_LOG.md#dec-020-continuity-of-the-selected-supabase-project).

## Coach menu — 2026-11-07

The coach dashboard header now has a native expandable menu linking to Today,
Schedule and Sign in. Component tests cover opening it and its available links.
This makes the previously decorative menu icon usable; the example dashboard,
students, posts and fees remain placeholders. The stale remote mobile browser
scenario expected access to an unauthenticated coach route and was not retained
after route protection was merged.

## Class setup with bounded weekly sessions — 2026-11-07

Local draft migration 048 adds a private per-workspace generation and a
request-key receipt for the app-facing begin operation. The generation advances
when a setup is acknowledged; an older manager view is rejected after it waits
for the acknowledgement lock. The old unversioned app begin RPC is revoked.
A local coach form checks availability, reserves with a stable request key,
creates a course, batch and bounded weekly sessions in one transaction, recovers
the saved schedule, and requires explicit acknowledgement before another setup.
The manager previews the session count and uses the academy time zone. An owner
or admin chooses that zone once if it is unset. DST gaps and repeated local
times fail closed; the series is limited to 104 sessions. The previous
authenticated completion RPC is revoked so it cannot skip weekly-session
creation. All controls remain default-off. Fresh isolated PostgreSQL checks
passed 421 unit tests, four standalone concurrency cases, all 425 JUnit cases
and cleanup. The frontend suite passed 283 tests. No hosted migration was
applied. An independent review found and this patch fixes the old RPC bypass and
silent browser-time-zone default; follow-up review remains. Enabled browser
evidence, schedule edit/cancel policy and an approved hosted rollout remain
open. See the
[class setup boundary spec](superpowers/specs/2026-11-03-class-setup-server-boundary.md).

## Coach route protection — 2026-11-07

Coach route-group pages now require a verified user with an active membership
in an active workspace. Owner, admin and coach roles are eligible. Signed-in
users without an eligible membership get an access explanation and a sign-out
recovery action. Unit/UI and anonymous browser coverage verify the gate. This
does not prove real provider identity or authorization for future write APIs.
Weekly course + recurring batch creation is implemented locally but remains
default-off pending enabled browser and hosted checks; no hosted data or
migration was changed. See [the coach route access spec](superpowers/specs/2026-11-07-coach-route-access.md).

## Private request lookup for a known workspace — 2026-11-07

Local draft migration 047 can look up a candidate creation request ID for one
known workspace ID belonging to its creator, after the private recovery status
rechecks the receipt, active workspace and active membership. The operation
returns only IDs and is inaccessible to application roles. It cannot discover an
unknown workspace, prove which submission the owner intended, or make a new
request safe. Account changes, lost workspace IDs, retention, real identity,
hosted rollout and the user-facing onboarding journey remain open.

## Private workspace request fence — 2026-11-06

Draft migration 046 adds an actor-scoped, exact-request fence. After a fence
commits, a later guarded or legacy workspace insert using that same key is
rejected. Existing receipts or surviving workspaces yield unknown instead of a
fenced claim. The private operation is disabled for app roles and requires the
default-off database control. This does not prove historical absence, recover a
lost key, prevent another key, or by itself permit a new request. Indefinite
fence retention, account changes, rate limits, hosted rollout and the full
onboarding journey remain unresolved.
New workspace inserts and the private fence operation conservatively reject
transaction isolation levels other than READ COMMITTED, because an older
snapshot could miss a committed fence; this includes READ UNCOMMITTED.

## Private workspace recovery status — 2026-11-06

Draft migration 045 adds a private, read-only lookup for an actor's exact
workspace creation request. It returns a known workspace ID only when its
receipt, workspace and creator membership remain valid; otherwise it returns
unknown. It uses the database control and request lock, and application roles
cannot call it. A status is a snapshot: unknown does not prove that a delayed
request cannot arrive and never authorises a replacement key. Lost keys,
retention, actual identity, a reviewed app journey and hosted use remain open.

## Workspace receipt forward repair draft — 2026-11-06

Local migration 044 disables workspace creation, installs the cutover safeguard,
and adds unknown receipts only for surviving workspaces missing one. Existing
known receipts remain intact; conflicting receipts abort the transaction. A
synthetic old-042/043 reconstruction also checks an in-flight old call rolls
back safely. A database already missing receipts for deleted workspaces cannot
reconstruct those keys; reconciliation and hosted rollout remain release blockers.

## Workspace cutover race correction — 2026-11-06

The local draft of migration 042 now drains existing workspace writers before
backfill and installs a trigger to retain an unknown receipt for legacy calls
that insert after cutover. Synthetic tests exercise both transaction orderings
and reject reuse of a retained key after privileged deletion. This change only
affects databases that apply the revised migration; installations that already
ran the old 042 need a separately designed forward repair. Deleted pre-existing
keys cannot be reconstructed. Hosted cutover and receipt retention remain open.

## Workspace control upgrade check — 2026-11-06

An isolated synthetic upgrade test applies migrations 041, 042 and 043 in
sequence. It checks an existing renamed workspace remains intact, a newer
workspace retry is blocked while the new control is disabled, and that retry
returns the same workspace after test-only enablement. This checks committed
pre-upgrade records, not concurrent migration cutover, lost request IDs,
retention or hosted deployment.

An independent synthetic test found that an in-flight 041 workspace creation
can commit after 042's backfill without a receipt. Following privileged deletion,
the same request key can create another workspace. This is a release-blocking
concurrent-upgrade risk; a safe rollout or migration correction remains unverified.

## Workspace creation database control — 2026-11-06

Local draft migration 043 puts workspace creation and replay behind a private,
default-off database control. It locks the control during each call and keeps
the prior creation implementation inaccessible to application roles. Synthetic
tests exercise disabled and missing controls, retry, private access and both
orders of disable-versus-creation/replay. The isolated test runner explicitly
enables the control for existing behavior checks and restores it afterward.
This is not a complete onboarding journey: hosted migration cutover, real
identity, receipt retention, rate limiting, rollout and recovery remain open.

## Workspace receipt legacy upgrade check — 2026-11-06

A separate disposable PostgreSQL container creates and renames a synthetic workspace under migration 041, applies 042, and checks that its name and owner remain while original creation details are marked unknown and retries fail closed. A new post-upgrade workspace retry is also checked. This is one isolated upgrade path, not verification of hosted data, concurrent rollout, recovery policy or receipt retention.

## Workspace creation receipt local draft — 2026-11-06

Draft migration 042 records the original workspace creation name and type privately for new requests; a valid retry can survive a later rename, while changed payloads and deleted targets fail closed. Existing rows are backfilled as unknown rather than guessing their original names, and their creation retries are unavailable. The draft retains names and identifiers without foreign keys; retention, deletion, old deleted keys, actual migration upgrade, exposure controls and hosted identity remain unresolved. No hosted database was changed.

## Workspace creation replay access — 2026-11-06

Draft migration 041 requires an active workspace and active creator membership before returning a workspace creation retry or comparing its details. Synthetic tests cover suspended/archived workspaces, suspended/removed/deleted membership, changed payload denial and both lock orderings. The draft still compares current mutable name/type rather than an immutable creation receipt; rename recovery, live identity, hosted privileges, audit and real workspace onboarding remain unresolved. No hosted database was changed.

## Two-sided MVP direction — 2026-11-06

The founder confirmed that the coach/academy experience must be ready alongside
the parent experience. The roadmap now records a proposed shared pilot journey
and explicit exit evidence for both sides. This is planning context, not a claim
that either end-to-end journey or its hosted deployment is complete.

## Connection RPC exposure safeguard — 2026-11-06

Local migration 040 revokes application-role execution of the unfinished connection-request and approval RPCs. Baseline privilege tests must verify denial; historical behavior and race tests use temporary grants in isolated fixtures and restore denial. Partial migration rollout, other RPCs, inherited hosted roles, real-provider access and the connection lifecycle remain unverified. No hosted database was changed.

## Connection-request retry receipt local draft — 2026-11-06

Draft migration 039 records each successful request key, including keys that reuse a pending request, to prevent a retry after approval creating a second request. A synthetic lock-race test also checks that an expired pending request is not reused after waiting. UUID-only receipts are retained without foreign keys so a missing request fails closed; historical reused keys cannot be reconstructed. Retention, erasure, abuse controls, live provider identity, legacy migration, database exposure controls and full lifecycle review remain release blockers. The existing authenticated RPC is directly callable when deployed; no hosted database was changed.

## Connection approval expiry safeguard — 2026-11-06

A local synthetic test reproduced approval of an expired request after waiting on a workspace lock. Draft migration 038 rechecks expiry after the blocking authorization and relationship locks, before approval writes. The targeted test verifies rejection without a relationship or approval event. This does not resolve connection-request retry receipts, provider identity, hosted migration ownership, audit/retention policy or release readiness; no hosted database was changed.

## Coach dashboard preview clarity — 2026-11-06

The dashboard identifies its classes and records as example data and replaces the nonfunctional start-class label with an example label. Component and local browser checks cover the preview wording; this is not real class scheduling or persistence.

## Coach navigation browser check — 2026-11-05

An automated Chromium scenario checks the five coach navigation links at a 320-pixel viewport: visible and non-overlapping 44-pixel targets, centre hit testing, keyboard traversal, navigation and current-page indication. This is one synthetic browser viewport, not physical-device, touch, screen-reader, contrast or full accessibility verification.

## Sign-in error browser checks — 2026-11-05

The local disabled-provider browser checks now verify that correcting an invalid email clears its warning, and a valid email is not marked invalid when email verification is unavailable. This uses Chromium and a disabled provider; real assistive technology and live email delivery remain unverified.

## Email code entry guidance — 2026-11-05

The local code-entry screen tells users to enter the six-digit code from their email and associates the instruction and any error with the code field. Component tests use simulated provider responses; real email templates, live delivery and assistive-technology testing remain unverified.

## Sign-in error accessibility — 2026-11-05

The local email form marks an email invalid for a format error, but does not mark a valid email invalid when requesting or re-requesting a code fails. Component tests use simulated service responses; live delivery and real assistive-technology testing remain unverified.


## Isolated enabled parent browser checks — 2026-11-05

A separate Chromium suite builds and runs the actual Next application with fixed synthetic session data and a local in-memory provider inside a network namespace that exposes only loopback IP interfaces and routes. It covers creation and acknowledgement, a lost confirmation response followed by reload, an uncommitted confirmation retried after reload, an unconfirmed response followed by two-tab advancement and historical recovery, an account switch, and a synthetic uncommitted request fenced before a new profile. An identified same-tab gap was corrected so a confirmation in progress immediately clears and locks the profile list; recovery must complete before the list is reloaded. The original disabled-feature browser checks remain separate. CI requires both browser reports and fails if namespace isolation is unavailable. This is simulated-provider evidence, not proof of signed-JWT verification, database authorization or concurrency, hosted behaviour, or filesystem isolation. The feature remains disabled.

## Parent creation integration simulation — 2026-11-05

Local component integration tests connect the actual parent panels and server actions to a synthetic in-memory provider and mocked session observer. They cover creation, acknowledgement, listing, lost responses, fencing, an advanced request, account change and denied historical access. The advanced request is injected into the fake provider, not a second browser tab. These tests use jsdom and do not exercise real browser-to-database, database concurrency, signed JWTs or a hosted provider. The feature remains disabled.

## Earlier child-creation recovery local draft — 2026-11-05

Draft migration 037 archives name-free references to future superseded requests. After a guarded history lookup, the local interface can recognise an earlier request without displaying a later profile as its result; it requires a fresh status check before another creation. Synthetic tests cover access, rollback and lock ordering. Already-overwritten history, deletion and retention policy, immediate revocation and real-provider end-to-end checks remain open; the feature stays disabled.

## Child-creation recovery scenario checks — 2026-11-05

Mocked component tests exercise recovery for a second profile, unacknowledged or mismatched state, account changes, a replaced tab marker and an earlier request superseded by a later profile. These mocked tests do not themselves establish cross-tab history or real-provider evidence; migration 037 adds a separate local history draft for future superseded intents. See the [recovery fence spec](superpowers/specs/2026-11-05-child-creation-recovery-fence.md).

## Child-creation recovery fence local draft — 2026-11-05

Draft migration 036 and a default-off application flow fence an exact unresolved request or find its already-created current result. Local synthetic tests cover both lock orderings, rollbacks, stale references, access and control changes; no hosted data is changed. This is not a complete release: privacy and retention decisions, identity loss, historical outcomes, real provider, signed JWT and enabled browser end-to-end checks remain open. See the [recovery fence spec](superpowers/specs/2026-11-05-child-creation-recovery-fence.md).

## Child-creation recovery fence design — 2026-11-05

A local synthetic database diagnostic checks that an empty status can be followed by creation in a later transaction. The [proposed recovery fence](superpowers/specs/2026-11-05-child-creation-recovery-fence.md) specifies a durable rejection and race, privacy and recovery tests. It is design work only: no fence, application flow or hosted change is implemented. The feature remains disabled.

## Child-profile recovery guidance — 2026-11-04

When browser storage is blocked or contains invalid recovery information, the default-off profile panels now explain why they cannot continue and warn against clearing saved data while a request may be pending. This improves guidance only; it does not resolve an invalid marker or provide cross-tab and identity-loss recovery.

## Child confirmation recovery draft — 2026-11-04

An interrupted acknowledgement can now be explicitly retried after same-tab reload when the original account and exact unacknowledged intent are confirmed. The list remains locked until a fresh status verifies acknowledgement. A temporary storage-write failure no longer leaves the form permanently locked after storage and status checks recover. This remains a default-off local draft; identity-loss, cross-device and live-provider recovery are not resolved.

## Same-tab child-creation recovery draft — 2026-11-04

A default-off local change records a tab-scoped request reference before child creation or acknowledgement. The profile list remains blocked during an unresolved request; an exact server-confirmed result can unlock it after a same-tab reload. The marker contains identifiers, not the child name. This is local simulated coverage, not real-provider verification. Storage deletion or tab closure, different accounts and devices, empty status after a crash, and historical receipts remain unresolved release blockers. See the [journey spec](superpowers/specs/2026-11-04-child-creation-journey.md).

## Parent child-creation journey draft — 2026-11-04

A default-off local draft now provides a parent creation, explicit confirmation and add-another flow backed by an actor-scoped durable intent and request identifier. Migration 035 revokes authenticated access to the legacy direct creation function; historical behaviour tests use temporary synthetic grants, and separate tests verify the real denial. Cross-account recovery, incomplete reload recovery, old-profile reconciliation, real provider/JWT behaviour and retention remain release blockers. See [the child creation journey spec](superpowers/specs/2026-11-04-child-creation-journey.md).


## Child creation database control — 2026-11-04

Draft migration 034 adds a private database switch that defaults off and gates direct authenticated `create_child` calls and retries. Existing behaviour tests explicitly enable it only in synthetic isolated fixtures; separate checks cover disabled/missing control, privileges and disable-versus-write ordering. A denied retry does not prove an earlier request failed. The parent-facing creation journey, durable lost-response recovery, real JWT/provider verification and lifecycle review remain incomplete. See [the child creation control spec](superpowers/specs/2026-11-04-child-creation-control.md).


## Child-creation replay safeguard — 2026-11-04

A local review reproduced an existing issue where replaying a child-creation request after the creator's guardianship was deleted recreated a provisional relationship, and replay after revocation or dispute still returned success. Draft migration 033 prevents that replay: an existing request requires a current provisional or active relationship before comparing details, and does not recreate one. Local tests cover deletion, revocation, dispute, both deletion/retry orderings and function privileges; see the current gate evidence.

At migration 033 the existing `create_child` function remained directly callable by authenticated database roles and was not controlled by the parent profile-read flag. Migration 035 later revokes that direct access and adds a default-off local journey; real JWT verification, complete recovery, lifecycle and retention remain unverified. Do not treat this local safeguard as approval to use real child data or as proof of production readiness.


## Parent profile disabled-state browser coverage — 2026-11-04

The local browser suite checks that the parent-created profiles page shows its unavailable state when the server flag is off, offers no load control and observed no non-GET/HEAD or external browser-page requests during the test. Local and session storage did not change from after the initial load through reload; server-side calls and other storage are not observed. This is a default-off synthetic check, not an enabled-profile, real-provider, cache-isolation or live-revocation test. The exact-case quality gate requires this browser scenario.


## Parent profile navigation — 2026-11-04

When its separate public navigation flag is explicitly enabled, the local signed-in screen links to the existing read-only parent-created profiles page, without prefetch. The navigation flag defaults off and is not an authorization control. The link is hidden when signed out and during sign-out. The destination, server action and database retain their separate default-off and identity controls; when disabled, the page says profiles are unavailable. Simulated-session checks do not prove real-provider navigation, authorization or immediate revocation. See [the parent profile spec](superpowers/specs/2026-11-04-parent-created-child-list.md).


## Parent-created profiles — 2026-11-04

A local, default-off read-only draft lets a signed-in parent request a bounded list of profiles they created, restricted to their own provisional or active guardianship. This is not all linked children or proof of legal guardianship. The UI clears names on observed session/focus changes; already visible names may remain after remote revocation until an invalidation event. Real-provider, signed-JWT, browser cache and immediate revocation checks remain release blockers. See [the parent profile spec](superpowers/specs/2026-11-04-parent-created-child-list.md).


## Explicit email account creation draft — 2026-11-04

A separate opt-in sign-up choice is drafted behind a default-off client flag and the existing live OTP flag; ordinary sign-in still prevents automatic signup. Client flags do not restrict direct provider calls. Keep provider-side signup disabled until approved and reviewed. Real provider signup, abuse controls, confirmation, account recovery, identity/session integration and the end-to-end onboarding journey remain unverified. See [the signup spec](superpowers/specs/2026-11-04-explicit-email-signup.md).


## Email code entry focus — 2026-11-04

After a locally accepted email-code request, the sign-in form moves keyboard focus to the code field when it is rendered. This is a keyboard-accessibility improvement; tests use a simulated provider. Live delivery, account provisioning and the complete sign-in journey remain unverified.


## Email retry verification — 2026-11-04

Local simulated-provider component tests now cover a repeat email-code request throwing an error and an account change during a delayed failed retry. They check that the prior code remains available on a thrown failure, and that stale information is not restored after an account change. Real provider behaviour and the full parent sign-in journey remain unverified. No usage data establishes an 80% frequency for either scenario.


## Email code paste — 2026-11-04

The local sign-in helper removes whitespace from a pasted verification code before checking for exactly six digits. This is a usability improvement based on an assumed common sign-in scenario; actual frequency is not measured. The provider remains disabled by default. Mocked-provider tests do not establish live delivery, provider verification, expiry or full sign-in.


## Prioritisation update — 2026-11-04

The founder requested prioritising frequently encountered scenarios and placing delayed class-setup recovery in the backlog. No usage data establishes a numerical occurrence probability; prioritisation is an assumption pending evidence. The class-setup write controls remain disabled, and delayed requests, identity recovery and unavailable-manager escalation continue to block that feature's release. The local email sign-in screen now labels the existing retry action “Request another code” after an accepted request and keeps code entry available after a failed retry, without claiming delivery; provider delivery, rate limits and real sign-in remain unverified.


## Partial workspace class-setup safeguard — 2026-11-04

Local draft migration 031 limits each academy to one unacknowledged class-setup intent, including across managers. This protects only concurrent unresolved intents and may block independent setup work. An independently identified delayed request can still arrive after acknowledgement and create another intent; a workspace generation or equivalent fencing, identity-loss recovery, and an escalation path for unavailable managers remain open release blockers. The feature stays disabled. See [the class setup boundary spec](superpowers/specs/2026-11-03-class-setup-server-boundary.md).


## Cross-manager class recovery blocker — 2026-11-04

A fresh isolated database diagnostic confirmed that two authorised managers in one academy can each receive a new pending reservation for the same class while the second manager's own recovery reports `unknown`. This was synthetic, rolled back and did not touch hosted services. Class setup writes remain disabled. See [the class setup boundary spec](superpowers/specs/2026-11-03-class-setup-server-boundary.md) for the reproduction, release boundary and required cross-manager concurrency, privacy and recovery scenarios. No fix or real-provider validation is claimed.


## Current class setup continuation — 2026-11-04

Local draft migration 030 introduces an authenticated begin operation that distinguishes a newly created reservation from an existing pending, completed or acknowledged reservation, under the existing actor/workspace lock. The ambiguous older app reservation wrapper is revoked in that migration. Its TypeScript operation bridge validates the returned classification. This is groundwork, not a released class-creation journey; the class recovery screen remains read-only and setup controls remain disabled by default.

An independent review found that interrupted writes could lose the original actor and workspace on reload or navigation, allowing a different account to start a duplicate; it also identified an unsafe same-session retry path after an unknown result. Proposed write controls were removed from the screen. Durable, identity-bound recovery and explicit retry reconciliation, real-provider/browser testing, hosted migration and deployment verification remain release blockers. No hosted services were changed. Inspect current Git state and fresh evidence before relying on a checkpoint.

Updated: 2026-11-03. Current local state; historical results are identified separately.

For a dated feature-by-feature scenario and end-to-end assessment, see the [Feature Scenario Register](FEATURE_SCENARIO_REGISTER.md). It is a snapshot; verify current source and evidence before relying on it.

## Checkpoint summary and milestone scope

- Quality-gate preparation baseline: `ac2b1f9af85b531142310fcd851a24c17390f4ae`.
- Approved local implementation checkpoint: `5b068b995957414a47dd2f47e8b6eb4147958563`; it has not been published to GitHub in this work.
- Shared-documentation foundation: drafted for review, including the prior communication standard. [Agent Handoff](AGENT_HANDOFF.md) owns branch, remote observations, working-tree state and detailed pending scope; inspect actual Git rather than treating this milestone summary as live status.
- Engineering state: quality-gate reliability/operating standards are committed locally; shared-context documentation is under review. No product milestone is completed by this documentation task.
- Approval boundary: present the complete reviewed scope/evidence before any commit. Push, merge, hosted changes, settings and deployment are separately unauthorized.

See [the audit report](INTELLIGENT_QUALITY_GATE_AUDIT.md) for exact files, findings, evidence and gap classifications, and [the operating workflow](FEATURE_DELIVERY_WORKFLOW.md) for future feature work.

## Recorded implementation capabilities

The following results belong to the prior quality-gate audit, not a fresh execution
for the current documentation draft. [Quality Evidence](QUALITY_EVIDENCE.md) owns
the execution provenance, snapshot reconciliation and artefact availability.

- Next.js coach demo and login UI with 24 component/auth-helper cases; TypeScript, lint and production build pass locally. OTP provider calls are mocked/disabled; this does not establish live sign-in.
- Thirteen PostgreSQL migrations and synthetic local auth fixture; 39 unit security/authorization tests plus four standalone concurrency scenarios pass in the existing disposable network-isolated database gate, including cleanup.
- Quality registry maps all 67 application/database cases exactly. Ten planned/deferred product gaps remain uncovered and visible.
- Quality engine has 49 behavioral regression tests after the independent audit; strict self-test rejects zero, skipped and expected-failure outcomes.
- Deterministic selection, segment-aware patterns, conservative security/unknown rules, recursive test collection, validated standalone entrypoints and exact-case evidence validation.
- Source fingerprints and run/attempt/report-bound receipts prevent accidental reuse across source snapshots or CI attempts. Local caller declarations remain a process trust boundary.
- Independent reviewer reproduced original defects, checked the corrections and reran all 49 engine tests. No remaining confirmed Important/Critical code finding was reported in the corrected scope.
- Engineering standards and feature-delivery instructions are routed from AGENTS.md, preserving Superpowers and application Next.js guidance. These are agent operating instructions, not a background autonomous service.

## Prepared, not hosted-verified

The orchestration and reusable workflows are in local checkpoint 5b068b9, not yet published in this work. All-branch/PR/merge-group event definitions, run-attempt artifact naming and receipt checks pass local syntax review but have not been exercised on GitHub. No branch-protection setting was inspected/changed or claimed active. The local implementation commit was approved; push and a matching actual CI run remain separate next steps requiring authorization.

The initial implementation report is historical and superseded by the audit report's evidence contract and counts. Historical machine evidence is under the ignored local `test-results/quality/audit/` directory. Its fingerprint and portability limitations are indexed in QUALITY_EVIDENCE.md; those reports do not validate the new documentation snapshot.

## Current local email verification slice

A reconstructed, uncommitted login screen slice adds code entry with error accessibility, duplicate submission guards and keyboard focus after successful mocked verification. The local UI offers current-session sign-out and provider-checked session restoration with mocked test responses; it does not establish live OTP, real-provider cross-tab delivery, session-aware navigation or a verified real-provider integration. Local mocked-event checks exercise stale-result and account-change handling. Product requirements and test scope are described in [the local spec](superpowers/specs/2026-11-03-email-otp-screen.md); see [Quality Evidence](QUALITY_EVIDENCE.md) and current local evidence for verified results. M2 remains incomplete.

## Synthetic coach schedule preview

An uncommitted M3 presentation slice shows clearly labelled example courses, batches and session times. A local recurrence utility calculates one-off and weekly instants with explicit time zones and daylight-saving rejection. Neither slice uses child data or implements persistent scheduling, permissions or enrollment. The [schedule spec](superpowers/specs/2026-11-03-schedule-preview.md) records the scope; actual M3 journeys and their security checks remain planned.

## Product milestones and release gaps

M0/M1 frontend foundation remain the historical completed baseline. M2 has local auth helpers and database foundations; the full authentication/data product milestone is incomplete. Database connection/approval contracts exist locally, but M3 classes/students/enrollment journeys are not established as complete. M4 attendance, M5 private diary/media and later milestones remain unimplemented/partial per the roadmap.

All ten registry gaps are acceptable for this synthetic-data engineering-tooling milestone. Live OTP, invitation journeys, enrollment, attendance, private media/consent, account lifecycle/retention, guardian history and learning delivery block release of the corresponding real product behavior. Formal verification method/timing needs a future decision, while sensitive access, disputes and revocation cannot be waived by self-declaration. Phone OTP remains deferred for the email-first scope.

The current uncommitted browser suite covers two disabled-OTP login scenarios; full browser journeys, hosted Supabase integration, real signed-JWT authorization, physical-device verification, real family data and production readiness remain unverified. The older npm audit count of 16 moderate findings and Cloud Shell preview/storage notes are historical; dependency audit and production/provider issues were not re-verified by this audit.

## Next actions

1. Review the shared-documentation foundation and its exact diff; obtain approval before committing this new scope.
2. After a separately approved push, inspect actual GitHub branch tips and hosted CI evidence. Do not claim another assistant can see unpublished local work.
3. Propose documentation-freshness/link checks and concurrency-aware automated writers as a separate scope; no such checker or sync service was added here.
4. The owner decides whether/when to require the final gate in branch protection; no settings changes are authorized here.
5. Select the next product slice through the operating workflow, resolving its privacy and acceptance decisions before real-data or release claims.

## Historical context retained

Earlier progress notes tracked branch `setup/parentplus-foundation`, checkpoint `ccd33c5`, four then six frontend tests and the M1 navigation milestone. Those reflect earlier local/Cloud Shell work and are not the current branch, test inventory or checkpoint. The Git history and original implementation report retain that chronology; current capabilities and limitations above take precedence.

The local recurrence calculator now identifies the date, time, zone and type of a daylight-saving conflict for future user guidance. This remains an unintegrated calculation component; the schedule screen, permissions and persistence do not yet use it.

A local draft database migration adds inaccessible-by-default course, batch and assignment tables with same-workspace foreign keys. Application-facing operations, role/status enforcement, real scheduling and hosted deployment remain incomplete and require security review.

A private local scheduling authorization helper checks active workspace, membership, role, batch and coach assignment while holding transaction-scoped locks. It is not exposed to app roles or connected to a write operation; race verification and security review remain outstanding.

The private scheduling helper has six local tests covering both transaction orderings for workspace suspension, membership suspension and assignment removal. They use a synthetic batch update; real scheduling writes and independent security review remain outstanding.

A private local-only one-off session persistence foundation validates authorization, UTC duration and retry identity. It is inaccessible to app roles and does not yet implement workspace-time-zone enforcement, recurring classes or a user-facing scheduling journey.

A private local wrapper derives one-off session time from the workspace zone and rejects ambiguous or nonexistent local times. Zone configuration, selection of repeated-time occurrences, integration and exposure remain unfinished; performance and timezone database consistency require review.

A private local initial time-zone configuration operation checks active owner/admin membership and rejects subsequent zone changes pending a safe policy. It is not yet exposed to application users; audit, UX and independent security review remain open.

The India-first scheduling continuation adds local private owner/admin course and batch creation with workspace isolation and retry checks. These operations are not accessible to app users; assignment, reads, UI integration, race coverage and independent security review remain open.

The local draft adds a private coach-to-batch assignment operation with active-workspace and role checks. This does not expose scheduling to app users or complete assignment management, audit, user journeys or security review.

A private local coach-removal operation is being verified against repeat requests, workspace isolation and concurrent session/assignment operations. Application access, audit and complete class-management journeys remain unfinished.

Independent review identified a stale assignment/removal retry flaw. A local request-receipt design is being verified to prevent earlier retries from undoing later actions. Its receipt retention and deletion behaviour needs review before application use.

The schedule screen has a practice-only in-memory course/batch setup preview, clearly marked as unsaved. It is not a real or persistent class-creation journey; the actual app-facing operations and authorization remain unfinished.

A local-only draft adds an authenticated course-creation database wrapper with workspace-manager checks; it does not yet connect the practice screen or establish hosted authentication, audit, release readiness or a full class-creation journey.

A local draft authenticated batch-creation wrapper complements the course wrapper, retaining workspace-manager and same-workspace course checks. This is not yet connected to the app or verified against a hosted provider.

A local authenticated-role draft can create a course and first batch atomically using a separate request receipt. It is not connected to the app or deployed; hosted identity/ownership, audit/retention, rate limits and full integration remain open.

An off-by-default server action draft prepares validated atomic class setup through a provider client. The practice screen remains unconnected; real provider, workspace selection, retry UX, rate limits and app E2E are unfinished.

### Class setup workspace lookup (local draft, 2026-11-04)

A server-only, default-off lookup for active manager workspaces is under development. It is not connected to the practice screen and is not real-provider verified; class creation remains incomplete. See `docs/AGENT_HANDOFF.md` for limits and inspect fresh test evidence.

The class setup screen remains disconnected while durable retry and shared-device privacy are designed. A browser-storage prototype was removed after review identified cross-tab and data exposure risks.

A private local reservation primitive is under development. It is inaccessible to app roles and does not yet implement the complete reservation, creation and acknowledgement journey. Class setup remains incomplete and disabled by default.

A local private completion draft can atomically attach created course and batch IDs to a reservation. Status recovery, acknowledgement and the user journey are not implemented; the separate authenticated creation endpoint still bypasses reservations. The feature is not release-ready.

A private local recovery-status draft distinguishes pending, completed and unknown reservations. It is not connected to the application, and it does not close the direct creation API bypass. Class setup remains incomplete and disabled by default.

A local migration now restricts the three legacy direct creation functions from app roles. The real class setup journey remains unavailable while reviewed reservation wrappers and recovery are built. Provider mocks do not verify actual access.

The old class setup server action now returns unavailable and does not call the legacy RPC, even if its app flag is enabled. Real class setup remains unfinished.

A local private acknowledgement draft records acknowledgement of a completed reservation without releasing the slot. Starting a subsequent class, recovery UX and app access remain unfinished.

A private local next-class transition draft uses retained history and payload-bound request IDs. It is not connected to the app; lost-token recovery, history/retention, remaining races and the complete user journey remain unfinished.

A private local recovery draft can return current reservation and next-request details to the same authorised actor. It does not recover an older archived result or complete app-facing class setup.

A private local lookup can retrieve a known archived class setup for the same authorised manager. Discovering a lost identifier and the end-to-end application journey remain unfinished.

A private local archive-discovery draft adds bounded, UUID-ordered pages for the same authorised manager. Pages are snapshots, not chronological or guaranteed complete across concurrent changes; application integration remains unfinished.

A local draft now grants authenticated-role access to narrow reservation-protocol wrappers, guarded by a database control that defaults off. Synthetic SQL tests are not real-provider or user-interface validation; the old web action remains unavailable and the complete feature is not release-ready.

A disabled-by-default server bridge for current class recovery is under development. Its identity and RPC tests use mocks; the real provider, archived recovery UI, class creation screen and end-to-end journey remain unverified.

A disabled-by-default server bridge now drafts reserve, complete, acknowledgement and next-class operations with account checks and uncertain-result handling. Tests mock the provider; the real screen and end-to-end journey remain incomplete.

A request-gated, default-off read-only class recovery panel is under development. Mocked UI tests do not establish real provider behavior or a complete class setup journey; creation, retry, acknowledgement and advancement remain unavailable in the screen.
