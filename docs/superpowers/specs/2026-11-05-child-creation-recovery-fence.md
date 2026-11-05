# Child-creation recovery fence — proposed local design

## Problem and scope

After a parent submits a profile, an empty creation status does not prove that the original request failed: it can arrive later. After a reload the tab retains a request reference but deliberately does not retain the child's name. Asking the parent to enter the name again cannot prove the payload matches the original; the two requests could race with different names. The current client therefore keeps the request unresolved. This document proposes a safeguard; it is not implemented or enabled.

## Proposed outcome

Give the original signed-in account an explicit way to resolve an uncertain request before starting another. Under the same database transaction and actor lock used for creation:

1. If the exact request and prior intent already created the current profile, report its existing result only after current guardian access is checked.
2. If the original request has not created the current profile and its expected prior state is still valid, persist a rejection bound to that exact actor, request ID and prior intent. Replaying the same recovery request must return the same durable outcome, including after a lost response. Every creation entry point must check this rejection before creating or replaying a profile. A delayed original request must then fail.
3. If the prior state has advanced and the original outcome cannot be proven, including when another request is current, report **unknown**. Do not report that the original request failed or expose a different profile as its result.

A rejection must be durable across tab closure, later requests and transaction retries. Without an independently enforced expiry, do not delete it merely because time has passed. Its privacy, retention, abuse and eventual deletion policy must be decided and reviewed before release. The record must not contain the child's name. The server must obtain the identity from the verified session and database `auth.uid()`; tab storage is untrusted context, not authority.

The application should clear its tab marker only after it verifies the original actor, request and prior, a committed rejection or exact existing result, and successful marker removal. Errors, account changes, revoked access, unavailable storage, missing control or disabled controls remain unresolved. A separate status check is needed before offering a fresh request, with protection against concurrent advancement. No implementation may assume the proposed rejection alone supplies cross-device coordination or historic receipts.

## Required tests before implementation is considered complete

- Creation commits first; recovery observes the exact created profile, with access checks.
- Recovery commits first; delayed original requests with the same or changed payload cannot create a profile, including after a new generation.
- Both transaction orders with rollback, concurrent duplicate recovery, different request IDs and changed prior IDs.
- Wrong account, missing authentication, revoked or disputed guardianship, and private table/function privileges.
- Missing or disabled control, control-disable races, stale prior state and an already superseded request: no false success or false absence.
- Lost recovery response and retry, account change or unmount during recovery, storage failures and marker tampering.
- Browser-to-server and signed-JWT/provider verification, plus review of retention and operational escalation before release.

The database diagnostic `ChildCreationJourneyTests.test_empty_status_does_not_prevent_a_later_creation` checks only that a later synthetic database request can create after an empty status in separate transactions. It does not simulate a real network delay or prove the proposed safeguard.
