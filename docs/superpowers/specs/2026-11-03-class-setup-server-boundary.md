# Class setup server boundary

## Problem and current scope

The current local draft connects the coach recovery panel to a server-only
bridge and a versioned reservation protocol. With both app and private database
controls explicitly enabled, the form creates a course, batch and bounded
weekly session series in one transaction, recovers pending/completed state, and
requires acknowledgement before another setup. The founder selected weekly
sessions through a fixed end date. The form previews the occurrence count and
uses the academy time zone, which an owner/admin may set once when absent. Local
time gaps and folds fail closed; schedules are limited to 104 occurrences.
Controls remain default-off. No hosted resource is accessed during tests. The
local form is not a production rollout.

## Contract and threats

When its server flag is enabled, the current action validates UUID-shaped workspace, request and expected-actor IDs and trimmed 1–120-character names. It asks Supabase Auth for the current user and rejects a missing or mismatched identity, then returns unavailable without attempting a write. The expected actor is an untrusted mismatch guard, not an authority for database access. Provider errors remain generic. This does not establish real JWT validation or real account-switch recovery.

Before a future write path is exposed, the database must independently enforce active workspace-manager authorization and the reviewed reservation protocol; the client must retain or recover the correct request identity. Rate limiting, true provider validation, workspace selection, application integration, retention and audit remain required.

## Tests

Mocked tests cover disabled mode, malformed inputs, signed-out/error responses, mismatched identity and the absence of a legacy RPC call. These tests do not establish signed-JWT/PostgREST behavior, actual provider access or a full browser journey.

## Independent app and database switches

The server environment flag gates this server action only; it cannot block a direct PostgREST/RPC call. The local draft combined RPC additionally checks a private singleton database control, defaulting to disabled and locked for the write transaction. App roles cannot read or change this control. The shared guard applies to the combined RPC and to the standalone course and batch creation RPCs; it does not gate unrelated operations. Neither control is permission to deploy. Pending retries are actor-scoped: the future UI must bind an uncertain retry to the original user and workspace and reconcile on account changes before offering a retry. The server action rejects an expected actor that differs from the verified current user. That is only a boundary check: the identity-switch UX and trustworthy retention of the original actor and workspace are not implemented.

## Recovery design under investigation — 2026-11-04

The existing committed receipt is created in the same transaction as the course and batch. It makes an identical retry safe only while the caller still knows the original request ID, actor, workspace and payload; it does not help a caller discover a lost request ID. A lookup returning “no receipt” must not be treated as proof of failure while the original transaction may still be running.

A candidate design is a server-side intent, reserved before the class creation attempt, with a server-generated ID and owner scoped to `auth.uid()`. A signed-in owner/admin can find their own unresolved intents for an active workspace after a reload or on another device. The create operation would lock and consume the same intent atomically with the existing class-setup receipt. A competing retry must wait for the same lock and return the committed result or safely perform the original operation. This is a proposal, not an implemented capability.

Before implementation or exposure, resolve and test these constraints:

- Recheck active user, workspace and manager membership on every list, reserve and create; anonymous, cross-user and cross-workspace reads and writes must fail closed. Define how a removed manager learns an outcome without exposing workspace data.
- Coordinate reservation and creation across tabs and devices. A reserve response can itself be lost; discover existing unresolved intents rather than silently issuing another. Two intentional identical classes must remain possible without treating their names as a universal uniqueness key.
- Define a bounded, explicit list and pagination, and ensure concurrent reserve, retry, cancel and completion transitions cannot produce false “not created” results or duplicate classes.
- Minimise stored data and define retention, shared-device and sign-out behaviour. Do not rely on browser storage as authority or persist arbitrary client fields. The design must not store child information for setup.
- Fail closed when the status is unknown, the feature is disabled or dependencies are unavailable. Preserve an explicit recovery path for in-flight transactions, stale intents and role revocation; do not silently discard uncertain work.
- Use a database-backed atomic protocol with deterministic concurrency and fault-injection tests, authenticated API tests and browser-to-database tests. Review migration ownership and grants and independently review the final implementation. No hosted migration is authorised by this design.

Independent review identified a critical reservation race: an empty list is only a snapshot and cannot establish that another reservation is not in flight. The decision that no unresolved intent exists and creation of a new intent must be atomic under a server-defined scope, using a transactional lock and constraint or an equivalent durable coordinator. The design must also define how to intentionally start a separate identical class after a prior intent is resolved. Bind the normalised payload, actor and workspace immutably to an intent; coordinate create, retry, cancellation and expiry transactionally with its receipt. A cancelled or expired intent must not later execute or silently release protection for an uncertain write. If access is revoked or the feature is disabled while an operation is in flight, a privacy-preserving recovery response must not assert that creation failed without synchronising with the original transaction; leave the outcome unresolved if it cannot be safely determined. These are design requirements, not implemented guarantees.

### Candidate reservation lifecycle and verification plan

For the initial draft, restrict each actor and workspace to one unresolved reservation. The server must serialize reservation using a transaction-scoped lock and a database uniqueness constraint; a preliminary SELECT alone is insufficient. A same-payload reservation returns the existing reservation ID, while a different payload returns a conflict requiring the caller to resolve the existing reservation. A completed reservation remains discoverable until an explicit acknowledgement has committed. A new intentional class, including one with identical names, may start only after acknowledgement. The action must explain the previous result before asking for that acknowledgement. This conservative restriction is an engineering proposal, not an established product rule.

Creation locks the reservation and writes both class records, the existing completion receipt and the reservation's completed state in one transaction. An identical retry must return the original result. A status read must serialize with an in-flight creation or return unknown; it must never convert an absent or inaccessible result into a claim that creation failed. No automatic expiry or cancellation may remove unresolved duplicate protection. Any acknowledgement must be scoped to the actor and workspace, lock the same reservation and refuse to acknowledge an unknown or in-flight result. If a permission or feature-control change prevents safe recovery, report an unresolved outcome without exposing class details to an unauthorised actor.

Required executable checks before attaching a UI include: two simultaneous reservations with identical and different payloads; reservation commit with lost response; a delayed first reservation racing a second; simultaneous creation retries; lost create response; creation versus acknowledgement in both orders; failed insert rolling back every write; workspace or manager suspension in both lock orders; disabled control; cross-user and cross-workspace attempts; changed payloads; and a deliberate second identical class after acknowledged completion. Run these using separate database transactions with observable lock waits, and independently review the function privileges, scope, direct-RPC bypasses and hosted migration ownership. Real-provider and browser coverage remains separate from synthetic local database tests.

## Proposed app-facing recovery journey (not implemented)

1. Verify the signed-in user and retrieve only active owner/admin workspaces through reviewed, authenticated server operations. Selecting an academy is a point-in-time choice: every database operation must independently recheck access. If identity, workspace or provider state cannot be verified, show an unavailable state and make no write.
2. Recover the current intent before offering a fresh action. Show its academy and class details for explicit user review. Pending, completed, acknowledged, unknown, unavailable and account-changed states must be distinct. Unknown is not proof of failure and must not automatically trigger creation, acknowledgement, cancellation or a new request.
3. A completed result can be acknowledged only after displaying the result to the current authorised user. An acknowledgement is a stored marker, not evidence that a user actually saw or understood it. The next class must use a stable request ID bound to the previous intent and payload; an uncertain response must retain that identity or recover it through a reviewed server operation, not silently generate another ID.
4. Offer discovery of the same manager's archived setups only after authorisation. Current private discovery is ordered by UUID, not date, and each page is a separate snapshot. A page sweep can miss records inserted before its cursor; a UI must describe this limitation and support a fresh scan/deduplication. Do not claim exhaustive or chronological history until a robust snapshot or monotonic ordering design is implemented and tested.
5. Account changes, sign-out, workspace suspension, membership removal and feature disablement must halt writes and avoid displaying stale sensitive data. Show an unresolved outcome when the original request cannot be safely reconciled; do not claim failure or expose another actor's record. Browser storage must not be treated as authority; minimise persisted data and resolve shared-device, deletion, retention and audit requirements before use.
6. Implement app-facing wrappers only after security review of grants, owner, signed JWTs, direct-RPC bypasses, partial rollout and abuse/rate limiting. Test with real signed identity, concurrent browser tabs, lost network responses, both orders of permission changes, backend transaction failures, refresh/reload, accessible error states and full browser-to-database journeys. Authenticated app-facing SQL wrappers exist behind a database control that defaults to disabled; the underlying helpers remain private. The old action remains unavailable. This section is a design, not a claim of implemented UI or provider support.

## Cross-manager recovery finding — 2026-11-04

A local diagnostic used a fresh network-isolated PostgreSQL database, synthetic identities and the draft database control enabled only inside a rolled-back test transaction. Two active managers belonged to the same academy. The first manager began a Dance/Morning setup and received `created:pending`. The second manager's current-setup lookup returned `unknown`; beginning the same setup also returned `created:pending`. The private intent table then contained two reservations. The transaction was rolled back. This reproduces an actor-scope gap; it does not prove that any hosted database or real account was affected.

This blocks enabling real class-setup writes. A solution must coordinate the decision to begin, advance, complete and recover across relevant managers and devices at the database boundary. It must not use browser storage as the authority, expose another manager's private intent details, confuse an unavailable result with absence, or stop an authorised manager from intentionally creating a separate class after the previous operation is safely resolved. Define lock ordering, release and reconciliation rules before implementing. Direct authenticated RPC calls must obey the same safeguards as the UI. The singleton database control and web flag must remain disabled until the complete protocol is tested and independently reviewed. Workspace coordination alone does not restore the original actor after a reload or account switch; discovery and reconciliation for that separate case also require a reviewed design.

Required regression scenarios include simultaneous and delayed requests from different managers, an original request arriving after a status check, both orders of completion versus retry, account switches and reloads, device changes, unknown or unavailable database responses, permission revocation and workspace suspension, same-name intentional new classes after resolution, privacy of other managers' details, and direct RPC calls. Use real database concurrency tests and, before release, signed-provider and browser-to-database tests. Passing a test that merely reproduces two reservations would document the defect, not resolve it.

## Versioned local workspace guard — draft 048, 2026-11-07

Migration 048 supersedes the unversioned single-pending-intent guard for the
app-facing begin operation. Each manager reads a workspace generation and
submits that value with a stable request ID. A shared workspace-version lock
orders begin against acknowledgement; acknowledgement advances the generation,
so a delayed request from a pre-acknowledgement screen fails and must refresh.
Matching request IDs replay their original outcome. The old three-argument app
begin wrapper is revoked. Local isolated tests cover stale snapshots, refreshed
intentional setup, idempotent retry and the concurrent acknowledgement-first
ordering. This is only a database slice. The control and UI remain disabled;
app integration, signed-provider testing, full identity-loss recovery, retention,
independent review and hosted rollout remain open.

## Local workspace guard draft — 2026-11-04

Migration 031 adds a partial unique index allowing at most one unacknowledged intent per workspace. This conservative restriction also blocks independent class setups in the same academy until the first is acknowledged. Existing duplicate unresolved intents make index creation fail; rollout needs a non-destructive preflight and reconciliation plan. The database control and UI remain disabled.

This does not establish complete duplicate prevention. A request sent before acknowledgement but received after it can still create a new intent; distinguishing that delayed request from an intentional later class requires a workspace generation or equivalent fencing protocol. If the original manager cannot acknowledge, other managers have no recovery path. Reload/account-switch identity recovery, revocation, privacy, signed-provider integration and actual browser journeys remain release blockers. Independent review identified the delayed-request and availability gaps.
