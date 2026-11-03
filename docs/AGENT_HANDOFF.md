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
