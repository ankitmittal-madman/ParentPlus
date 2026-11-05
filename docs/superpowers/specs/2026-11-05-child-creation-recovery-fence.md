# Child-creation recovery fence — local draft

## Problem and scope

After a parent submits a profile, an empty creation status does not prove that the original request failed: it can arrive later. After a reload the tab retains a request reference but deliberately does not retain the child's name. Asking the parent to enter the name again cannot prove the payload matches the original; the two requests could race with different names. The current client therefore keeps the request unresolved. Migrations 036 and 037 and a default-off application flow implement a local draft; neither hosted deployment nor release is authorized or verified.

## Local draft outcome

Give the original signed-in account an explicit way to resolve an uncertain request before starting another. Under the same database transaction and actor lock used for creation:

1. If the exact request and prior intent already created the current profile, report its existing result only after current guardian access is checked.
2. If the original request has not created the current profile and its expected prior state is still valid, persist a rejection bound to that exact actor, request ID and prior intent. Replaying the same recovery request must return the same durable outcome, including after a lost response. Every creation entry point must check this rejection before creating or replaying a profile. A delayed original request must then fail.
3. If the prior state has advanced and the original outcome cannot be proven, including when another request is current, report **unknown**. Do not report that the original request failed or expose a different profile as its result.

A rejection must be durable across tab closure, later requests and transaction retries. Without an independently enforced expiry, do not delete it merely because time has passed. Its privacy, retention, abuse and eventual deletion policy must be decided and reviewed before release. The record must not contain the child's name. The server must obtain the identity from the verified session and database `auth.uid()`; tab storage is untrusted context, not authority.

The local application clears its tab marker only after it verifies the original actor, request and prior, a committed rejection or exact existing result, and successful marker removal. Errors, account changes, revoked access, unavailable storage, missing control or disabled controls remain unresolved. A separate status check is needed before offering a fresh request, with protection against concurrent advancement. A fenced outcome applies to the exact actor, prior intent and request tuple, not proof that the UUID never appeared in older generations. Migration 037 archives name-free references when future current intents are superseded. The history lookup returns only found or unknown after checking the original actor and guardian access; the UI asks for a fresh status check before offering another creation. Already overwritten intents cannot be reconstructed. Deleting the referenced child cascades to its history, making that result unknown. This does not provide cross-device coordination, and access verification is point-in-time.

## Required tests before implementation is considered complete

- Creation commits first; recovery observes the exact created profile, with access checks.
- Recovery commits first; delayed original requests with the same or changed payload cannot create a profile, including after a new generation.
- Both transaction orders with rollback, concurrent duplicate recovery, different request IDs and changed prior IDs.
- Wrong account, missing authentication, revoked or disputed guardianship, and private table/function privileges.
- Missing or disabled control, control-disable races, stale prior state and an already superseded request: no false success or false absence.
- Lost recovery response and retry, account change or unmount during recovery, storage failures and marker tampering.
- Browser-to-server and signed-JWT/provider verification, plus review of retention and operational escalation before release.

The database diagnostic `ChildCreationJourneyTests.test_empty_status_does_not_prevent_a_later_creation` checks only that a later synthetic database request can create after an empty status in separate transactions. It does not simulate a real network delay or prove the proposed safeguard.

## Local integration simulation

The actual React panels and server actions are tested together with a synthetic in-memory provider and mocked session observer. One test injects a later request into the fake provider; it is not evidence of a real second browser tab or database transaction. These jsdom tests do not replace real browser-to-database, signed-JWT or hosted-provider verification.

## Isolated enabled browser checks

The separate enabled browser suite uses Chromium and the actual Next application with preseeded synthetic session data and a local in-memory provider. The runner removes root environment files from its temporary copy, scrubs the process environment, and runs the services and browser in a network namespace with loopback-only IP interfaces and routes. This is not filesystem isolation and does not prove host Unix-domain sockets are inaccessible. The normal disabled-feature suite remains separate. CI requires both exact JUnit reports and fails closed if the namespace cannot be created. The fake provider is not evidence of actual database authorization, signed-JWT verification, true database concurrency, email delivery or hosted behaviour.

| Scenario | Required enabled browser case |
| --- | --- |
| Create, confirm and list a synthetic profile | `creates and confirms a profile using a synthetic provider` |
| Unconfirmed response, a second tab advances and the first recovers | `recovers an unconfirmed request after another tab creates a later profile` |
| Original account changes while a request is unresolved | `keeps an unresolved request locked after an account switch` |

The quality gate requires the three exact browser cases in addition to the existing disabled-feature browser evidence; the feature remains disabled by default.
