# Private coach assignment removal plan

**Goal:** Let an academy owner or admin remove an assigned coach without deleting class records.

**Architecture:** Private invoker-rights assignment and removal operations serialize on a workspace/batch/membership advisory lock. They verify the active manager and batch in the same workspace; removal is idempotent and takes the existing assignment row lock, so a concurrent session write either completes first or is denied after removal. App roles remain unable to execute these functions.

**Spec:** [Real scheduling design](../specs/2026-11-03-real-scheduling-design.md).

1. Test authorized and repeated removal, post-removal scheduling denial, invalid cross-workspace references, unauthorized actors and no app-role access.
2. Test real PostgreSQL blocking in both orders of removal versus session creation and removal versus assignment; verify persisted outcomes.
3. Implement in a new migration, retain all existing tests and run the full isolated gate; keep the operation private until independent security review, audit and UI integration.
4. Exercise an India-first private database journey from course and batch creation to assigned-coach session and removal. Test simultaneous reuse of one request ID with changed action or batch; verify one receipt and no unintended mutation. These are local database integration tests, not app E2E tests.
