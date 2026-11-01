# ParentPlus Database Architecture

Status: Draft for founder review
Milestone: M2 Authentication and Data Foundation
Reference decisions: DEC-005 through DEC-010

## 1. Architecture objective
Support independent coaches and academies through one shared platform.
Allow one coach to belong to multiple workspaces.
Maintain one child identity with isolated workspace-specific records.
Support guardian-controlled linking and two-way connection initiation.

## 2. Identity domain
- profiles: authenticated user profiles.
- children: minimal platform-level child identity.
- guardianships: verified guardian-child relationships and permissions.

## 3. Workspace domain
- workspaces: independent coaching businesses and academies.
- workspace_memberships: users and workspace-specific roles.
- workspace_children: authorized workspace-child relationships.

## 4. Connection domain
- connection_requests: coach-initiated invitations and guardian-initiated requests.
- Request states: pending, approved, rejected, expired, cancelled.
- The initiating party expresses intent.
- The receiving party confirms.
- Expired or rejected requests cannot activate connections.
- Connection does not automatically create a class enrollment.
- Invitations and QR codes never grant direct access without validation.

## 5. Classes domain
- batches: recurring class groups.
- batch_coaches: coach assignments.
- enrollments: children registered in batches.
- class_sessions: individual scheduled occurrences.
- attendance: attendance per session and enrollment.

## 6. Communication and safety domain
- class_updates: class diary entries.
- update_recipients: authorized recipients of updates.
- media_assets: private media references and visibility metadata.
- consent_records: purpose-specific permissions and withdrawals.
- audit_events: security-relevant activity history.

## 7. Security principles
- Workspace isolation is mandatory.
- No unrestricted child or guardian directory.
- No automatic child matching using names or phone numbers.
- Coaches access only authorized classes and children.
- Guardians access only authorized child information.
- Media remains private by default.
- Sensitive linking operations require trusted backend validation.
- RLS policies and negative security tests are required before real data.

## 8. Data integrity rules
- Use UUID primary keys.
- Use foreign keys for relationships.
- Prevent duplicate active memberships, connections and enrollments.
- Attendance must reference valid sessions and enrollments.
- Record important approval and revocation events.

## 9. Pending design decisions
- Authentication methods and account recovery.
- Guardian verification and dispute resolution.
- Invitation expiry and rate limits.
- Consent purposes and retention requirements.
- Detailed table columns, indexes and SQL constraints.
- RLS policy implementation and security tests.

## 10. Implementation status
Design only. No Supabase project, migrations or database tables created.

## 11. Courses and learning delivery
- subjects: learning domains such as art, music or mathematics.
- courses: workspace offerings, including age range, level, duration and status.
- course_lessons: planned curriculum units.
- batches: scheduled delivery groups linked to courses.
- batch_coaches: assigned instructors.
- class_sessions: individual class occurrences.
- session_coaches: actual instructors for individual sessions.
- session_lessons: lessons delivered during sessions.
- enrollments: child participation in batches.

## 12. Persistent relationships
- workspace_children stores the historical child-workspace relationship.
- Enrollment completion does not automatically remove that relationship.
- Relationship lifecycle and enrollment lifecycle are independent.
- Alumni access is restricted by authorization and retention policies.
- Marketing permissions are separate from historical operational access.

## 13. Historical learning records
- learning_records: progress observations, skills, milestones and achievements.
- Learning records reference the child, workspace and relevant learning context.
- Authorized guardians can access permitted historical records after enrollment.
- Historical records remain subject to privacy, consent and retention rules.
- Advanced analytics and data export are deferred from the initial MVP.

## 14. Public discovery boundary
- Parents may discover published coaches, academies and course offerings.
- Private child records and student rosters are never publicly searchable.
- Public discovery and private operational access use separate authorization rules.
- Full discovery and marketing functionality may be implemented later.

## 15. Outstanding design work
- Define course pricing, duration and scheduling fields.
- Define post-enrollment academy access permissions.
- Define historical media retention and deletion rules.
- Define learning-record visibility and correction policies.
- Review privacy requirements before storing real children's information.

## 16. Relationship and enrollment lifecycle

### Workspace-child relationship
- active: child currently has an authorized operational relationship.
- alumni: child previously attended; historical relationship retained.
- restricted: relationship exists but access is limited or disputed.
- archived: operational relationship is no longer active.
- Revocation of access must not be treated as deletion of all history.

### Enrollment
- pending: registration initiated.
- active: child is participating.
- completed: course or batch successfully finished.
- withdrawn: child left before completion.
- cancelled: enrollment cancelled before participation.

### Access after enrollment
- Guardians retain access to permitted historical learning records.
- Academy staff retain only authorized historical operational access.
- Former enrollment does not grant access to new child information.
- Media remains subject to consent, visibility and retention rules.
- Marketing permissions are independent of enrollment history.

### Implementation rules
- Do not cascade-delete learning history when enrollment ends.
- Record status transitions with timestamps and responsible actor.
- Use explicit authorization checks for historical records.
- Define retention, deletion and dispute policies before real-data use.

## 17. Account lifecycle and deletion architecture

Status: Confirmed architecture; retention and deletion procedures pending privacy review

### Separate lifecycle operations
- Account deactivation: disable account access.
- Membership removal: revoke workspace-specific permissions.
- Ownership transfer: assign responsibility to another authorized user.
- Account deletion: process identity and personal-data removal.
- Historical retention: preserve only records with a valid retention basis.

### Database requirements
- Do not cascade-delete operational history when membership ends.
- Require safe ownership transfer before deleting an Owner.
- Keep historical access separate from active enrollment permissions.
- Track account and membership lifecycle events.
- Define deletion and anonymization behavior before production use.

### Open decisions
- Retention periods for attendance, learning updates and media.
- Guardian disputes and deletion requests.
- Academy closure and historical record access.
- Legal and privacy requirements for children's information.

No SQL implementation approved yet.

## 18. Connection schema contract

Status: Proposed implementation of DEC-005, DEC-009, DEC-010 and DEC-013

### Connection requests
- Support workspace-initiated invitations and guardian-initiated requests.
- Initiator identity and receiving-party confirmation are separate.
- Request states: pending, approved, rejected, expired, cancelled.
- Skip does not change the pending state.
- A request cannot activate a connection after expiry or rejection.
- Invitation codes and QR codes identify a destination, not authorization.
- Invitations may exist before a guardian has a ParentPlus account.
- Existing child identity linking requires guardian authorization.
- No unrestricted parent, child or private roster directory.

### Workspace-child relationships
- Store one relationship per workspace-child pair.
- Relationship lifecycle is independent of class enrollment.
- Relationships may become active, alumni, restricted or archived.
- Historical relationships do not grant unrestricted access.
- Reconnection must follow explicit authorization rules.

### Connection events
- Record initiating actor, confirming actor and relevant timestamps.
- Record approval, rejection, cancellation and revocation events.
- Preserve an auditable relationship history.
- Do not store invitation secrets in plaintext.

### Authorization boundaries
- Only authorized workspace staff may initiate workspace invitations.
- Only an authorized guardian may confirm child linking.
- Guardian confirmation is a self-declaration in MVP.
- Formal legal guardian verification remains deferred.
- Connection approval does not automatically grant access to sensitive records.
- Connection approval does not create enrollment.

### Open implementation details
- Invitation expiry duration and rate limits.
- Secure token generation, hashing and redemption.
- Unregistered-parent invitation flow.
- Guardian disputes and multiple-guardian approval.
- Reconnection after relationship restriction or revocation.
- Exact RLS policies and post-enrollment access rules.

No SQL implementation approved yet.

## 19. Connection initiation and authorization contract

Status: Proposed implementation of confirmed ParentPlus V1 decisions

### Guardian-initiated request
- Caller must be authenticated.
- Caller must have an authorized guardian-child relationship.
- Destination workspace must be identified through an allowed discovery or code flow.
- Request starts as pending.
- Authorized workspace staff confirms or rejects.
- Guardian initiation does not grant workspace access automatically.

### Workspace-initiated invitation
- Caller must be an active, authorized workspace staff member.
- Invitation may exist before the guardian has registered.
- Invitation redemption requires authenticated guardian participation.
- Guardian selects or creates the child identity under authorized rules.
- Confirm records MVP guardian self-declaration.
- Skip leaves the request pending.
- Reject declines the request.
- Invitation possession alone grants no child-data access.

### Approval authorization
- Only the receiving party may approve.
- Initiator cannot approve their own request.
- Expired, rejected and cancelled requests cannot activate connections.
- Approval must resolve a valid child and guardian.
- Approval and relationship creation must be atomic.
- Approval must record an audit event.
- Duplicate approval must not create duplicate relationships.
- Enrollment is not created automatically.

### Privacy boundaries
- No unrestricted child, guardian or private roster directory.
- No automatic child matching by name or phone.
- Formal guardian verification remains deferred.
- Sensitive data access requires separate authorization.
- Historical relationship access follows DEC-015 through DEC-017.

### Implementation dependencies
- Secure invitation token and redemption design.
- Request expiry and rate limits.
- Controlled initiation and approval functions.
- Effective privilege and RLS review.
- Negative authorization and concurrency tests.

No SQL functions approved yet.

## 20. Guardian connection eligibility

Status: Proposed MVP implementation of DEC-012 and DEC-013

### Eligible guardian relationships
- Provisional, self-declared guardians may initiate connection requests.
- Active guardians may initiate and confirm connection requests.
- Provisional guardians may confirm invitations through an explicit self-declaration.
- Revoked guardians cannot initiate or confirm new connections.
- Disputed guardians cannot initiate or confirm new connections.

### Authorization safeguards
- The authenticated caller must match the guardianship user ID.
- The guardianship must reference the requested child.
- A child ID alone never establishes guardian authorization.
- Guardian self-declaration is not formal legal verification.
- Connection approval does not automatically grant sensitive academy-data access.
- Sensitive operations require separate authorization checks.
- Record confirmation actor, request and timestamp.

### Deferred decisions
- Formal legal guardian verification workflow.
- Multi-guardian approval requirements.
- Guardian dispute resolution.
- Verification evidence and document retention.
- Detailed post-connection data-access policies.

No SQL authorization functions approved yet.

## 21. Pending connection uniqueness

Status: Proposed implementation rule

### Guardian-initiated requests
- Only one pending request is allowed per guardian, child and workspace.
- Repeated submissions using the same request ID are idempotent.
- A new request ID must not create another pending request for the same relationship.
- An existing valid pending request may be returned to the initiating guardian.
- Expired pending requests must be transitioned before replacement.
- Terminal requests remain in history for audit purposes.

### Database enforcement
- Use a partial unique index for pending guardian-initiated requests.
- Do not use now() inside a partial index predicate.
- Handle expiry through a controlled transactional operation.
- Concurrent requests must not create duplicate pending relationships.
- Different guardians may require separate requests and authorization.

### Relationship safeguards
- An active workspace-child relationship must not be duplicated.
- Existing relationships require explicit reconnection rules.
- A pending request never grants academy access.
- Connection approval and enrollment remain separate.

Implementation status:
Design only. Database constraint and initiation function pending.
