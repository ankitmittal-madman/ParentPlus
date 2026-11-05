# Atomic course-and-batch setup plan

**Goal:** Prepare a safe single-request course and first-batch creation operation.

**Architecture:** A security-definer database wrapper with an empty search path calls the private course and batch operations within the same transaction using the same request ID. A later application layer must be disabled by default, verify identity, validate inputs and call this operation without accepting a caller-supplied actor ID. No table grants are added.

**Spec:** [Real scheduling design](../specs/2026-11-03-real-scheduling-design.md).

1. Test owner/admin creation, identical and conflicting retries, second-step rollback, unauthorized actors, anonymous invocation and table denial; observe initial failure.
2. Implement the local migration, then test simultaneous requests and manager/workspace suspension in both orders.
3. Independently review and run complete local gate. Real signed-JWT/PostgREST, audit, rate limits, client integration, hosted ownership and deployment approval remain open.
