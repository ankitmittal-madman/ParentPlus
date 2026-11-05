# Private course and batch setup plan

**Goal:** Enable local, controlled course and batch creation as a foundation for India-first class scheduling.

**Architecture:** Private invoker-rights operations derive the actor from auth.uid(), lock the active workspace and owner/admin membership, validate names, enforce same-workspace courses, and use actor/request uniqueness for safe retries. No application-role execute or table access is granted.

**Spec:** [Real scheduling design](../specs/2026-11-03-real-scheduling-design.md).

1. Add tests for valid creation and retries, changed payload, cross-workspace references, invalid names and unauthorized roles; confirm they fail.
2. Implement private operations and reconstruct all migrations. Register exact tests and run the full local gate.
3. Before exposure: verify actual-write duplicate and revocation races, independently review security, implement assignment and visibility operations, integrate with the UI and test the full journey.
