# Private initial workspace time-zone configuration plan

**Goal:** Establish an authorization-checked local operation for initial workspace zone setup.

**Architecture:** An invoker-rights private operation derives the actor from auth.uid(), locks the active workspace and active owner/admin membership, validates a PostgreSQL-recognized named zone and sets it only if unset or identical. Changes to an established zone are rejected pending the product's existing-session and recurrence semantics. No application execution grant is provided.

**Spec:** [Real scheduling design](../specs/2026-11-03-real-scheduling-design.md).

1. Test owner/admin success and identical retries, coach/anonymous/cross-workspace/inactive denial, invalid zones, changed-zone rejection and app-role denial.
2. Observe failures and implement the private operation in the draft migration. Verify both ordering of workspace-zone setup and session creation in isolated PostgreSQL sessions.
3. Run full local regressions, evidence and independent security review. Before exposure, finish the zone-change policy, audit trail, real session integration, clock-change resolution UX and release checks.
