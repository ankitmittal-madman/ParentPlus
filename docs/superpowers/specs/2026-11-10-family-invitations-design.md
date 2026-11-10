# Academy family invitations — M2-02 first slice

## Product intent and scope

Continue the founder-authorised next development steps against the supplied
pilot kit and coach design. Deliver an actual browser → Supabase → browser
academy connection: owner/admin creates a single-use invitation, a signed-in
parent selects their own existing child and explicitly confirms, and Students
shows that saved connection after reload. Parents without a profile use the
existing real child-creation flow first. Dummy founder OTP remains unchanged.

This is the first slice of S2-04/M2-02 and M2-49, not completion of either feature.
Second guardians, batch enrolment/filtering, attendance, contact, fees and full
child snapshots remain future. A connection is not enrolment or legal guardian
verification. No automatic identity matching by name/phone. No auto-created child.

## Approach and reconciliation

Builder choice under the founder's instruction to make routine decisions:
reuse workspaces, guardianships and workspace_children, adding one private invite
table and narrow authenticated RPCs. Replacing the schema with the old kit's
organisation tables would lose current work; re-enabling legacy connection
functions would bypass their explicit access revocation. Neither is appropriate.
Use current shared UI colours/rounded cards and Students/Add a student semantics
from ParentPlus_Coach_Tutor_App.html; never copy fake attendance/fee values.
All new interface copy comes from EN/HI messages with a local language selector.

## Contract and boundaries

- Owner/admin of an active academy can issue an invite. A normal coach cannot
  manage academy-wide admission until batch-scoped admission is designed.
- Browser generates 32 random bytes (64 lowercase hex) and a request UUID;
  the database stores only SHA-256 digest. Same actor/workspace/request/hash
  returns the existing invitation; changed payload or actor is refused.
- Invite expires after 14 days, uses database wall time after locks, single-use.
  A valid signed-in recipient sees only academy name/expiry/status before consent.
  No anonymous metadata lookup and no child/guardian details in the link.
- Parent must have an eligible provisional/active guardianship AND have created
  the selected child, matching the current first-use profile list. Confirmation
  creates one active academy-child relationship and one approved request/event,
  atomically. It never changes guardian verification or creates enrolment.
- A retry by the same parent for the same child returns the original relationship
  while eligibility/access remains valid. Another actor/child is refused. Expired
  unused invites, suspended academy/issuer, revoked guardianship and restricted
  existing relationships fail closed. Never reactivate a restricted relationship.
- Lock invite, workspace/issuer membership, guardianship and relationship writes;
  serialize same academy/child so two different invitations cannot duplicate it.
  Direct table access remains denied/RLS on. Legacy RPC grants remain revoked.
- Manager roster returns bounded pages ordered by relationship UUID with cursor;
  child display name + relationship state only, no parent contact or invented stats.
- Parent can read the academy connections for their own created eligible child.
- Link uses `/join#<token>` so token stays out of server URL/access logs. Browser
  strips fragment immediately, retains it in memory only and clears on unmount.
  User can reopen the original shared link after reload/sign-in. Never persist
  token to localStorage or include in reports/screenshots. No automatic redirect.
- Invite issuance and confirmation are explicit user actions. Unknown responses
  preserve the same in-memory token/request or chosen child for safe retry;
  reloading may require reopening the link. Error text gives honest recovery.
- UI clears sensitive state on auth event/focus return and ignores late responses;
  signed server identity and expected actor are rechecked on each write.

## Acceptance and verification

SQL: valid lifecycle/retry, changed-payload/other-actor rejection, wrong child,
expiry, suspension/revocation, restricted relationship, denied direct/anonymous
access, scoped paginated roster and parent connections; real transaction races.
Frontend: validation/error redaction, DB output validation, expected actor,
loading/double click, token/privacy handling, locale, late auth response handling.
Real local Supabase browser: coach issue → separate parent dummy sign-in → create
child → accept → reopen/retry → roster persists after reload and parent can see
academy; fake token refused. Screenshots and scenario registry/report extended.
Run full selected quality suites and independent review before authorised Git
publication. Hosted testing migration must preserve records; no resets/new accounts.
