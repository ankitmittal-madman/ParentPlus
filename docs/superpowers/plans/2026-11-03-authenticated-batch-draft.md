# Local authenticated batch-creation draft plan

**Goal:** Prepare a narrow authorized batch-creation boundary following course creation.

**Architecture:** A security-definer wrapper with empty search path delegates to the private workspace-manager checked operation. It accepts no actor ID and grants authenticated execution only; table and private-helper privileges remain denied.

**Spec:** [Real scheduling design](../specs/2026-11-03-real-scheduling-design.md).

1. Test owner/admin and retry success; deny anonymous, coach, invalid input, inactive workspace/membership, cross-workspace course, direct table access and changed retries.
2. Verify real PostgreSQL lock order under manager/workspace suspension and simultaneous matching/conflicting requests. Use synthetic identities and disposable containers.
3. Add the local draft migration, review metadata and owner, map exact cases, run full gate and independent review. Real signed-JWT/PostgREST, audit/retention and UI integration remain release gaps.
