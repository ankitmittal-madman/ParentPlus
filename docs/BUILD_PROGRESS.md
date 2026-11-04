# ParentPlus Build Progress

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
