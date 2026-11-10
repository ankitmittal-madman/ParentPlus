# Local first-use implementation plan

Spec: ../specs/2026-11-09-local-first-use.md
Architecture: existing Auth/RPC/RLS contracts, Next.js actions and default-off UI;
local Docker Supabase plus Playwright/Mailpit real-provider integration.

- [x] Verify policy and missing local work; inspect/fetch recovery base and reconcile patch.
- [x] Start slim local Supabase; diagnose disk/proxy/template permissions; apply all 49 migrations.
- [x] Reproduce missing coach link, reconcile patch and loopback configuration with regressions.
- [x] Add failing actor/key, control and uncertain-outcome action tests, then workspace onboarding.
- [x] Run real parent and coach first-use browser flows including reload and revocation.
- [x] Run frontend/build, full isolated DB regression, upgrade rehearsal and quality checks.
- [x] Independent review, resolve important findings, maintain canonical evidence and handoff.

No commit, push or hosted change. Review focus: forged actors, lost responses,
storage corruption, account switches, disabled controls and local-only fixture guards.
