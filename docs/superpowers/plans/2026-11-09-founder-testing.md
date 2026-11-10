# Founder testing implementation plan

Spec: ../specs/2026-11-09-founder-testing.md
User explicitly delegated routine design/engineering choices and requested dummy
login and founder veto for local testing; proceed within those bounds.

- [x] Add failing server-mode/endpoint/code tests; implement local dummy OTP exchange.
- [x] Connect existing login helpers to founder mode without changing normal OTP.
- [x] Add founder navigation, record-count inspection and membership override.
- [x] Add local launcher and browser suite using actual local sessions/database.
- [x] Review, run regressions and maintain handoff/progress/evidence truthfully.

Keep hosted Supabase untouched. Preserve earlier changes and the recovery stash.
