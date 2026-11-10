# ParentPlus Decision Log

## Reading this history (reconciled 2026-11-03)

Earlier entries and their implementation-status wording are retained as dated
intent, not current execution/deployment facts. Later confirmed decisions take
precedence over earlier pending lists: email-first OTP is confirmed by DEC-011.
DEC-002's founder-run Cloud Shell workflow and DEC-004's checkpoint convention
are historical; current [engineering standards](ENGINEERING_STANDARDS.md) and task
approvals govern agent execution and Git actions. No new product/privacy decision
is made by this annotation. Current implementation and evidence are indexed in
[Build Progress](BUILD_PROGRESS.md), [Database Architecture](DATABASE_ARCHITECTURE.md)
and [Quality Evidence](QUALITY_EVIDENCE.md). Local code does not prove deployment.

## DEC-001: Repository
Use the existing ParentPlus GitHub repository.
Reason: Preserve Git history and Superpowers installation.

## DEC-002: Development workflow
ChatGPT guides implementation; founder executes commands in Google Cloud Shell.
Reason: No Codex assistant available inside the editor.

## DEC-003: Initial frontend
Use Next.js App Router, React, TypeScript and Tailwind CSS.
Reason: Compatible with the development kit and existing application setup.

## DEC-004: Git checkpoints
Use feature-level local commits and milestone-level GitHub pushes.
Reason: Reduce unnecessary commits while protecting development progress.

## Pending decisions
- Final authentication method.
- Final Supabase schema.
- Hosting and deployment arrangements.
- AI provider and children's data handling.

## Confirmed M2 product and architecture decisions
Decision date: 2026-10-31
Status: Confirmed
Scope: ParentPlus V1

## DEC-005: Two-way connection initiation
Both the academy/coach and guardian can initiate a connection.
- Coach invites: guardian confirms.
- Guardian requests: authorized workspace staff confirms.
- An initiating party does not need to approve its own request again.
- Invitations, QR codes and connection codes identify a destination but do not grant automatic access.
- Connection and enrollment are separate.
Reason: Reduce onboarding friction while requiring mutual intent.

## DEC-006: Shared workspace architecture
Independent coaches and academies use the same workspace model.
An independent coach can operate a single-member workspace.
An academy can have multiple authorized staff members.
Reason: One product architecture supports both business types.

## DEC-007: Multi-workspace coach membership
One coach account may belong to multiple workspaces.
Roles and permissions are scoped independently to each workspace.
Reason: Coaches may work independently and at multiple academies.

## DEC-008: Shared child identity
One platform-level child identity may connect to multiple workspaces.
Attendance, class updates and operational records remain workspace-specific.
Reason: A unified guardian experience without cross-academy data exposure.

## DEC-009: Guardian-controlled child linking
Linking an existing child identity requires verified guardian authorization.
No unrestricted directory of children, guardians or private academy rosters.
No automatic identity linking using names or phone numbers alone.
Reason: Protect children's privacy and prevent incorrect identity matches.

## DEC-010: Separate connection and enrollment
A verified workspace-child connection does not automatically enroll a child.
Enrollment links the child to a specific batch or class.
Reason: Keep relationship verification separate from class participation.

## Implementation safeguards
- Use synthetic data until privacy and security controls are verified.
- Enforce authorization in backend and database policies.
- Audit connection approvals, revocations and sensitive changes.
- Define invitation expiry, dispute handling and guardian verification before implementation.
- Decisions above do not constitute a completed database schema.

## DEC-011: Email OTP authentication
Status: Confirmed
Date: 2026-10-31
Scope: ParentPlus V1

Decision:
- Use email OTP as the initial sign-in method.
- One authenticated account may access multiple authorized workspaces.
- Phone OTP is deferred from the initial release.
- Supabase Auth is the proposed implementation provider.
- Account recovery and email-change verification require separate design.
- Email authentication does not establish legal guardianship.

Reason:
- Reduce initial implementation complexity and SMS dependency.
- Support passwordless onboarding.
- Keep authentication separate from child access authorization.

Implementation status:
Design only. No authentication service configured.

## DEC-012: Progressive guardian verification
Status: Confirmed
Date: 2026-10-31
Scope: ParentPlus V1

Decision:
- A parent can create a child profile after email OTP authentication.
- The initial guardian relationship is provisional.
- Creating a profile does not establish verified legal guardianship.
- Academy linking requires additional authorization.
- Private academy records remain inaccessible until the relationship is approved.
- Child identity linking cannot rely on names or phone numbers alone.
- Sensitive operations require appropriate additional verification.

Reason:
- Reduce parent onboarding friction.
- Allow parents to begin using ParentPlus before joining an academy.
- Preserve child privacy and prevent unauthorized academy access.

Implementation notes:
- Separate account authentication, guardian verification and workspace authorization.
- Model guardian verification status explicitly.
- Record approvals, revocations and disputes in audit history.
- Define handling of conflicting guardian claims before implementation.

Implementation status:
Design only. No database or authentication changes deployed.

## DEC-013: Guardian declaration in MVP; formal verification deferred
Status: Confirmed
Scope: ParentPlus V1 MVP

Long-term requirement:
- Support formal guardian authorization and verification.
- Exact verification method, evidence, timing and workflow remain undecided.
- Document upload and verification may be considered later.

MVP decision:
- Present parents with Confirm, Skip and Reject actions.
- Confirm records a self-declaration of authority.
- Skip leaves the request pending.
- Reject declines the connection.
- No document upload or formal verification workflow in MVP.
- A declaration must not be represented as verified legal guardianship.

Architecture:
- Store guardian declaration separately from formal verification.
- Store academy connection status separately from both.
- Record actor, timestamp and relevant request.
- Do not grant access to sensitive real child information solely
  because a parent clicked Confirm.

Deferred decisions:
- When formal verification becomes mandatory.
- Which evidence is acceptable.
- Who reviews verification evidence.
- How disputes and revocations are handled.
- Document retention and deletion rules.

Reason:
Keep MVP onboarding lightweight while preserving the ability
to implement stronger guardian verification later.

Implementation status:
Design only. No authentication or database implementation completed.

## DEC-014: Course and learning structure
Status: Confirmed
Scope: ParentPlus V1

Decision:
- Subjects, courses, lessons, batches and class sessions are separate entities.
- A course defines what is taught.
- A batch represents a scheduled delivery of a course.
- A session represents an individual teaching occurrence.
- Multiple coaches may teach batches or individual sessions.
- Lessons describe planned learning content and may be linked to sessions.

Reason:
Support independent coaches and academies offering structured learning programs.

## DEC-015: Persistent academy-child relationships
Status: Confirmed
Scope: ParentPlus V1

Decision:
- Workspace-child relationships survive enrollment completion or withdrawal.
- Enrollment status and workspace relationship status are separate.
- Historical relationships do not imply unlimited access to child data.
- Post-enrollment access is restricted by authorization and retention policies.
- Alumni marketing permissions are separate and deferred.

Reason:
Preserve historical relationships without granting unrestricted data access.

## DEC-016: Parent access to learning history
Status: Confirmed
Scope: ParentPlus V1

Decision:
- Authorized guardians retain access to permitted historical learning records.
- Completing or leaving a class does not automatically remove historical access.
- Learning records remain associated with the child and original workspace.
- Retention, deletion and consent restrictions still apply.
- Advanced learning analytics and export features may be implemented later.

Reason:
Support a continuous view of a child's learning journey across academies.

## DEC-017: Account lifecycle and historical data
Status: Confirmed
Scope: ParentPlus V1

Proposed approach:
- Account deactivation, membership removal and data deletion are separate operations.
- A departing coach loses workspace access without automatically deleting historical teaching records.
- Workspace ownership must be transferred before an Owner account can be deleted.
- Guardian access revocation must not automatically destroy historical learning records.
- Historical access remains subject to authorization, consent and retention requirements.
- Account deletion requests require a controlled privacy workflow.
- Retention periods, anonymization and deletion exceptions remain unresolved.

Implementation status:
Architecture proposal only. No database behavior changed.

## DEC-018: Schedule management and recurrence
Status: Confirmed by founder
Date: 2026-11-03
Scope: ParentPlus class scheduling

- Workspace owners, admins and authorised coaches may create and edit sessions.
- Support both recurring weekly classes and one-off sessions.
- Authorisation is workspace-scoped; this decision does not grant access to children or another workspace.

Implementation note: Define the exact coach assignment and permission checks, recurrence boundaries, timezone and daylight-saving behaviour in the scheduling design and verify them before real use. This decision does not establish that scheduling is implemented or deployed.

## DEC-019: Schedule assignment, recurring edits and time zone
Status: Confirmed by founder
Date: 2026-11-03
Scope: ParentPlus class scheduling

- Coaches may manage only batches assigned to them.
- A recurring-class edit may apply to one occurrence or all future occurrences, according to the user's choice.
- Use the workspace time zone; ask the user to resolve ambiguous or nonexistent local times caused by a daylight-saving transition.

These choices do not approve hosted changes, define every retention/visibility rule or establish that scheduling is implemented.

## DEC-020: Continuity of the selected Supabase project
Status: Confirmed by founder
Date: 2026-11-07
Scope: ParentPlus hosted database

- The founder intends the currently selected ParentPlus Supabase project to be
  used for test accounts now and for real family data later.
- Treat the selected project as a long-lived database, not a disposable test
  database. Preserve data and migration history; do not reset or replace it as
  a routine testing step.
- Use fictional data for testing. Test-only data cleanup, backup and recovery,
  retention and consent controls must be designed before any real family data is
  introduced. Keep destructive and concurrency tests in isolated databases.
- This decision does not establish that hosted migrations, identity, access
  policies or privacy controls have been verified, and does not authorise real
  family data before the applicable security and pilot readiness checks.

## DEC-021: Founder-only local testing mode

Date: 2026-11-09. Source: explicit founder instruction in this development session.
Use dummy .test emails and OTP 123456 for local founder testing, with actual
frontend/backend/database flows. Founder controls can override synthetic-account
workspace access so policy testing does not prevent product testing. Existing
parent/coach operations continue to exercise database policies; the local founder
console is a separate administrative capability. Require development runtime,
explicit server/public flags and exact local API endpoint. Never enable this mode
against hosted Supabase or production. No external email or identity verification
is implied. This does not change the production email-OTP direction in DEC-011.
The founder asked routine implementation decisions to proceed autonomously.


## DEC-022 — Existing backend and Vercel app are founder testing environments (2026-11-10)

Explicit founder clarification supersedes DEC-021's local-only boundary for the
current testing app. Use existing Supabase fmavpazczahxeusqbxuh; no separate project
or account. Fictional .test email/123456 verification and founder membership
overrides may run in Vercel's technically named Production environment. This is
product testing, not launch. Real launch checks return only after explicit launch
instruction and implementation/verification; a production Next build is not that
instruction. Preserve existing records, keep private credentials server-side and
retain normal persona database policies. Direct deployment through existing
GitHub→Vercel is authorised. A launch-stage build disables forced testing defaults.
