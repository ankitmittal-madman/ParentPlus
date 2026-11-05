# Scheduling data foundation implementation plan

**Goal:** Add a local-only, inaccessible-by-default data foundation for courses, batches and explicit coach assignments.

**Architecture:** Three workspace-owned tables with composite foreign keys enforce same-workspace relationships. RLS and revoked application-role privileges deny reads and writes until separately reviewed authorization operations exist. This slice stores no children or session records.

**Tech stack:** PostgreSQL 17, SQL migrations, Python unittest, isolated Docker test database.

**Spec:** [Real scheduling design](../specs/2026-11-03-real-scheduling-design.md).

## Verification and constraints

- Synthetic data only. No hosted migration or production access.
- Test valid same-workspace relationships, cross-workspace course and membership references, and denial of application-role reads and writes.
- Reconstruct all migrations, check existing security/concurrency tests and database cleanup, and register exact tests in the quality gate.
- Do not claim schedule management, coach authorization, visibility or a user journey is implemented.
- Independent security review remains mandatory before exposing these tables to application users.
