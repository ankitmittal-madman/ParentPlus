# Intelligent Quality Gate v1 Implementation Plan

**Goal:** Implement the supplied autonomous quality-gate brief on feature/intelligent-quality-gate-v1.
**Architecture:** Deterministic registry validation and impact selection; reusable CI jobs; exact-case runtime evidence verification.
**Tech Stack:** Python standard library, Vitest, PostgreSQL 17, GitHub Actions.
**Spec:** docs/superpowers/specs/2026-11-03-intelligent-quality-gate.md

## Constraints
Preserve security assertions and GitLab backup. Synthetic isolated data only. No push, merge, deployment, hosted migration, paid services or repository security changes. Use existing checkout. No fixed test-count policy in the new engine.

## Review focus
Renames/deletions and missing Git bases must not hide changed paths. Policy edits must not weaken security floors. A passing job without fresh exact-case evidence must fail. New tests must require registry mapping. Planned features must never acquire passing status from unrelated tests.

## Tasks
- [x] Write failing behavioral tests for registry schema, inventory completeness, coverage, policy floors, change selection and evidence rejection.
- [x] Implement scripts/quality/quality_gate.py; collect actual inventories and populate quality/requirements.json and quality/policy.json. Verify red-to-green tests.
- [x] Integrate reusable existing frontend/database jobs with intelligent-quality.yml and same-run artifact validation. Preserve all checks and backup automation.
- [x] Run gate tests, inventory/impact CLI positive and negative checks, existing frontend and isolated database checks, workflow validation and diff checks.
- [x] Document usage, gaps, evidence and limits; review the full diff and report unverified hosted CI explicitly.

Execution is native in this session under the user's explicit instruction to plan then proceed autonomously. No additional design or execution approval is required within that scope.

## Completion evidence

39 gate tests passed after test-first negative regressions and the independent review fix pass. All 67 registered application/database cases passed via existing runners; frontend lint, typecheck/build, actionlint, syntax, changed-file secret scan and whitespace validation passed. Generated final gate evidence is in test-results/quality/verified/. Hosted CI has not run. Work remains uncommitted for founder review.
