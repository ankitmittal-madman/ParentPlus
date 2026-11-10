# Hosted founder testing plan

Spec: ../specs/2026-11-10-hosted-founder-testing.md

- [x] Reproduce disabled-login and local-only hosted-runtime guards.
- [x] Support explicit hosted testing, pin the selected existing project and keep service keys server-only.
- [x] Add Vercel non-secret testing defaults; retain an explicit later launch switch.
- [x] Rehearse001–013-to-049 and apply missing hosted test migrations with per-file atomic receipts, preserving original rows.
- [x] Enable implemented hosted test features and prepare exact manual Vercel key steps.
- [x] Finish current-source regression suites, hosted build checks and independent-review fixes.
- [x] Founder confirms PARENTPLUS_TEST_SERVICE_KEY in Vercel Preview and Production.
- [ ] Publish through GitHub and inspect actual deployment.

Existing project is a TEST environment by latest explicit founder instruction.
Do not create another project or reset this one. Vercel technical Production scope
is the current testing app, not permission to claim launch readiness.
