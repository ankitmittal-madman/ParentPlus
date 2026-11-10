# Batch enrolment and student directory

## Intent

Continue the founder-authorised app development loop. References define features;
Codex owns engineering choices. Preserve the Coach/Tutor prototype's mobile list,
batch chips, rounded cards, muted background and teal primary actions. Use real
Supabase, existing dummy sign-in and existing testing backend. No new accounts,
paid services or data resets. Current clean baseline9245349.

Deliver: manager selects an academy/batch and connected child, explicitly enrols;
Students filters saved enrolments by batch, pauses/resumes/completes/withdraws an
enrolment with safe recovery; permitted parent sees saved class and status.
Academy connection never auto-enrols. This supports S2-06/S2-07 and M2-49.

## Engineering decisions

Reuse workspaces/courses/batches/workspace_children/guardianships. Add enrolments,
request receipts and events as private RLS tables with controlled authenticated
RPCs. Preserve pending/active/completed/withdrawn/cancelled states and ADD paused
for the reference's reversible temporary break; never mislabel pause as withdrawal.
Initial enrolment is active; active↔paused and active/paused→completed/withdrawn.
Terminal states cannot reopen through retry. One enrolment per child/batch in this
slice; re-entry into a terminal enrolment requires a future explicit flow.

Admissions/status changes are owner/admin operations, matching existing Students
management. Assigned coaches may read only their assigned batch's roster and
batch metadata; attendance work will use these reads. Parent reads require own
created child + current eligible guardianship + active academy connection and
workspace. No new legal/media/pickup/fee permissions are implied.

Each write uses a browser-memory request UUID bound to actor and entire payload.
Status transitions include expected integer version; concurrent stale edits fail.
Same request retry returns the original result receipt after rechecking current
access. UI treats this as an operation result then explicitly refreshes the roster;
it must not overwrite current state with an old receipt. On unknown response keep
actor/target/status/version/request fixed; disable changes until retry/reconciliation.
No free-form personal notes: pause/withdraw reason is a required enum
`temporary_break|schedule_change|other`; resume/complete use null reason.

## RPC contracts (migration052)

All app RPCs derive auth.uid, validate current workspace/batch/relationship and
lock permissions against concurrent revocation; direct table/private helper and
anonymous execution remain denied. All creation/grant work in one transaction.
Names below use enrollment spelling to match existing architecture.

- app_enrollment_batches(p_workspace_id uuid): TABLE(batch_id uuid,batch_name text,
  course_name text). Owners/admins all; assigned active coach only assigned batches.
- app_enrollment_candidates(p_workspace_id uuid,p_after uuid DEFAULT NULL):
  TABLE(child_id uuid,child_name text). Manager only; active connections,50/page UUID order.
- app_batch_enrollments(p_workspace_id uuid,p_batch_id uuid,p_after uuid DEFAULT NULL):
  TABLE(enrollment_id uuid,child_id uuid,child_name text,status text,version integer).
  Manager or assigned coach; active connection;50/page by enrollment UUID.
- app_save_enrollment(p_workspace_id uuid,p_batch_id uuid,p_child_id uuid,p_request_id uuid):
  TABLE(enrollment_id uuid,status text,version integer). Manager, active connection.
  Matching natural key already active returns it without duplicate event; terminal
  or paused conflict fails rather than silently resuming. One payload-bound receipt.
- app_change_enrollment(p_enrollment_id uuid,p_status text,p_expected_version integer,
  p_reason text,p_request_id uuid): TABLE(enrollment_id uuid,status text,version integer).
  Manager; guarded transition and optimistic version; receipt/event atomic.
- app_parent_enrollments(p_child_id uuid): TABLE(enrollment_id uuid,academy_name text,
  batch_name text,course_name text,status text,version integer). Own eligible child,
  active connection/workspace; bounded100. No reasons/contacts exposed.

## Frontend contracts

`src/modules/enrollments/contracts.ts`: EnrollmentState union (six states),
Batch{id,name,courseName}, Candidate{id,name}, Enrollment{id,childId,childName,status,version},
SavedEnrollment{id,status,version}, ParentEnrollment{id,academyName,batchName,courseName,status,version}.
`src/lib/enrollments/actions.ts`: listEnrollmentBatches(actor,workspace),
listEnrollmentCandidates(actor,workspace,after), listBatchEnrollments(actor,workspace,batch,after),
saveEnrollment(actor,{workspaceId,batchId,childId,requestId}),
changeEnrollment(actor,{enrollmentId,status,expectedVersion,reason,requestId}),
listParentEnrollments(actor,child). Return existing Result<T> union; verify server
user and expected actor before RPC; validate/project all returned rows and errors.
Use no admin/service-role client for product writes.

UI: separate EnrollmentPanel on Students, preserving invitation panel. EN/HI new
copy under messages files (enrollments section) and remembered choice. Parent
classes panel on profiles page. Use session boundary invalidation, clearing stale
private reads on auth/focus and ignoring late promises. Write uncertainty retains
same payload/request; account change discards view and requires original account
for retry, never silently regenerates a mutation. Existing invites still usable.

## Acceptance

TDD for SQL/action/component paths. Real local browser: two accounts, academy/class,
invitation→connection→explicit enrolment→parent sees class after reload; pause,
resume and withdrawal; repeat request no duplicate. Negative: cross-workspace,
anonymous/parent/coach write, revoked role/connection/guardian, bad state/version,
request collision, rollback, two concurrent enrolments and both revocation orders.
Pagination >50. Extend scenario catalogue/HTML/Excel screenshots as work proceeds.
Independent review and full quality gate before publication. Preserve all prior
work/stash; existing commit/push/merge/testing-deploy authorisation persists.

## UI integration details for stable user journeys

Students retains its existing h1/invite controls and adds a clearly labelled
`Batch enrolment` region. Automatically verify the session and load eligible academies, then default to the
only/first eligible academy and batch with scoped reads. Allow labelled
`Academy for enrolment` selection when needed, and present batch selection as
prototype chips with saved batch names. Connected child options load on academy
selection; labelled `Connected child`, then explicit `Enrol child`. Provide
`Refresh enrolments` and a focused retry state after read errors; avoid making
ordinary app navigation a sequence of developer-style Load buttons. A saved roster shows real
child names/status and `Pause enrolment`, `Resume enrolment`, `Complete enrolment`,
`Withdraw enrolment` actions only when valid, with `Reason` choice where required.
A clear refresh/check-status action reconciles unknown replies without generating
new request IDs. Pagination controls are reachable and bounded.

Parent profiles get a `Child classes` region: automatically load own eligible
children and default to the first, labelled `Child for classes`; refresh or select
a child to show saved academy/course/batch/status. Provide `Refresh classes` and
an honest empty/error state. Auto-loading reads must clear old data and verify
current server identity on session/focus changes; mutations stay explicit.
New feature language selector uses `Enrolment language / नामांकन की भाषा` to avoid
ambiguous duplicate labels beside existing family controls. EN/HI keys under
`enrollments`; preserve existing `families` keys. Read installed Next docs before
integration. Root will extend headless scenarios against the actual resulting UI.

## Review clarification: definitive conflict recovery

Ordinary read Result<T> remains unchanged. Mutation results may additionally
return the fixed redacted discriminator `{ok:false,conflict:true}` for allowlisted
DB rejection codes (40001 stale version,23505 saved-state/request conflict). Never
expose provider error text. A conflict result is not a new write or permission:
revalidate the actor/current readable roster, release that rejected intent, and
allow an explicit next action using the displayed current version. Do not auto-
rebase/reissue. Transport exceptions, malformed success/output and other unconfirmed
errors retain original UUID/payload as uncertain. Keep account-mismatch/privacy
and committed-write/lost-reply guarantees. This small typed distinction is needed
for a usable concurrent management flow without changing any SQL RPC signature.
