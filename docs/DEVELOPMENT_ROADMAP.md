# ParentPlus Development Roadmap

Status: Working roadmap
Repository: ParentPlus
Original foundation branch: setup/parentplus-foundation

Reconciled on 2026-11-03: this is the product milestone plan, not the live Git
state. See [Build Progress](BUILD_PROGRESS.md) for verified slices and
[Agent Handoff](AGENT_HANDOFF.md) for the current operation/checkpoint. Local
foundation code does not establish complete auth, hosted deployment or release.

## Development principles
- Build one verified feature slice at a time.
- Preserve the existing Coach App design reference.
- Use synthetic data until security and consent controls are implemented.
- Run automated tests before milestone completion.
- Prepare verified Git checkpoints under the approval rules in [Engineering Standards](ENGINEERING_STANDARDS.md); implementation permission is not commit or push permission.
- Do not merge into main without review and passing checks.
- No paid service or real children's data without founder approval.

## Milestones

| ID | Milestone | Deliverables | Exit criteria | Status |
|---|---|---|---|---|
| M0 | Development setup | Repository, Next.js, TypeScript, Tailwind, preview | App builds and preview works | Complete |
| M1 | Frontend foundation | Components, design tokens, navigation, tests | Responsive preview and checks pass | Complete |
| M2 | Authentication and data | Supabase, roles, core schema, consent, RLS | Access and security tests pass | Partial local foundation; exit criteria incomplete |
| M3 | Classes and students | Batches, schedules, enrollment, student profiles | Core journeys pass end-to-end tests | Planned |
| M4 | Attendance | Attendance capture and parent visibility | Attendance journey and security tests pass | Planned |
| M5 | Class diary | Updates, media, consent, parent feed | Safe coach-to-parent publishing works | Planned |
| M6 | AI and notifications | AI drafting, redaction, reminders | Quality, privacy and delivery checks pass | Planned |
| M7 | Pilot readiness | Security, performance, monitoring, deployment | Founder approves pilot readiness gate | Planned |

## Historical checkpoint policy

The bullets below retain the earlier checkpoint convention. They are not current
authorization: the current task and engineering standards require reviewed scope
and approval before commits, with separate authorization for push/merge/deployment.

- Small change: test locally.
- Completed feature: local Git commit.
- Milestone or end of session with meaningful changes: push to GitHub.
- Cleanup only after verifying a remote checkpoint.
- Record milestone commit hashes in BUILD_PROGRESS.md.

## Open engineering work
- Resolve npm audit findings before deployment.
- Review mobile navigation accessibility.
- Establish automated end-to-end tests.
- Finalize Supabase schema before handling real family data.
