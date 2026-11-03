# Private single-session write plan

**Goal:** Establish a closed local database write for one session with authorization and retry safety.

**Architecture:** A workspace-scoped session row references a batch with composite keys. A private invoker function checks authorization in the same transaction, validates bounded UTC instants and uses an actor/request unique constraint for atomic retries. No application role receives table or function access.

**Spec:** [Real scheduling design](../specs/2026-11-03-real-scheduling-design.md).

1. Test successful creation and matching retries, rejected changed-payload retries, unauthorized actors and invalid times, and denied application-role privileges.
2. Observe failing tests, then implement the private table and operation in the local draft migration.
3. Run isolated PostgreSQL reconstruction, all database and frontend checks and exact evidence validation.
4. Before app access: implement server-authoritative workspace time zones and daylight-saving resolution; test actual-write revocation and duplicate races; implement recurrence, edit and visibility contracts; complete independent security review and integration/E2E tests.
5. Verify the actual session write against workspace, membership and assignment revocation in both transaction orderings, and simultaneous identical and changed retries. Use two database sessions and observe blocking, returned identity and persisted record count.
