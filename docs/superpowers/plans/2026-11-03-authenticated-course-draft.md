# Local authenticated course-creation draft plan

**Goal:** Prepare one narrow course-creation boundary for the real class-management flow.

**Architecture:** An authenticated-role security-definer wrapper calls the existing private workspace-manager checked operation and returns its UUID. The wrapper accepts no actor ID, fixes its search path, denies anonymous execution and grants no direct table access. All tests run in disposable PostgreSQL with synthetic auth claims.

**Spec:** [Real scheduling design](../specs/2026-11-03-real-scheduling-design.md).

1. Test owner/admin success and idempotency; reject anonymous, coach, cross-workspace, suspended membership/workspace, malformed and changed requests; verify direct table access remains denied.
2. Observe missing-operation failures, then add a new local migration; test manager revocation in both orders and concurrent duplicate creation.
3. Run full local gate and independent review. Before any hosted deployment or UI claim, verify real signed JWTs, deployed ownership/privileges, audit/retention, rate limits and real app integration.
