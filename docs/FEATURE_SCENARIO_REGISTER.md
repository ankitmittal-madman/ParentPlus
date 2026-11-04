# ParentPlus — Feature, Scenario and End-to-End Register

Prepared: 2026-11-04. Source snapshot: branch `feature/intelligent-quality-gate-v1`, HEAD `d1580e02fb928deb17872acce522e202b068885d`, before this report was added. This report is a reviewed snapshot, not a live dashboard or a substitute for the [roadmap](DEVELOPMENT_ROADMAP.md), [decisions](DECISION_LOG.md), [build progress](BUILD_PROGRESS.md) or [executable registry](../quality/requirements.json). Check Git and fresh evidence for later changes.

ParentPlus aims to connect parents, coaches and academies while protecting children's information. **No complete parent-to-academy product journey is established by the current evidence.** Local database operations and mocked screens are foundations, not released features.

## How to read the status

| Label | Meaning |
| --- | --- |
| Demo | Sample content or practice UI; no real record is created. |
| Partial | Some code exists, but the complete user journey or required checks are missing. |
| Private foundation | Local database capability inaccessible to app roles; not a user feature. |
| Planned | Requirement or scenario identified; no complete implementation established. |
| Deferred / decision | Intentionally later, or requires an explicit product/privacy decision. |
| Browser scenario | Real local Chromium interaction, often with synthetic data and external traffic blocked; not automatically a live-provider E2E test. |
| True E2E | A user can complete the full journey through the interface, authenticated services and persisted data, including relevant permission and failure checks. None of the product journeys below is established as complete E2E. |

“Covered” below means an executable test exists for the described scope. It does not mean every variation or production environment is covered. Security/authorization database checks use synthetic users and a disposable PostgreSQL database, not real Supabase signed JWTs. Several historical creation-wrapper tests temporarily grant permissions in isolated test fixtures; migration 022 revokes those direct app-role grants in the current local schema.

## Current priority update — 2026-11-04

The founder asked to focus on frequently encountered scenarios and backlog delayed class-setup recovery. Frequency above 80% is not established by usage data; use a clearly labelled assumption until measured. Class-setup writes remain disabled: delayed requests, account identity recovery and unavailable-manager escalation still block release. The current local sign-in retry label makes the existing repeat request discoverable; real email delivery, provider limits and the full sign-in journey remain unverified.

## Local account-creation draft — 2026-11-04

A separate, default-off email account-creation choice is now drafted. Local tests use mocked provider responses. Existing sign-in still disables automatic signup. The client-side flags are not provider access controls; real signup, abuse protection and the full onboarding journey remain unverified and must stay disabled until reviewed. See [the signup spec](superpowers/specs/2026-11-04-explicit-email-signup.md).

## Local parent profile-list draft — 2026-11-04

A default-off local page can list profiles created by the signed-in account, provided its own provisional or active relationship remains. It is a subset, not a complete list of linked children or evidence of legal guardianship. Security, real-provider and revocation limitations are recorded in [the parent profile spec](superpowers/specs/2026-11-04-parent-created-child-list.md).

## Local child-creation replay safeguard — 2026-11-04

A draft database migration prevents an old child-creation request from recreating a deleted guardianship or succeeding after revocation or dispute. This protects a local replay scenario; parent-facing creation, durable lost-response recovery and live-provider validation remain incomplete. At that checkpoint the authenticated database RPC was not controlled by the separate parent-read flag; migration 035 later revoked direct authenticated access.

## Local child creation control — 2026-11-04

The local database draft now defaults child creation off even for direct authenticated calls. Synthetic tests explicitly enable the control where needed and test its disabled/missing states. The parent-facing creation journey and live-provider verification remain incomplete; see [the child creation control spec](superpowers/specs/2026-11-04-child-creation-control.md).

## Local parent child-creation journey draft — 2026-11-04

A default-off local parent screen now supports checking status, entering a name, confirming a result and deliberately starting another profile. Its database journey binds an actor, prior intent and request identifier; mocked component and synthetic SQL tests are not live-provider end-to-end evidence. Recovery across accounts, navigation and older profiles remains incomplete. See [the journey spec](superpowers/specs/2026-11-04-child-creation-journey.md).

## 1. Features with code or foundation

| ID | Feature / real use | What exists | Covered scenarios and evidence | Missing or not established | Complete E2E? |
| --- | --- | --- | --- | --- | --- |
| F01 | Coach dashboard and navigation: coach views daily tasks | Demo dashboard, shared navigation and components | Component tests check navigation, header and stats. [UI tests](../apps/web/src/ui/components) | Live data, functional start-class action, real tasks, role-aware access and full device/accessibility verification | **No**; demo only |
| F02 | Email OTP sign-in: coach signs in | Email entry, six-digit code screen, helpers and disabled-by-default live flag | Invalid email, code validation, mocked provider success/failure, duplicate submits and accessible errors; browser checks invalid email and disabled OTP. [Login tests](../apps/web/src/app/login/page.test.tsx), [browser tests](../apps/web/e2e/login.spec.ts) | Real delivery, expiry/resend/provider edge cases, actual signed session and protected-page journey; new-user provisioning and account recovery need design | **No**; 2 limited browser scenarios |
| F03 | Session restore, change and sign-out | Helpers and login-screen handling for current-user check, sign-out, auth events/focus rechecks | Mocked session success, unavailable/missing state, sign-out failure, stale async responses and account-change handling. [Auth tests](../apps/web/src/lib/auth) | Live provider/token refresh, actual cross-tab events, protected navigation and revoked-session E2E | **No**; mocked provider only |
| F04 | Workspace and role foundation: independent coach or academy operates a workspace | Local schema, workspace creation and own-profile/membership RLS foundation | Anonymous/direct insert denied, own vs other profile, workspace isolation, suspended membership and workspace-creation concurrency. [Database tests](../tests/database/test_authorization.py), [workspace concurrency](../tests/database/test_concurrent_workspace.py) | Workspace onboarding UI, invitations, ownership transfer, complete lifecycle, hosted policies and real identity | **No**; local SQL only |
| F05 | Parent creates a child profile | Draft child, provisional guardianship and idempotent creation operations | Anonymous/direct child and guardianship writes denied; identical retry, changed request, atomic failure and simultaneous creation. [Child tests](../tests/database/test_child_authorization.py), [concurrency](../tests/database/test_concurrent_child.py) | Parent-facing UI, true identity/guardian verification, disputes, safe real-data handling and hosted auth | **No**; local SQL only |
| F06 | Parent requests an academy connection | Draft guardian-initiated request, relationships and approval operations | Valid request; unrelated, revoked or disputed guardian; suspended/archived workspace; repeat/conflicting request; expiry and approval/revocation races. [Connection tests](../tests/database/test_connection_authorization.py), [approval races](../tests/database/test_approval_authorization_races.py) | Guardian and academy user screens, coach-initiated invitations, confirm/skip/reject journey, dispute handling, full audit and real identity | **No**; local SQL only |
| F07 | Example schedule and class setup practice | Example classes and in-memory course/batch preview, labelled not saved | Component validation and stale-preview handling; browser checks example labels, preview, reload, observed non-read requests and browser storage. [Schedule browser test](../apps/web/e2e/schedule.spec.ts) | Real class/session records, workspace selection, permissions, schedule visibility and persistence | **No**; practice browser scenario only |
| F08 | Time calculation for one-off / weekly sessions | Local recurrence utility and private database local-time draft | One-off and recurrence calculations; invalid inputs and bounded limits; selected gaps/overlaps and workspace-zone cases. [Recurrence tests](../apps/web/src/lib/scheduling/occurrences.test.ts), [DB scheduling tests](../tests/database/test_scheduling_foundation.py) | Integration, real session management, recurrence edit/cancel/exception journeys, timezone data consistency and performance. India-first delivery remains the priority | **No**; utility/private SQL only |
| F09 | Courses, batches and assigned coaches | Local tables and private creation, assignment/removal and one-off session primitives | Same-workspace keys; role and status denials; assignment/removal; replay and changed-request checks; selected assignment, membership and workspace race orderings. [Scheduling tests](../tests/database/test_scheduling_foundation.py), [race tests](../tests/database/test_scheduling_authorization_races.py) | App-facing CRUD, real course/batch/session list, recurring edits, schedule visibility, audit, retention and full journey | **No**; private SQL only |
| F10 | Safe class setup reservation and completion | Private reservation, atomic course/batch completion and private status; legacy direct RPC execution denied to app roles | Matching/conflicting reservations, concurrent retries, rollback on forced batch failure, same-workspace wrong actor, pending/completed/unknown status and status-vs-write waits; explicit direct-app denial. [Migrations 019–022](../supabase/migrations), [scheduling tests](../tests/database/test_scheduling_foundation.py) | App-accessible reviewed wrappers; discovery/acknowledgement; lifecycle/retention; account-change recovery; remaining revocation races; real JWT and browser-to-DB flow. Old server action now returns unavailable | **No**; private SQL only |
| F11 | Eligible academy lookup | Default-off server-only draft for active owner/admin workspaces | Mocked query filters, no user, invalid provider data, empty list and provider errors. [Lookup tests](../apps/web/src/lib/scheduling/list-class-workspaces.test.ts) | Real PostgREST/RLS and signed JWT verification, pagination, selector UI and membership changes after selection | **No**; mocked lookup only |
| F12 | Intelligent quality gate and CI | Registry, test selection, reports and GitHub workflows | Tests for mapping, changed-file selection, missing/skipped/stale evidence and receipts; local full gate runs. [Gate](INTELLIGENT_QUALITY_GATE.md), [workflow](../.github/workflows/intelligent-quality.yml) | Gate only evaluates mapped scenarios; branch-protection enforcement and latest hosted run must be checked separately | **Engineering automation**, not a product journey |
| F13 | Students, fees and posts screens | Placeholder routes | Source confirms “Coming soon”; no completed product-flow evidence. [Students](../apps/web/src/app/%28coach%29/students/page.tsx), [Fees](../apps/web/src/app/%28coach%29/fees/page.tsx), [Post](../apps/web/src/app/%28coach%29/post/page.tsx) | Real students, enrollment, fees/payments and private posting workflows | **No**; placeholders |

## 2. Pending end-to-end feature and scenario register

These are scenarios to implement and verify, not claims that a test currently exists. “Decision” identifies an unresolved product/privacy choice, not a requirement for the founder to approve routine engineering.

| ID | Pending feature | End-to-end journey and required positive / negative scenarios | Dependencies / open decisions | Status |
| --- | --- | --- | --- | --- |
| P01 | Live email sign-in and account provisioning | Request code → receive real email → enter valid code → verified session → authorised page → sign out; invalid/expired/reused code, resend limits, provider outage, refresh, account switch and revoked session | Test provider and environment; account creation, email-change and recovery policy. No real user data until approved | Planned; `AUTH-LIVE-OTP` |
| P02 | Academy / independent-coach onboarding | Create workspace → choose type → establish owner → reopen correct workspace; duplicate requests, invalid details, inactive owner, cross-tenant access and creation retry | Real sign-in; reviewed workspace UI and hosted authorization | Partial local SQL |
| P03 | Staff invitations and multi-workspace roles | Invite staff → accept or decline → choose workspace → perform permitted action; expired/revoked invite, suspended membership, duplicate acceptance, role change and cross-workspace denial | Invitation lifecycle, membership administration, audit | Planned |
| P04 | Child and provisional guardian onboarding | Authenticated parent creates child → sees provisional relationship → returns after sign-in; duplicates, invalid data, retry, revoked/disputed guardian and unauthorized viewing | Parent UI, real auth, privacy and consent; declaration is not verified legal guardianship | Partial local SQL |
| P05 | Guardian-initiated connection | Parent requests connection → authorised academy staff reviews → approve/reject → parent sees status; duplicate/expired request, revoked guardian, suspended workspace, concurrent approval and no automatic enrollment | UI, privacy-safe status, audit and real auth | Partial local SQL |
| P06 | Coach-initiated invitation and guardian actions | Coach invites → intended guardian confirms, skips or rejects → both see outcome; expired/reused invite, wrong guardian, replay and revocation | Invitation channel and expiry; declaration wording and dispute process. `CONNECTION-COACH-INVITATION` | Planned |
| P07 | Guardian verification and disputes | Self-declaration recorded separately from verification; handle conflicting claims, disputes, review, revocation and sensitive-data access | Formal method, acceptable evidence, timing, reviewer and retention require decisions. Self-declaration alone must not grant sensitive access | Deferred / decision; `GUARDIAN-FORMAL-VERIFICATION` |
| P08 | Create a real course and first batch | Select eligible academy → enter names → reserve intent → complete both → see persisted result; invalid names, switched account, lost response, parallel tabs, duplicate/conflicting requests, suspended membership and rollback | Finish reviewed authenticated reservation/status/ack protocol; close all bypasses; real auth and UI | Partial private foundation; `LEARNING-DELIVERY` |
| P09 | Manage course, batch and coach assignments | Owner/admin creates, views and edits course/batch; assigns/removes coach; assigned coach accesses permitted work. Test cross-workspace, duplicate assignment, removal vs write and suspended staff | Real read visibility rules, audit, retention and lifecycle | Partial private foundation |
| P10 | Session scheduling | Assigned coach creates one-off or weekly session → parent/coach sees authorised schedule; edit one vs future, cancel, exceptions, overlapping sessions, duplicate retries, removed coach and cross-academy access | Recurrence persistence, visibility, exception and overlap policy. Prioritise India-first workflows; retain existing time safeguards | Partial private foundation |
| P11 | Student enrollment lifecycle | Approved connection → enroll in batch → active/completed/withdrawn/cancelled → view permitted history; duplicate/concurrent enrollment, invalid batch, unauthorized actor, capacity and withdrawal | Enrollment is separate from connection; transition/visibility rules and capacity need definition | Planned; `ENROLLMENT-LIFECYCLE` |
| P12 | Attendance | Coach marks attendance for a valid session and enrolled child → authorised parent views it; absent/late/correction, duplicate concurrent update, unassigned coach, wrong workspace and withdrawn child | Enrollment, sessions, correction/audit policy, guardian visibility | Planned; `ATTENDANCE-AUTHORIZATION` |
| P13 | Learning content and lesson delivery | Create course/lesson → associate lesson to session → record delivered learning → authorised guardian sees permitted history; draft/published, updates, wrong tenant and revoked access | Course/lesson lifecycle, historical visibility and retention | Planned; `LEARNING-DELIVERY`, `GUARDIAN-HISTORY` |
| P14 | Private class diary and media | Coach drafts update → adds authorised media → publishes to intended guardians → parent reads it; consent absent/revoked, wrong audience, upload failure, editing/removal and cross-workspace leakage | Media storage, purpose-specific consent, moderation and retention decisions | Planned; `DIARY-MEDIA-CONSENT` |
| P15 | Fees and payment status | Coach records fee expectation/payment status → authorised user sees accurate state; duplicate entries, correction/refund, access control and reconciliation | Product scope, payment provider and paid-service approval if needed; no payment integration established | Placeholder / needs scope |
| P16 | Notifications and reminders | Event → recipient preference/consent → queued message → delivery or retry → user opens correct authorised content; opt-out, duplicate, invalid destination and provider failure | Notification channels, delivery provider, consent and retention | Planned |
| P17 | AI-assisted drafting | Coach requests draft → reviews/redacts → explicitly publishes permitted content; unsafe output, child-data leakage, provider failure and no consent | AI provider, privacy/data-processing and cost decisions; human review and audit | Planned / decision |
| P18 | Account, ownership and history | Deactivate/remove user → transfer owner where required → preserve permitted history → process deletion request; revoked access, multiple guardians, conflicts and deletion failures | Retention periods, anonymisation, exceptions and dispute resolution need decisions | Planned / decision; `ACCOUNT-RETENTION`, `GUARDIAN-HISTORY` |
| P19 | Phone OTP | If later approved: request/receive/verify phone code; expiry, abuse, rate limits and recovery | Explicitly deferred from email-first V1; provider and costs require decisions | Deferred; `PHONE-OTP` |
| P20 | Pilot, security and operations | Deploy reviewed version → monitor → investigate failure → restore service; penetration/privacy review, load, backup/restore, alerting, accessibility and real-device tests | Founder approval for pilot, hosting/production access and real children’s data; deployment design | Planned |

| P21 | Privacy-safe provider discovery | Find an intentionally published coach, academy or course → review public details → begin an authorised connection; unpublished entries, stale availability, private rosters and child search must not be exposed | Confirm discovery scope, publication rules and access boundaries; do not infer approval for a full marketplace | Planned / scope decision |

## 3. Milestones and test automation

| Milestone | Current assessment | Exit still required |
| --- | --- | --- |
| M0–M1: development and frontend foundation | Historical foundation complete; current dashboard is demonstration data | Production readiness is not implied |
| M2: authentication and data | Partial; mocked login and synthetic database foundations | Real auth, hosted security, consent and verified end-to-end flows |
| M3: classes and students | Partial private foundations and practice UI; not an M3 completion | Real classes, scheduling, enrollment and secure parent/coach journeys |
| M4: attendance | Planned | Capture, correction, parent visibility and authorization E2E |
| M5: class diary | Planned | Private publishing, media and consent E2E |
| M6: AI and notifications | Planned | Approved providers, privacy, output quality and delivery checks |
| M7: pilot readiness | Planned | Security, performance, monitoring, deployment and founder approval |

| Automation / scenario simulation | Last observed local evidence for the source snapshot | Meaning and limitation |
| --- | --- | --- |
| Frontend component and helper tests | 110 passed | Includes mocked providers; does not establish live auth or real data |
| Database unit/security and selected transaction races | 167 passed | Synthetic identities in isolated local PostgreSQL; includes temporary-grant historical behavior tests |
| Standalone concurrent scenarios | 4 passed | Workspace, child, connection and approval concurrency; not every concurrency case |
| Browser | 3 passed | Invalid email, disabled OTP and example schedule/preview; not complete product E2E |
| Quality engine | 51 passed | Gate selection/evidence behavior, not proof that all feature requirements are specified |
| Lint, typecheck and production build | Passed locally | Does not prove deployed or hosted behavior |

Evidence provenance: the last recorded local run was prepared against base commit `ae002a7` with the subsequent server-action changes present in the working tree; its source fingerprint was `96f49f73f3fba0d707d73af809353977221be4d0257fe1981b7cdecf49c88a76`. A fresh plan at HEAD `d1580e0` reported the same fingerprint. The old receipt names the pre-commit base, so this report does **not** present it as a new run on the committed HEAD. The ignored `test-results/` files may not persist. No new test execution is claimed by this report. Inspect [Quality Evidence](QUALITY_EVIDENCE.md) and actual CI runs for later verification.

The registry currently contains 291 mapped entries: 281 marked implemented/covered and 10 planned or deferred/missing. These entries are primarily exact executable scenarios and do **not** imply 281 complete product features. The ten registry gaps are represented in P01, P06–P08 and P11–P19 above; this wider report also lists cross-cutting work not captured by those ten labels.

## 4. Decisions and update rules

| Topic | Current position |
| --- | --- |
| Routine technical implementation and test fixes | Proceed within the current authorised scope; no founder input for ordinary engineering choices. |
| Formal guardian verification, disputes and retention | Exact method, timing, evidence and retention need product/privacy decisions before the affected release. |
| Real data, hosting, deployment and paid providers | Require the applicable explicit founder authorisation and reviewed security evidence. |
| Maintaining this register | After each verified feature slice, update the relevant rows and evidence date; keep the roadmap, build progress and executable registry as canonical owners. Do not convert a local or mocked result into an E2E-complete claim. |

**Next engineering action:** Finish the reservation recovery and acknowledgement protocol, including secure app-facing access and failure/concurrency checks, then integrate and test the real class setup journey end to end.
