# Batch enrolment implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development.

**Goal:** Explicit DB-backed child-to-batch enrolment and parent class visibility.
**Architecture:** Private enrolment/receipt/event tables, scoped RPCs, validated server actions and prototype-aligned client panels.
**Tech Stack:** PostgreSQL17, Next.js16.4.3, React19, TypeScript, Vitest, Playwright.
**Spec:** ../specs/2026-11-10-enrolment-design.md

## Global Constraints

Preserve all work/data/stash. No worktree, reset, new account or paid service.
Dummy .test/123456 remains. Reference original files remain unchanged.
Connection does not auto-enrol. New copy EN/HI. Product writes use ordinary sessions.
SQL/code/API contracts follow the spec verbatim. Do not commit/push independently;
root coordinates the reviewed integrated checkpoint using existing authorisation.

## Review Focus

Revocation while waiting; same request different actor/target; uncertain reply;
stale status version or terminal reopening; parent seeing another child's class.

### Task 1: Database enrolment contract and regressions

**Files:** migration052; tests/database/test_enrollments.py; corresponding CI migration/count/cleanup guards; deploy inventory; requirements mappings for these tests.
**Interfaces:** Produces all six SQL RPC signatures in spec.
- [ ] Write failing SQL contracts; execute RED on isolated fixture.
- [ ] Implement private tables/RPCs with atomic grants, locks, receipt binding/events.
- [ ] Verify positive,negative,retry,rollback,pagination and observed concurrency histories.
- [ ] Register runner/count/cleanup/migration safeguards; report exact evidence and current diff. Do not touch frontend or founder originals. Coordinate fixed disposable DB container with root.

### Task 2: Server actions and enrolment screens

**Files:** src/modules/enrollments/*; src/lib/enrollments/*; EN/HI messages; Students/profile page integration; necessary component tests/requirements mappings.
**Interfaces:** Consumes six RPCs; produces six typed server actions and manager/parent panels as spec.
- [ ] Read installed Next guidance; failing validation/identity/output tests RED.
- [ ] Implement actions with ordinary verified sessions; component tests RED then panels GREEN.
- [ ] Prototype mobile list/batch filters, explicit child enrolment, state controls/reasons,
  stable uncertain request, late session invalidation; parent saved classes.
- [ ] Focused tests,lint/types, self-review. Do not alter source originals or DB contract.

### Task 3: E2E evidence and integrated delivery

**Files:** e2e-qa/enrollments.spec.ts; quality/browser-scenarios.json; canonical progress/evidence/handoff/architecture documents.
**Interfaces:** Consumes actual UI and local backend.
- [ ] Real local two-account enrolment/lifecycle/reload scenarios and mapped actions.
- [ ] Review integrated diff; fix regressions and run selected full suites once final source is stable.
- [ ] Commit, deploy testing migration preserving fingerprints, push/PR/merge and inspect CI/Vercel.
- [ ] Continue next attendance/Today slice; do not pause for routine founder confirmation.
