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
| M3 | Classes and students | Batches, schedules, enrollment, student profiles | Core journeys pass end-to-end tests | In progress: saved weekly classes, academy connections and verified batch enrolment; attendance/remaining flows remain |
| M4 | Attendance | Attendance capture and parent visibility | Attendance journey and security tests pass | Planned |
| M5 | Class diary | Updates, media, consent, parent feed | Safe coach-to-parent publishing works | Planned |
| M6 | AI and notifications | AI drafting, redaction, reminders | Quality, privacy and delivery checks pass | Planned |
| M7 | Pilot readiness | Security, performance, monitoring, deployment | Founder approves pilot readiness gate | Planned |

## Two-sided MVP pilot journey — reconciled 10 November 2026

The founder confirmed that the MVP must support both the parent and the
independent-coach/academy experience. A preview or an isolated database test on
either side does not satisfy this objective. The proposed first complete journey
is: coach or academy signs in and sets up a workspace and class; parent signs in
and creates a child profile; an authorised connection is established; the child
is enrolled in the class; the coach records attendance; and the authorised parent
can see it. The [founder pilot kit](founder-references/2026-11-10/README.md) now supplies the
product requirements and stages. Current founder testing uses fictional accounts
and the existing testing backend; launch and real-family gates remain separate.

| Area | Required capability for the proposed journey | Current state | Completion evidence |
|---|---|---|---|
| Shared identity | Real email sign-in and account recovery for both sides | Founder dummy OTP and real local Auth/session journeys verified; hosted real email delivery remains unverified | Real test accounts exercise success, invalid/expired code, recovery, sign-out and account switching |
| Coach / academy workspace | Independent coach or academy creates or accesses the right workspace | Saved first-use onboarding and workspace access tested locally; existing founder hosted entry flow previously manually confirmed | Owner/admin/coach roles, multiple workspaces, suspension and cross-workspace denial verified end to end |
| Coach class management | Authorised coach creates and manages a course, batch and sessions | Saved course, batch and weekly sessions tested locally; broader scheduling lifecycle remains | Saved class and session journey, assigned-coach checks, retries and concurrent changes verified |
| Parent and child | Parent creates and recovers a child profile and sees permitted records | Real local profile creation/recovery/list journey verified; legal verification and wider guardian lifecycle remain | Real identity, duplicate and interrupted requests, account change, revoked/disputed access and safe recovery verified |
| Connection and enrollment | Parent and workspace establish an authorised connection; child is enrolled separately | Invitation-based connection plus explicit batch lifecycle/parent classes verified locally;052 applied to existing TEST; original data preserved; GitHub publication pending at preparation | Request/approval and enrollment work for authorised users; expiry, retry, revocation, wrong workspace and audit checks pass |
| Coach attendance | Authorised coach records and corrects attendance for an enrolled child | Planned | Session, enrollment and coach authorization, concurrent edits and correction/audit scenarios pass |
| Parent visibility | Authorised parent sees the agreed attendance or learning outcome | Planned | Correct guardian sees the correct child's permitted data; wrong/revoked guardian and cross-workspace access denied |
| Pilot operations | A controlled pilot works on real devices with support and recovery | Planned | Real-provider E2E, privacy/security review, mobile testing, monitoring, backup/restore and founder approval completed |

Coach and academy workflows must be tested as complete user journeys, including
negative, interrupted and concurrent cases; parent-side success cannot substitute
for coach-side completion. Results must distinguish simulated checks from real
provider and hosted evidence. No calendar launch date is established until scope,
dependencies and remaining work are estimated against a verified baseline.

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
