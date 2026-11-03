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

## Local-only course, batch and assignment foundation

The draft migration creates workspace-owned course and batch records and explicit batch-to-membership assignments with composite foreign keys. Application roles receive no table access, and row-level security has no application policies. A same-workspace membership reference alone does not prove an active coach role: future trusted operations must verify actor, workspace, membership status and assignment at execution time, including revocation races, before granting access. No course creation, schedule operations, visibility, enrollment or session journey is exposed by this slice. Migration and authorization changes require independent security review before any hosted use.

## Private authorization building block

A private, owner-invoked database helper may check the authenticated actor against an active workspace, active membership and batch. Owners and admins may manage any batch in that workspace; coaches require an explicit assignment. Lock the workspace, membership, batch and assignment rows until the caller's transaction ends. Deny missing identity, invalid references, inactive status and unassigned coaches uniformly. The helper grants no app-role execution, exposes no data and must only be invoked inside a trusted mutation transaction; it is not a permission token and must never be used as a check before a separate transaction. Deterministic revocation-race tests and independently reviewed actual write operations remain required before release.

## Private single-occurrence write foundation

A private invoker-rights operation may create one session using explicit UTC instants and a caller-supplied request UUID. It must call the authorization helper and write in the same transaction. Restrict duration to positive whole minutes up to 1440 minutes as a technical guard; reject non-finite timestamps. The actor/request pair uniquely identifies a retry, and reuse with changed workspace, batch or time must fail. Application roles cannot call this operation or access its table. UTC inputs alone do not enforce the founder's workspace-time-zone and daylight-saving decisions; a server-authoritative time-zone contract, races on the actual operation, recurrence, user journey and independent review are required before exposure.

## Private workspace-local time validation

A private server-side local-time operation derives the zone from the locked workspace, never from the caller, and calls the private UTC session write in the same transaction. It requires a configured PostgreSQL-recognized named zone, minute-precision local time, a positive whole-minute duration up to 1440 and a technical date range of 2000–2100. It rejects nonexistent and ambiguous local times instead of guessing; user-facing resolution remains unimplemented. Test exact UTC outcomes and gaps/overlaps, including half-hour transitions. This local-only implementation uses bounded candidate search and requires performance, timezone database compatibility and independent security review before exposure. A private initial zone configuration operation exists in the local draft; app-facing configuration is not implemented.

## Private initial workspace zone configuration

As a conservative implementation boundary, a private operation allows an active owner or admin to set a recognized workspace time zone once, or retry the identical setting. It denies coaches, anonymous/cross-workspace actors, inactive memberships and suspended workspaces, and does not allow changing an established zone until the impact on existing and recurring sessions has been designed. The operation is invoker-rights, inaccessible to app roles, locks the workspace then membership in the same order as session creation, and must be reviewed before exposure. This one-time restriction is an engineering safeguard, not a permanent product decision.

## India-first delivery priority and private course setup

The founder confirmed India-first delivery and requested proportionate attention to time-zone edge cases. Keep the existing workspace-time-zone safeguards, but prioritise functional classes, batches and sessions for Indian academies over additional international clock-change features. This is a delivery priority, not approval to remove existing protections.

Private, invoker-rights local operations may create courses and batches for active workspace owners/admins using the signed-in actor and an actor/request idempotency key. Check and lock the workspace and membership; reject cross-workspace courses, invalid names and changed retries. Coaches cannot use these initial operations. App roles receive no execute or table grants. Course/batch creation policy, visibility, coach assignment operations, duplicate races, integration and independent review remain to be completed before exposure.

## Private coach assignment

The local draft permits an active workspace owner/admin to assign an active coach membership to a batch in the same active workspace. The actor comes from auth.uid(); workspace, actor, batch and target coach rows are locked within the transaction. Identical repeated assignments succeed without creating duplicates. Reject missing/cross-workspace/inactive/non-coach targets and unauthorized actors. No application role can execute the operation or access the table. Assignment removal, audit, real application integration and independent security review remain open.
