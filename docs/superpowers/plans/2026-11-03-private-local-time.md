# Private workspace-local time plan

**Goal:** Prevent private session creation from guessing or accepting a caller-chosen zone.

**Architecture:** A private wrapper checks and locks workspace authorization, reads a workspace zone, resolves a minute-precision local time using PostgreSQL's timezone database, rejects gaps and overlaps and calls the existing private UTC write in the same transaction. The workspace zone must already be configured by trusted setup; there is no app-facing configuration or scheduling operation.

**Spec:** [Real scheduling design](../specs/2026-11-03-real-scheduling-design.md).

1. Add tests for Kolkata conversion, New York gaps and overlaps, Lord Howe half-hour transitions, missing/invalid zones and app-role denial; observe failure.
2. Implement the private bounded resolver and local-time write; reconstruct all migrations and run database, frontend and quality-gate checks.
3. Before exposure, verify zone configuration authorization, timezone database consistency, performance, realistic time-zone transitions, repeated-time choice UX, write races, independent security review and end-to-end flow.
