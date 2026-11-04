# ParentPlus — Agent Handoff

Prepared: 2026-11-03, against local baseline
`5b068b995957414a47dd2f47e8b6eb4147958563` on
`feature/intelligent-quality-gate-v1`. This is a preparation snapshot, not a claim
that a future reader's HEAD still equals this baseline. Find the commit containing
this handoff and inspect current Git state before acting.

## Scheduling recurrence foundation — 2026-11-03

The uncommitted local recurrence utility expands one-off or explicitly bounded weekly sessions into UTC instants in a supplied workspace time zone. It rejects ambiguous or nonexistent local times; duration is elapsed minutes. It has resource guards and is not wired to persistent data, UI scheduling, backend authorization or real-provider services. Extended ISO years can occur at the date boundary and consumers must handle or reject them. See [the recurrence spec](superpowers/specs/2026-11-03-schedule-recurrence-engine.md), the current local gate and independent review. Real scheduling remains incomplete.

## Session resume and scheduling decisions — 2026-11-03

The founder confirmed that owners, admins and authorised coaches may manage sessions, and scheduling should support both weekly recurrence and one-off sessions; see DEC-018. DEC-019 confirms assigned-batch coach scope, single or future occurrence edits by user choice, and workspace time zone with user resolution for ambiguous/nonexistent local times. Visibility, overlap, deletion, cancellation and retention policies remain to be designed as needed. The schedule display remains a synthetic preview and is not a real scheduling implementation.

The current local authentication slice also rechecks session state on window focus or return to a visible page when live authentication is enabled. The behavior is tested using simulated events and provider responses; it does not establish continuous background expiry checking, live provider revocation or backend authorization. See [the session resume spec](superpowers/specs/2026-11-03-session-resume-check.md), the latest review and current quality evidence before any checkpoint.

## Session-change safety continuation — 2026-11-03

The local login slice subscribes to provider authentication-change hints when live authentication is enabled, defers user revalidation until after the callback, invalidates stale requests and clears old identity input on account changes. A failed sign-out enters an uncertain state and requires a fresh session check before another sign-out action. The subscription is not established when live authentication is disabled. Focused tests use synthetic events and deferred promises; they do not prove real cross-tab event delivery, remote revocation or timely expiry. The independent reviewer identified account-switch and stale-email races; both were corrected and rechecked. See [the session-change spec](superpowers/specs/2026-11-03-session-change-safety.md) and current local gate evidence.

Real scheduling remains a separate M3 slice. Founder input was requested on which roles can edit schedules and whether recurring and one-off sessions are in scope; do not invent answers. The schedule screen remains clearly labelled synthetic examples only.

## Synthetic schedule preview — 2026-11-03

The current local M3 presentation slice replaces the schedule placeholder with a read-only, clearly labelled synthetic example of course, batch and session time. A local Chromium case also checks the example label and representative session. It does not establish real scheduling, enrollment, attendance or access control. The [schedule spec](superpowers/specs/2026-11-03-schedule-preview.md) records the boundaries and tests. The previous session-restoration work remains in the same uncommitted scope; cross-tab updates and expiry handling are not completed by this schedule preview. Inspect current status, quality evidence and independent review before checkpoint.

## Session restoration continuation — 2026-11-03

The local uncommitted login slice now checks the current user with the provider SDK when live authentication is enabled. It shows a signed-in view only after a provider-confirmed user, shows sign-in for a missing session, and shows an unavailable/retry state for other errors. Disabled mode makes no provider call. A reviewer identified that provider identity does not prove email verification; the UI now uses neutral signed-in wording. Session expiry, cross-tab synchronization, real provider behavior and server-side access authorization remain unverified release gaps. See [the session spec](superpowers/specs/2026-11-03-session-restoration.md), the current gate evidence and independent review before checkpoint.

## Local sign-out continuation — 2026-11-03

The uncommitted sign-in slice now includes an explicit current-session sign-out action after successful verification. The login form returns only after a successful provider response; on failure the view reports uncertain status without claiming the session remains active. The helper is guarded by the disabled-by-default live flag and requests local scope. These are local mocked-provider behaviors, not proof of live sign-out, session restoration, cross-tab handling or protected access. See [the sign-out spec](superpowers/specs/2026-11-03-local-signout.md), current quality evidence and review before checkpoint. No hosted provider or real user data was used.

## Browser test continuation — 2026-11-03

This working tree adds two local Chromium login checks with live OTP disabled and a mandatory browser step before the existing frontend CI receipt. The tests cover invalid email and the disabled-provider response; live sign-in, session handling and hosted CI for this new step remain unverified. Browser tests run against a local server and intercept external page requests; this is not a general server-side network sandbox. [The browser spec](superpowers/specs/2026-11-03-login-browser-tests.md) records scope and limitations. Inspect current Git status, quality evidence and independent review before a checkpoint.

## Current local continuation — 2026-11-03

The historical snapshot below predates the merged `main` checkpoint `ff41e3b`. This continuation is on `feature/intelligent-quality-gate-v1` at baseline `7ad48fe`; the working tree contains the reconstructed email-code form, scenario mappings, tests and documentation. Earlier uncommitted work from a disconnected environment was unavailable and was recreated, not recovered. Inspect Git for exact current status before acting.

The slice is described in [the spec](superpowers/specs/2026-11-03-email-otp-screen.md). The existing helper remains disabled by default and no hosted service is used. Session-aware continuation and sign-out, real OTP delivery, provider template compatibility, account-enumeration assessment and browser E2E remain open before live sign-in. A fresh independent review identified focus handling, session continuation and provider limitations; the focus regression was reproduced and addressed. Check the current local quality evidence and review status before a Git checkpoint. No product, database or privacy decision has changed.

## Recorded state and visibility

- Latest local checkpoint: 5b068b9, the quality-gate and engineering-operating-system commit.
- Its originating founder approval covered that local commit. It did not approve push, merge or hosted actions. Future agents must verify their own task authority; Git alone is not an approval record.
- GitHub feature tip last verified read-only in the preceding audit on 2026-11-03: ac2b1f9af85b531142310fcd851a24c17390f4ae. The local branch was one commit ahead; no upstream tracking was configured. This observation is not live synchronization.
- Starting dirty scope for this session: modified AGENTS.md plus the untracked CODEX_COMMUNICATION_STANDARD.md draft. Both were preserved and extended, not discarded.
- Current work: the approved documentation foundation below. It remains local/uncommitted at preparation; commit and push are not approved.
- Recorded writer: the originating Codex session. This is not a live ownership lock; confirm coordination before overlapping work.

## Product and verification context

Read [Project Context](PROJECT_CONTEXT.md), then
[Build Progress](BUILD_PROGRESS.md) for what is built and
[Quality Evidence](QUALITY_EVIDENCE.md) for what was actually checked. The latter
separates historical application execution from this documentation-only task.
Ten registry gaps remain visible and retain their release consequences in
[the independent audit](INTELLIGENT_QUALITY_GATE_AUDIT.md).

## Pending documentation scope

| Scope | Files |
| --- | --- |
| Short entrypoints | README.md, AGENTS.md, new CLAUDE.md |
| Shared context and boundaries | New PROJECT_CONTEXT.md and SYSTEM_ARCHITECTURE.md |
| Continuity and evidence index | This new AGENT_HANDOFF.md and new QUALITY_EVIDENCE.md |
| Communication draft | Existing untracked CODEX_COMMUNICATION_STANDARD.md, extended for all assistants |
| Reconciliation annotations | BUILD_PROGRESS.md, DEVELOPMENT_ROADMAP.md, DECISION_LOG.md, DATABASE_ARCHITECTURE.md, DB_SECURITY_REVIEW.md |
| Maintenance instructions | FEATURE_DELIVERY_WORKFLOW.md |

Paths without a directory above are under docs, except the three root entrypoints.
Application source, migrations, requirements/policy, CI definitions, engineering
standards and upstream Superpowers files are outside this foundation's edit scope.

## Foundation verification at preparation

[Quality Evidence](QUALITY_EVIDENCE.md) records the observed local checks and
read-only review. References, preservation and the 14-file Markdown scope were
checked; engine/registry validation ran. Frontend/database execution, hosted CI,
connector access and actual future agent compliance were not established for
this documentation snapshot. A passing selection plan is not a completed gate.

## Next actions and approvals

1. Inspect the actual branch, HEAD, dirty/staged paths and any divergence from this snapshot. Preserve unrelated work and report discrepancies before editing.
2. Review the documentation foundation and its exact diff. Follow the shared communication standard, including a proportionate Technical Appendix.
3. Present the complete reviewed scope and verification results for founder approval before a commit. Do not infer commit permission from permission to implement docs.
4. Push is a separate approval. After an approved push, verify the remote ref and actual hosted run before saying these instructions or workflows are GitHub-visible and validated.
5. Propose the documentation CI checker, negative tests and concurrency-aware automated writer as a separately reviewable scope. No such automation is installed by this foundation.
6. Only then select a new product slice through the existing delivery workflow and its privacy/acceptance decisions.

## Session-end maintenance

Update this handoff after meaningful work with preparation baseline/date, observed
remote or supplied-snapshot provenance, dirty scope, evidence references,
failed/unrun checks, unresolved decisions and next action/approval. Record why
architecture or decisions did not need updates rather than generating duplicate
records. Never write an invented future commit or mark a milestone complete from
intention alone. Do not keep adding parallel handoff documents.

If an agent cannot read Git or the cited artefacts, it must state that limitation
and use a supplied snapshot explicitly. Conflicting branches are distinct states;
they are not automatically synchronized by sharing this filename.

## Clock-change error details — 2026-11-03

The local recurrence calculator reports the specific date, local time, time zone and whether a clock-change conflict is ambiguous or nonexistent. It still rejects the conflict rather than selecting a time. This does not implement the user resolution journey or real scheduling. Inspect current Git status and fresh evidence; earlier descriptions of uncommitted work above are historical snapshots.

## Scheduling database foundation — 2026-11-03

A local draft migration adds courses, batches and batch-to-membership assignments, enforcing same-workspace references and denying app-role table access. This is not an authorization implementation: future operations must check active workspace, active membership, role and assignment, including concurrent revocation, before any access is granted. Schedule visibility, sessions, editing, real-provider integration and hosted migration are not implemented. See the scheduling data foundation plan and fresh local test evidence. No hosted resources were modified.

## Private scheduling authorization helper — 2026-11-03

The draft migration contains a private, invoker-rights helper that derives the actor from `auth.uid()`, checks active workspace and membership, batch ownership and coach assignment, and locks relevant rows to transaction end. It has no app-role execution grant and no write operation calls it yet. Standalone calls cannot authorize a later transaction; future trusted mutations must call it and write within the same transaction. Revocation race tests for this helper, full write operations, and independent security review remain required before any exposure or hosted migration.

## Scheduling authorization race coverage — 2026-11-03

Six synthetic local database tests cover workspace suspension, membership suspension and assignment deletion before and after a test-only transaction invokes the private helper and changes a batch. They observe actual PostgreSQL blocking and check whether the synthetic change commits. These tests exercise the helper contract, not a real schedule-writing operation. Independently reviewed application operations, additional race and failure cases, and hosted verification remain required.

## Private single-session write — 2026-11-03

The local draft contains a private UTC-only single-session write with same-transaction authorization and actor/request idempotency. App roles cannot execute it or read its table. It is not ready for app integration: server-authoritative workspace time zones and DST, actual-write revocation and duplicate races, recurring/edit operations, read visibility and independent security review remain open. No hosted migration was performed. Refer to fresh local test evidence for the current snapshot.

## Actual session-write race coverage — 2026-11-03

Eight local concurrency cases exercise the private session write against workspace suspension, membership suspension and assignment deletion in both orderings, and simultaneous identical and changed retries. Inspect the latest test evidence for results. These cases do not expose the operation, replace independent security review, or complete server-side workspace time-zone validation, recurrence, editing or a user journey.

## Private workspace time-zone wrapper — 2026-11-03

The local draft adds a private server-side operation that reads a configured workspace time zone under the authorization transaction, rejects ambiguous/nonexistent minute-precision local times, and calls the private UTC session write. The bounded 2000–2100 implementation searches offsets at second precision, which requires performance review before exposure. PostgreSQL/JavaScript timezone database consistency, zone configuration, an ambiguity-resolution UI, repeat/edit behavior, real-user flows and independent security review remain open; no application access or hosted migration is enabled. Consult the latest test evidence for actual execution results.

## Private initial workspace zone configuration — 2026-11-03

A local private invoker function permits an active owner/admin to set a PostgreSQL-recognized workspace time zone once or retry the same zone. Coaches and app roles cannot call it; changing an established zone is rejected as a temporary engineering safeguard pending existing-session and recurrence semantics. The configuration and session operations lock the workspace for transaction consistency. Review current race-test evidence; user-facing setup, audit, safe future zone changes, resolution UX, performance review and independent security review remain outstanding.

## India-first private course and batch setup — 2026-11-03

The founder requested prioritising Indian parents and proportionate time-zone work. The local draft adds private owner/admin course and batch creation with workspace/membership checks, same-workspace references and request retry identity. It does not expose an application API or implement coach assignment, data reads or user-facing class setup. Actual-write duplicate and permission-revocation races, complete authorization cases, independent security review and end-to-end testing remain before exposure. Existing time-zone safeguards were retained.

## Login focus test timing — 2026-11-03

During the course/batch full regression, the login success focus assertion failed after the success text appeared with focus still on the body. The focused case passed on retry; React applies the focus in an effect. The test now waits for the same focus requirement rather than assuming text appearance and the effect are simultaneous. A deliberate temporary removal of the focus action caused the revised case to fail; after restoring application code the case passed. This establishes that the assertion still detects absent focus, not that every possible intermittent cause is excluded. Consult fresh full-gate evidence.

## Private coach assignment — 2026-11-03

The draft migration adds a private assignment operation for active owners/admins and active same-workspace coaches, with row locks and a duplicate-safe unique assignment. App access, assignment removal, auditing, real scheduling UI, end-to-end verification and independently reviewed release readiness remain open. Consult fresh evidence for the exact test results and Git status.

The coach-assignment review identified missing concurrency coverage. New deterministic cases exercise coach suspension in both transaction orders and simultaneous duplicate assignments. Other manager/workspace revocation and batch lifecycle races remain release gaps; inspect the current gate evidence. No app access or hosted database change was performed.

## Private coach removal — 2026-11-03

A new local draft migration adds private owner/admin removal of a coach assignment, preserving existing sessions while preventing later scheduling writes by the unassigned coach. Assignment and removal acquire the same transaction-scoped advisory lock to serialize conflicting operations, including an absent assignment row. The operation has no app-role grant and no UI or audit trail. Review current isolated test evidence and obtain independent security review before any exposure; no hosted database changes were made.

### Coach assignment replay correction

Independent review identified and local tests reproduced stale add/remove retries undoing later opposite actions. The private draft now requires actor-scoped request IDs and durable payload-bound receipts; unversioned private assignment is removed. Matching historical retries do not repeat the mutation, and conflicting request reuse is rejected. The receipt table retains referenced membership/batch records via foreign keys: retention/deletion decisions and additional concurrent conflict/revocation tests are release gaps. Review fresh gate evidence and independent review; no app access or hosted migration was enabled.

### Private class journey and conflicting requests

A synthetic local database integration case chains private course and batch creation, India workspace configuration, coach assignment, one local-time session and coach removal; it checks retained past session and denial after a delayed old assignment retry. Separate two-transaction cases cover simultaneous request-ID reuse with changed action or batch. Consult fresh gate results. This is not an app E2E journey or hosted integration. UI, visibility rules, audit, retention and performance review remain open.

The private class journey also has a separate-transaction local test covering committed course, batch, assignment, session, removal and delayed replay. It remains a database-only synthetic test; no browser, app-role or hosted integration is established.

## Practice class-setup screen — 2026-11-03

The example schedule includes an in-memory practice-only course/batch preview with explicit unsaved messaging, validation, stale-preview clearing and no network or storage use. This is not a real class creation journey or authorization implementation. Browser, component and gate evidence must be checked for the current snapshot. Real API exposure, persistence, coach selection, permissions, independent review and actual browser-to-database integration remain release blockers.

An independent review of the practice form identified that a single invalid field incorrectly marked both fields invalid. The test reproduced the issue and the component now marks only the affected field. The browser case also checks no non-read request or browser-storage change occurs during the preview; inspect fresh evidence. Full accessibility and real-integration review remain outstanding.

## Local authenticated course wrapper — 2026-11-03

A local draft migration grants the authenticated database role access to one narrow course-creation security-definer wrapper, delegating to the private active-workspace/owner-admin check and request idempotency. It grants no course-table access and accepts no actor ID. Synthetic role/claim tests are not signed-JWT/PostgREST evidence. The draft is not deployed: migration owner and grants, audit/retention, rate limiting, full app integration, real provider verification and independent security review remain required before hosted use. Consult current evidence for actual tests.

The authenticated course draft's local checks include attempted anonymous invocation even with a synthetic claimed ID, attempted direct table insertion, role and status denial, owner/admin retries and deterministic workspace/member suspension and duplicate-request races. Local tests do not validate signed JWTs, PostgREST, hosted function ownership or production settings; these and audit/retention remain release blockers. Inspect the source-bound gate for current results.

## Local authenticated batch wrapper — 2026-11-03

A draft migration adds authenticated-role execution of a narrowly scoped batch-creation wrapper. It delegates to active owner/admin and same-workspace course checks and grants no direct table or private-function access. Tests use synthetic roles/claims; signed JWT/PostgREST, deployed owner and grants, audit/retention, rate limits and actual app integration remain release blockers. Review current source-bound test evidence and independent findings before exposure.

## Local atomic course and batch setup draft — 2026-11-03

A new local authenticated-role security-definer operation creates a course and first batch in one transaction using a separate actor/request receipt. A review identified and the design avoids adoption of partial standalone records with the same caller request ID. A controlled trigger test checks rollback after the batch insert fails and verifies an identical retry. Direct table and anonymous access remain denied. Receipt foreign keys retain associated records; review deletion/retention before exposure. Signed JWT/PostgREST, hosted ownership/privileges, audit, rate limits and application/browser integration remain release blockers. Inspect current gate evidence; no hosted migration was performed.

## Class setup server boundary — 2026-11-03

A server action draft validates workspace/request IDs and names, fails closed unless PARENTPLUS_ENABLE_CLASS_SETUP is exactly true, asks the Supabase server client for the current user and calls the local atomic class-setup RPC with sanitized output. It is not connected to the practice UI and no hosted provider is used by tests. Mocked identity/RPC cases do not prove signed JWTs, deployed owner/grants, rate limits, audit, real workspace selection, request-ID lifecycle or end-to-end functionality. Check fresh gate and independent review before integration.

Independent review found that an app environment flag cannot disable a direct database RPC. The local draft combined RPC now has a separate private database control that defaults off and is locked throughout each call; app roles cannot access it. The shared control also gates the separate course/batch creation wrappers; it does not gate unrelated operations. The future UI must bind uncertain retries to the original authenticated actor/workspace; actor-scoped receipts alone can duplicate a request after account switching. That retry UX, safe control operations, signed JWT verification, deployment review and app integration remain unfinished.

The course and batch draft migrations remain private during partial reconstruction; only the later atomic-setup migration grants authenticated execution after installing the shared default-off database guard. The local initialization script checks effective anon/authenticated execute rights immediately after each earlier migration. This does not establish safe hosted migration ownership or signed-JWT behavior; the server flag remains action-specific, and actor-bound retry UX is still required.

An independent review found that creating security-definer functions and revoking default PUBLIC execution in separate autocommitted statements could expose an ungated function briefly during a partial rollout. Draft migrations 016 and 017 now create and revoke within a single DO statement; 018 does the same for the combined wrapper. Local reconstruction checks post-migration privileges. This source-level correction still requires review under the actual hosted migration tool and ownership model before deployment. The app flag gates only the action; the database control independently gates these three draft creation RPCs. Actor-switch retry UX remains open.

The draft server action now requires an expected actor ID and rejects a mismatch with the authenticated user before calling the RPC. The expected ID is not used as authorization and is not passed to the database. This does not implement a retry UI or preserve the original actor/workspace across navigation; those remain release blockers.

## Draft eligible-workspace lookup — 2026-11-04

A disabled-by-default server action queries the verified user's own active owner/admin memberships joined to active workspaces and returns only workspace IDs and names. It relies on existing row-level security and the write operation must independently recheck authorization. The lookup is not wired to a screen; the provider and PostgREST query shape have only been exercised with mocked responses, not real signed JWTs or hosted resources. Pagination, real provider behavior, account-switch/retry state, independent review and the complete browser-to-database journey remain open. Check current test evidence and Git status before relying on this draft.

## Class setup retry investigation — 2026-11-04

A proposed browser-storage retry helper was tested and independently reviewed, then removed before integration. Read-then-write storage operations cannot prevent separate tabs from overwriting pending requests, and browser storage can expose class names on a shared device. A real setup form needs a reviewed durable retry and reconciliation design, including account changes, multiple tabs, reload, privacy, loss of connectivity and unknown outcomes. Do not claim that the server action's expected-actor comparison alone solves these cases. The workspace lookup remains disconnected and class creation is disabled by default.

The proposed recovery design now distinguishes the existing completion receipt from an earlier durable intent, and records open concurrency, lost-reservation-response, privacy, revocation and pagination requirements. It is a design candidate only: no reservation/status operation or real form exists. See the class setup server boundary specification before implementing it.

The recovery design now has a proposed conservative one-unresolved-intent-per-actor/workspace lifecycle and an explicit concurrency test matrix. It is not implemented: acknowledgement, permission-change recovery, persistence and all new database operations still require code and tests. No UI should rely on the proposal as a working guarantee.

## Private class reservation prototype — 2026-11-04

A local migration introduces a private, app-inaccessible reservation primitive: one actor/workspace intent, payload-bound retries, default-off control and manager checks. The unique constraint serializes concurrent reservations. It does not implement completion, acknowledgement, status recovery, deletion/retention, release or a UI and must not be exposed as a complete workflow. The existing authenticated creation RPC can still be called separately when enabled; it does not consume this reservation. The migration is not deployed. Consult fresh test evidence and independent review before further work.

## Private reservation completion — 2026-11-04

A local-only private completion operation locks the actor/workspace intent and atomically creates its course and batch, retaining their IDs on the intent for retries. It uses the intent as its own receipt and does not adopt a receipt from the separately callable atomic RPC. Synthetic tests cover retry, same-workspace wrong actor, batch-failure rollback, app-role denial, receipt collision and concurrent completion. Independent review and fresh gate evidence are needed for the final source. Status discovery, acknowledgement, retention, revocation races, real auth/provider and UI are unfinished; the existing authenticated atomic RPC bypasses reservations, so no end-to-end duplicate protection is claimed and the app/database controls remain default-off. No hosted migration was performed.

## Private class setup recovery status — 2026-11-04

A local-only, app-inaccessible status function checks active manager/workspace and the default-off control, then locks the current actor's visible reservation. It returns pending or completed for a visible record; a missing row is explicitly unknown, including when a reservation is in flight. A status result is a snapshot, not proof that no other API created a class. Direct authenticated creation still bypasses reservations; acknowledgement, permission-revocation races, real provider, UI and hosted verification remain outstanding. Consult fresh evidence and review; no hosted migration was performed.

## Direct creation access restriction — 2026-11-04

Draft migration 022 revokes app-role execution on all three legacy course/batch creation entrypoints. A separate test executes each as an authenticated manager with the control enabled and expects denial. Historical wrapper behavior tests temporarily grant execution only in disposable test fixtures; their successful calls do not describe current application permissions. Frontend action unit tests mock the provider and do not establish live access; the existing server action will fail against the restricted database and remains disconnected. Reservation APIs, status and completion are still private, so no class setup UI is enabled. Verify effective hosted ownership/role memberships and migration rollout before any future deployment.

## Old class setup server action disabled — 2026-11-04

The server action still validates inputs and identity when its flag is enabled, but returns unavailable without invoking the legacy unreserved RPC. This is an additional application-side safeguard, not an operational class setup journey. Three old mock-RPC behavior tests were replaced by tests asserting that no RPC is invoked; existing input, identity, account-change and error-redaction checks remain. Database restriction, reservation access, status recovery, acknowledgement, real provider and UI work still need the documented review before exposure.

## Private acknowledgement draft — 2026-11-04

A local, app-inaccessible acknowledgement primitive locks the caller's completed intent, checks current manager access and the default-off database control, rejects pending/other-actor intents, and is idempotent. Acknowledgement deliberately retains the unique reservation slot and result; it cannot yet start another class. The status function still reports completed without exposing the acknowledgement bit. A safe slot-release/new-request protocol, recovery after permission changes, full race and hosted/provider verification, and app/UI integration remain open. This is not a complete class-setup journey and no hosted migration was performed.

## Acknowledgement permission-race coverage — 2026-11-04

Local tests exercise acknowledgement against workspace suspension, membership suspension and database-control disablement in both transaction orders, using observed PostgreSQL blocking and checking the committed acknowledgement marker. Inspect fresh gate evidence. A next-class transition is not implemented: independent review identified a delayed legacy request race, requiring a common actor/workspace serialization point and a durable request identity that binds previous intent and payload. Safe retention, lost-token recovery, app access and real-provider testing remain open.

## Private next-class transition draft — 2026-11-04

A local-only migration adds private next-class transition and receipts. The prior completed/acknowledged intent is archived; a new request ID is bound to actor, workspace, prior intent and normalized payload. Matching retries return the original new intent ID. The actor/workspace advisory lock is shared with legacy reservation; after history exists untokenized reservation fails closed. This is a local draft, not app access. Historical result discovery, retention/deletion, lost request-token recovery, other revocation and race orderings, real auth/provider and UI remain open. Inspect fresh gate evidence and independent review; no hosted migration was performed.

## Private current-class recovery draft — 2026-11-04

A private local recovery operation checks manager and database control, serializes with reservation/advance, and returns the current actor/workspace intent and its linked request details, including completion and acknowledgement state. An absent visible intent remains unknown. It is a current snapshot: if further advances occur it cannot identify which older request a user meant, and it does not provide archived-result lookup. It does not authorise app access; retention/privacy, missing/corrupt receipt, revocation orderings, real provider and UI still require review. No hosted migration was performed. Inspect current tests and independent review.

Independent review found that a corrupted private recovery receipt could mix the current intent with a different payload or another actor's history. Local recovery now checks payload and prior-history actor/workspace consistency and fails closed; tests reproduce both defects against privileged synthetic corruption. App roles cannot modify these tables. Inspect fresh evidence and review; this does not implement old-result discovery or the app journey.

## Private archived-class recovery draft — 2026-11-04

A private local lookup returns one known, archived, completed class setup only to the same active workspace manager while the default-off database control is enabled. It shares the actor/workspace transition lock; a missing, current or other-actor identifier returns unknown, not failure. It requires the caller to know the old intent ID and provides no list or lost-identifier discovery. Retention, permission-change races, real provider, application access and user-facing recovery remain open. Inspect fresh evidence and independent review; no hosted migration was performed.

Independent review identified that an internally corrupted archive could reference a batch from a different course in the same workspace. The private lookup now checks the relationship and fails closed; a synthetic corruption test covers it. Archived names remain historical snapshots, not a guarantee of current names. App roles cannot modify these private rows. Inspect fresh evidence; no hosted migration was performed.
