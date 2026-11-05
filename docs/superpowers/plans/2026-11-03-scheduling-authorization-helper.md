# Scheduling authorization helper plan

**Goal:** Build a local-only authorization building block for future schedule mutations.

**Architecture:** A private invoker function derives the actor from `auth.uid()`, locks the active workspace, actor membership, batch and (for coaches) assignment using transaction-scoped row locks, and raises a uniform authorization error on rejection. No app role receives execute permission. A future trusted operation must invoke it and mutate within the same transaction.

**Spec:** [Real scheduling design](../specs/2026-11-03-real-scheduling-design.md).

1. Add tests for active owners/admins, assigned coaches, unauthorized actors, inactive membership/workspace and denied function execution.
2. Observe failures, implement the private function in the uncommitted draft migration, then rerun all isolated database and quality checks.
3. Before exposing any mutation: test both orderings of membership, workspace and assignment revocation races; verify no identity spoofing, replay or cross-workspace behavior; obtain independent security review.
4. Use two independent PostgreSQL sessions and confirm the blocking relationship for both orders of workspace suspension, membership suspension and assignment removal. The test-only transaction invokes the helper and changes a synthetic batch; it does not establish an application-facing write operation.
