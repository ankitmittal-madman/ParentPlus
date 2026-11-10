# Attendance, Today and parent signals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The controller owns dispatch and publication; implementers do not dispatch additional workers or publish independently.

**Goal:** Deliver real dated coach attendance, child-scoped parent signals and a usable parent attendance feed backed by private transactional contracts.

**Architecture:** One forward053 migration adds session lifecycle, attendance audit/receipts, append-only signals and typed parent parcels. Database-owned guards,052-compatible batch locking and normalized full-payload receipts provide authority, atomicity and recovery; bounded server actions feed prototype-aligned coach and parent modules.

**Tech Stack:** Existing PostgreSQL17/Supabase, Next16.4.3, React19.3.0, TypeScript, Vitest, Playwright and Python unittest/JUnit gate. No dependency changes.

**Spec:** `../specs/2026-11-10-attendance-today-design.md`.

## Global Constraints

- Preserve existing source, data, original founder files and stash; modify only assigned paths. The preceding052 checkpoint is frozen/published to work.
- Attendance states: `present`, `late`, `absent`, `excused`, `make_up`.
- Signals: `running_late`, `missing_today`, `dropped_off`, `picked_up`.
- Missing reason is required and one of `unwell`, `travelling`, `other`; other signal types require reason=null.
- Session lifecycle: `scheduled` or `cancelled`; positive int32 version starts1.
- Bounded responses: academy/session/feed/signal pages50, with explicit next cursor. Atomic session roster supports at most200 active enrolments before connection filtering.
- Keep testing email/123456 sign-in. Preserve original founder files and existing profile, invite and class-recovery entrypoints.
- No new services, accounts, dependencies, worktrees or paid products. Never edit014–052 or backfill invented attendance.
- Parent scope: child creator plus provisional/active guardian, active workspace and active academy connection. Historical enrolment never overrides current access.
- Signals remain parent reports; explicit coach confirmation/save is the only attendance writer. No safe-handover claim.
- New copy has EN/HI keys. No demo counts, fake posted state, no-op posting/media controls or unimplemented metric tiles.
- Existing continuation/publication authorisation belongs to the controller. Tasks end in evidence/review checkpoints, not new routine permission stops.

## Review Focus

1. Two saves must not both hold batch SHARE then upgrade: Task1 tests the guard taking UPDATE directly.
2. Pause/resume has the same final active status but a changed roster version: Task1 tests the ABA conflict.
3. A version1 receipt recovered after correction3 resolves recovery without replacing current data: Tasks1/2 test both boundaries.
4. Scope/account switches during reads/polls/saves never expose prior data or replay another actor: Tasks2/3 test late promises and persisted recovery.
5. Unknown item versions and encoded action URLs never crash or navigate outside approved own-child routes: Task3 tests the safe fallback.

## File boundaries and shared interfaces

The spec owns every exact RPC signature, JSON field, table/key/index, lock order,
normalization and error rule. Tasks consume that contract rather than duplicating
SQL or independently inventing response shapes. New feature modules stay focused;
do not turn family/enrolment actions into a generic service layer.

| Files | Responsibility |
| --- | --- |
| supabase/migrations/20261110005300_attendance_today.sql | Complete053 schema, helpers, RPCs, lifecycle and ACLs; single writer. |
| tests/database/attendance_fixtures.py; test_attendance.py; test_attendance_concurrency.py; test_parent_signals.py; test_parent_items.py | Synthetic fixtures, scoped contracts, rollback, both race orderings as individually collected unittest cases. Existing four standalone scenarios remain registered and execute unchanged. |
| apps/web/src/modules/attendance/contracts.ts; pending.ts; session-boundary.ts; attendance-panel.tsx | Strict attendance/input/receipt types, actor recovery storage, generation fence, polling and explicit roster editing. |
| apps/web/src/modules/today/contracts.ts; today-panel.tsx | Bounded academy/session pages and real Today composition. |
| apps/web/src/modules/parent-feed/contracts.ts; item-card.tsx; parent-home.tsx | Parent navigation/session/signal/week/feed contracts, fallback renderer and parent home. |
| apps/web/src/lib/attendance/actions.ts; lib/parent-feed/actions.ts | Verified getUser fence and strict mapping to the spec RPCs, without service credentials. |
| Existing coach root/header, parent/login routes and messages | Replace demo Today, inject actual academy, expose usable parent entry and EN/HI copy. |
| apps/web/e2e-qa/attendance.spec.ts; tests/ops/test_attendance_upgrade.py; existing quality/runner/ops/docs | Signed cross-persona journey, migration preservation, traceability and source evidence. |

Runtime boundaries have meaningful focused `*.test.ts`/`*.test.tsx` coverage;
pure type declarations reuse decoder/consumer tests rather than mirror-only tests. SQL UUID/date/
time fields become validated strings, counts/versions numbers and statuses exact
unions. Snake_case to camelCase happens once in decoders.
`Result<T>={ok:true,data:T}|{ok:false,kind:'invalid'|'forbidden'|'conflict'|'unknown'}`.
`AttendancePayload`/`SignalPayload`/receipts match the exact spec JSON shapes.
`PendingOperation={format:1,actorId:string,requestId:string,payload:AttendancePayload|SignalPayload}`.

### Task 1: Complete private attendance/signals/feed database contract

**Files:** Migration053 and the five DB files above; existing initializer,
runner/JUnit and cleanup inventories as required to execute the new cases.

**Interfaces:** Produces all13 RPCs in the spec, the private guard/normalizers,
seven new private tables, session lifecycle and added composite keys. Existing
014/015/049/051/052 contracts remain unchanged. No partially exposed migration.

- [ ] Write failing schema/read tests for exact keys/types, private table/helper ACLs, owner/admin/assigned-coach isolation, creator+guardian parent scope,50/51 tied cursor pages, local-date/DST/cross-midnight boundaries, sheet version0 with no writes, active-connected roster only,200 editable/201 blocked and lifecycle version guard.
- [ ] Run `python3 -m unittest tests.database.test_attendance tests.database.test_parent_items -v` against isolated synthetic fixtures; record missing053/functions as intended failures. Implement schema/guards/reads from the spec. Attendance obtains batch UPDATE directly, never SHARE then upgrade. Add no broad direct-table policies.
- [ ] Write failing save/recovery tests for exact roster/version/token, five statuses, equivalent reordered payload retry, malformed/duplicate/case-variant inputs, other actor/changed full payload collision, correction events/stable parent item, old receipt versus newer sheet, current-authority replay and failure injected at record/event/item/receipt with identical before/after snapshots.
- [ ] Write deterministic two-connection tests: admission/pause/resume/withdraw through actual052 both orderings; pause/resume ABA; duplicate saves without lock upgrade; workspace/membership/assignment/connection/guardian revocation as applicable; initially hidden connection reactivation; cancel/move/restore using batch-first fixture; duplicate request/status wait. Use explicit barriers/blocker observations, not timing-only sleeps.
- [ ] Run failures, then implement atomic save/status with one transaction, full canonical payload receipts and held locks. No receipt or item survives rejected writes. Historical omitted records survive. Unknown status is not permission to replace the key.
- [ ] Add failing signal/feed/week tests for four enums/reason nullability, active enrolment/current local day, day rollover after observed waits using the spec's privileged fixture-only clock override (restore in finally; production always real clock), append-only actor history, same-key recovery/rollback, parent isolation/type-independent base access/expiry, navigation workspace/batch IDs and exact weekly counts over >50 detail rows. Implement remaining RPCs; signals never update attendance.
- [ ] Run all new modules, actual052/family/private-coach regressions and all existing standalone scenarios. Register the new concurrency unittest module in database_junit.py; do not duplicate its cases through a new main() entrypoint. Run `bash scripts/ci/database-quality.sh` once inventories are truthful. Expect53 migrations, all cases executed, no orphan records/grants or cleanup residue. This is a local development checkpoint, not release evidence for a later source.

### Task 2: Strict adapters, durable recovery and real coach Today

**Files:** Attendance/today modules, lib/attendance/actions.ts, shared parent
contract schemas needed by Task3 (parent actions are implemented in Task3); existing coach root/page tests,
coach-header/tests, EN/HI messages. Read local Next16 guides before web coding.

**Interfaces:** Actions `listTodayAcademies`, `listTodaySessions`,
`loadAttendanceSheet`, `saveAttendance`, `attendanceRequestStatus`,
`listSessionSignals` consume `(actor:unknown,input:unknown):Promise<Result<T>>`;
input is the relevant spec RPC arguments mapped to camelCase, except writes and
status use `{requestId,payload}`. No actor enters canonical DB payloads.
`canonicalAttendancePayload(input:unknown):AttendancePayload|null`;
`canonicalSignalPayload(input:unknown):SignalPayload|null`;
`readPending(actorId:string,operation:'attendance'|'signal'):PendingRead`;
`PendingRead={kind:'none'}|{kind:'pending',value:PendingOperation}|{kind:'corrupt'}|{kind:'unavailable'}`;
`writePending(value:PendingOperation):'stored'|'same'|'blocked'|'unavailable'`;
`clearPending(expected:PendingOperation):void` (compare full identity/payload,
not UUID alone; never clear another operation's slot).
`AttendancePanel({actorId,workspaceId,sessionId,onSaved})` has three string IDs
and `onSaved:()=>void`; `TodayPanel()` composes it.
`CoachHeader({academyName?:string})` has no fictional academy fallback.

- [ ] Write failing adapter/decoder tests for every exact argument/result mapping, actor/getUser mismatch, missing/duplicate/malformed/oversized replies, bounds, redaction and SQL error classification. Add immutable pending tests for persist-before-send, reload, another actor, malformed/storage-unavailable, dropped reply, unknown status, old receipt/current sheet and exact-key retry.
- [ ] Run focused Vitest and capture intended failures. Implement strict adapters, pending helpers and session boundary. Generation fences clear fetched private data on actor/scope/focus changes; pending keys survive uncertainty. Poll only visible current session signals every15seconds and clean up timers.
- [ ] Write failing UI tests for assigned-coach autoload, academy-local default date/strip/pagination, no implicit marking, P/L/A/More, mark-all preserving exceptions, absence suggestions on unmarked rows only, all rows required before Save, conflict refresh/review, recovered receipt followed by current-sheet fetch,200/201/empty/cancelled and late promise/account switches.
- [ ] Run the failures; implement real Today and editor using prototype cards/coloured strips/compact roster. Remove root demo imports/static names/rooms/metrics. No End class and post or capture button until those journeys work. Polling signals does not reset dirty marks. Header uses selected academy; unknown save blocks replacement writes.
- [ ] Run focused Vitest, existing root/header/enrolment tests, lint/typecheck/build. Check keyboard names,44px targets, live save feedback, mobile footer clearance and EN/HI. No example-data fallback remains on real Today.

### Task 3: Parent home, signals and safe typed item fallback

**Files:** Parent-feed modules/actions; `apps/web/src/app/parent/page.tsx`;
parent/children and login destination links/tests; EN/HI messages.

**Interfaces:** Parent actions `listParentAcademies`, `listParentBatches`,
`listParentSessions`, `listParentItems`, `loadParentWeek`, `sendParentSignal`,
`parentSignalRequestStatus` use Task2's actor/input/result convention and exact
spec arguments. `ParentHome()` consumes them.
`ParentItemCard({item:ParentItemEnvelope})` handles known v1 or fallback.
`safeParentAction(value:unknown,childId:string):{label:string;href:string}|null`
implements the spec allowlist; it confers no destination authority.

- [ ] Write failing action/component cases for automatic own child/academy/class/feed loading, dedicated workspace/batch IDs, independent pagination, academy-local date, accurate saved/week facts, reports not attendance, signal recovery, no-eligible/paused/ended/revoked views and stale child/academy/account promises.
- [ ] Write fallback cases for unknown type/version/extra fields/malformed known payload, escaped HTML, at most one action, own-child-only query, external/JS/data/protocol-relative/encoded/backslash/control/traversal/fragment/duplicate-query denial. Assert title/body bounds and no navigation on invalid action.
- [ ] Run failures; implement the strict parent adapters, `/parent` selectors/date strip/session reports/typed feed/week facts. Signed-in login links Parent home while retaining profiles. `/parent/children` links home and preserves creation/recovery/connection/enrolment functions. No other guardian's report or contact info enters parent UI.
- [ ] Run focused and existing login/parent/enrolment integration suites, lint/typecheck/build. Check empty/error/recovery mobile states and both languages. Sending a parent report never changes attendance or counts locally.

### Task 4: Signed journey, upgrade preservation, review and delivery evidence

**Files:** attendance.spec.ts, test_attendance_upgrade.py; quality requirements/
browser catalog; existing scripts/ci init/run/database-quality/JUnit/concurrency/
evidence validators; first-use upgrade rehearsal and existing deployment-upgrade
script/tests only where053 inventories require it. Integrate canonical spec/plan,
architecture/decisions/roadmap/build/evidence/handoff after verified work.

**Interfaces:** Executable AT01–AT14 mappings, fresh source-bound reports/receipts,
immutable source and truthful release boundaries. No new provider infrastructure.

- [ ] Add failing browser cases for the signed manager → separate parent → explicit enrolment → Today save → exact parent record/week → own signal → correct coach session journey, reload persistence, pause removal, another parent denial, date/academy switches and dropped-response recovery. Create sessions on actual academy-local today; browser clock mocking alone does not change DB today. Catalogue controls/screenshots on mobile+desktop and remove obsolete demo expectations.
- [ ] Add upgrade assertions:052 fingerprints retained, only declared session defaults added,53 history entries, seven new private tables, actual catalog/ACL inventory, complete standalone execution/JUnit and zero residual rows. Public table baseline34 becomes41 if no other integrated schema change; verify actual catalog. Do not lower existing case minimums.
- [ ] Run `python3 scripts/quality/quality_gate.py inventory`, `self-test`, then `plan --output test-results/quality/attendance053`; inspect new exact test identities/path classification. Run selected complete checks plus `bash scripts/ci/database-quality.sh`, `npm --prefix apps/web test`, `npm --prefix apps/web run lint`, `npm --prefix apps/web run typecheck`, `npm --prefix apps/web run build`, `PARENTPLUS_CHROMIUM_PATH=/usr/bin/chromium python3 scripts/qa/run-browser.py` using existing documented prerequisites. Do not share a DB container concurrently with another owner. Inspect exits, case counts, screenshots, report identities and cleanup.
- [ ] Obtain independent review of the complete spec/scope/AT matrix, SQL locks/recovery/fallback and evidence. Resolve reproduced findings with regressions and rerun affected checks. Self-review is not independent review. State any unavailable check/review explicitly.
- [ ] Generate and verify receipts only for complete passing suites at the current source. Controller publishes only the immutable reviewed source through existing Git/TEST authorisation and records real hosted outcomes separately. Implementers perform no hosted operation; root uses existing testing authority after verification.

## Self-review and handoff

Coverage: schema/ACL/bounds/atomicity/receipts/052 races/signals/history/feed/week
Task1; adapters/recovery/Today/editor Task2; parent entry/fallback Task3; signed
browser/migration/traceability/evidence Task4. Every Review Focus has named test
coverage. SQL signatures/JSON field definitions live in the spec; UI mappings
must preserve them exactly. Seven new tables correct the initial arithmetic;
existing session/enrolment alterations are not new tables.

Unrun: implementation, runtime/security/concurrency/browser tests, independent
review and hosted migration/publication. This plan starts after052's verified checkpoint under existing continuation
authorisation; no extra founder confirmation is needed for routine execution.
