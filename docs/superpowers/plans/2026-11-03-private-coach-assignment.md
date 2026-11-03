# Private coach assignment plan

**Goal:** Give the scheduling foundation a controlled, retry-safe way to assign an academy coach to a batch.

**Architecture:** A private invoker operation checks the active owner/admin actor and locks the workspace, batch and target active coach membership before inserting a unique assignment. No app role receives access. Revocation of an assignment and user-facing management are separate unfinished work.

**Spec:** [Real scheduling design](../specs/2026-11-03-real-scheduling-design.md).

1. Test assignment, duplicate retry, inactive/non-coach/cross-workspace targets, unauthorized actors and app-role denial; run the tests before implementation.
2. Implement the private operation, map exact tests and run database, frontend and quality checks.
3. Review race conditions and independent security findings; do not expose the operation or claim the scheduling journey is complete.
