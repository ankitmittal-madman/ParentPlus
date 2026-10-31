# ParentPlus Decision Log

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
