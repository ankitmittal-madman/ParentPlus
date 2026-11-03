# Real scheduling — draft architecture and test matrix

Status: **design in progress; no real scheduling implementation or approval to deploy**.

## Confirmed product requirements

Per DEC-014 and DEC-018, courses, batches and sessions are separate concepts. Workspace owners, admins and authorised coaches may create and edit sessions; both one-off and recurring weekly sessions are required. A schedule does not itself grant access to children, enroll them or grant cross-workspace visibility.

## Security-oriented candidate architecture

Workspace-owned courses and batches, explicit coach assignment, a recurrence series and individual session occurrences are candidates for a local database design. Composite workspace keys should prevent cross-workspace references. Writes should derive the actor from verified server identity, check active workspace and membership plus the approved coach-authorisation rule, and use narrow operations with replay/duplicate and concurrent-revocation protection. Read policies must enforce the separately defined visibility rules. No child data should be stored in a schedule merely to support this feature.

## Confirmed detailed choices and remaining design

DEC-019 confirms assigned-batch coach access, a choice between one occurrence and future occurrences when editing, and use of the workspace time zone with user resolution of daylight-saving gaps and overlaps. The precise data model, schedule visibility, overlap policy, recurrence bounds, deletion/cancellation and retention require design as implementation proceeds. Do not treat these decisions as deployed behavior.

## Minimum verification matrix

| Area | Required scenarios |
| --- | --- |
| Identity and tenancy | Anonymous, cross-workspace, invited, removed and suspended actors; suspended workspace; cross-workspace references |
| Permission | Owner/admin, authorised coach and unauthorised coach; direct table privilege and role-escalation attempts |
| Data correctness | One-off and weekly creation, valid/invalid dates, bounds, duplicate or replayed requests, same request with changed payload |
| Time | IANA zones, daylight-saving gaps and overlaps, offset changes, duration and chosen time-zone policy |
| Concurrency | Duplicate creation, conflicting edits, assignment/membership/workspace revocation versus write in both orderings, occurrence uniqueness |
| UI and integration | Accessible create/edit flow, success and failure states, frontend/backend agreement, browser journey and session expiry |
| Operations | Synthetic fixtures only, rollback/cleanup, migration reconstruction, evidence and independent security review |

The existing schedule preview has no persistent database behavior. Product release remains blocked until the decisions, implementation, required tests and actual provider/hosted verification are complete.
