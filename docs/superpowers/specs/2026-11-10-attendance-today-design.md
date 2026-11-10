# Attendance, parent signals and real Today

Status: planned at creation, 10 November 2026. Enrolment052 is verified in code
8f0ae0e, documentation17ca3dc and the existing TEST backend. This dependent053
feature is not implemented or tested at design creation. Current evidence belongs
to Quality Evidence; design statements alone are not runtime or deployment proof.

## Outcome and source reconciliation

A manager or assigned coach opens Today, selects an academy/date, opens a real
session, explicitly marks its enrolled children and saves one atomic sheet. The
eligible parent opens `/parent`, sees that child's saved attendance and can send a
session-specific quick signal. Data comes from the existing database, including
the sessions created by weekly class setup. Keep testing email/123456 sign-in.

Sources: founder PRD sections 3–5; parent-items contract envelope/fallback/v1;
Module2 HTML M2-06/09/10/11/41/58; Coach/Tutor HTML `today()`, `live()`, `allp`,
`leave`, `endclass`; actual migrations014/015/049/051/052 and current app callers.

Engineering rulings, requiring explicit recording when this draft is integrated:

| Conflict or missing contract | Decision for this slice |
| --- | --- |
| Founder model calls tables organizations/classes/class_sessions/attendance | Keep workspaces/batches/schedule_sessions and introduce attendance_sheets/attendance_records. `class_id` in the parent envelope aliases batch_id; never create a duplicate classes model. |
| M2-06 premarks absence and M2-10 auto-confirms after class | Signals remain labelled parent reports. Suggested absence requires an explicit review action, then explicit Save. No timed confirmation, location, QR, media-derived presence or confidence engine. |
| Prototype `leave` and `endclass` announce saved attendance in memory | Save attendance calls the atomic RPC. Do not expose End class and post until posting actually works. No capture buttons, fake posted status or invented fees/engagement/attendance percentages. |
| Founder item contract says every guardian; current051/052 parent contracts require child creator plus eligible guardianship | Preserve creator + provisional/active guardian access for this slice. Do not silently admit another guardian. Record multi-guardian distribution as unfinished M2-02/M2-58 scope. Verification level is not upgraded. |
| Existing academy selectors are manager-only; Today must support coaches | Add a dedicated bounded Today academy RPC supporting active owner/admin/coach. Assigned coaches see only their assigned batches. Do not reuse manager-only `familyAcademies` or class-setup lookup. |
| M2-06 names Supabase Realtime, but private tables have no subscription policy | Visible-tab polling every15seconds, plus refresh/focus, through bounded authenticated RPCs. Show the last successful refresh time; no realtime claim. |
| Parent count/week wording has no denominator policy | Show factual saved attendance rows and “Attended this week”, counting present/late/make_up. No percentage, billing deduction, scheduled-session denominator or inference from signals. |
| Schedule has no cancellation/version fields | Add forward-only lifecycle columns/guard in053; retain old history. No cancellation/edit UI in this slice. Future schedule writes must share the batch mutex. |

This is a complete usable attendance/signals/feed journey, not completion of all
M2-41 aggregation, M2-58 item types, handover safety, diary or launch readiness.
Preserve original founder files and existing profile, invite and class-recovery
entrypoints. No new services, accounts, dependencies, worktrees or paid products.

## Scope, states and limits

- Attendance states: `present`, `late`, `absent`, `excused`, `make_up`.
- Client-only `unmarked` is null; it is never persisted. No row becomes present
  merely because a screen opens. P/L/A are primary buttons; More exposes
  Excused/Make-up. Each control has child-specific accessible names.
- Signals: `running_late`, `missing_today`, `dropped_off`, `picked_up`.
  Missing reason is required and one of `unwell`, `travelling`, `other`; other
  signal types require reason=null. No free text/medical details or pickup names.
  UI labels every drop/pick signal “Parent report”; it is neither verified
  handover nor authority to release a child. Keep M2-11 separate.
- Session lifecycle: `scheduled` or `cancelled`; positive int32 version starts1.
- Bounded responses: academy/session/feed/signal pages50, with explicit next
  cursor. Atomic session roster supports at most200 active enrolments before
  connection filtering. Read at most201 candidates; if the201st exists, return `roster_too_large` with
  no partial editable roster or fabricated total. Zero roster is a real empty
  state; do not create an empty saved sheet. This is an explicit first-slice
  operational limit, not a hidden truncation or change to enrolment admission.
- Dates are ISO local dates in the academy's configured IANA zone. A session
  belongs to the date of starts_at; a cross-midnight session appears once. Do not
  use browser zone to silently configure an academy. Null/invalid zone means
  unavailable, with link to existing class setup for a manager.

## Ownership and migration053

Create `supabase/migrations/20261110005300_attendance_today.sql` after the verified052 source checkpoint. One transaction creates private objects and changes
ACLs. Never edit014–052, backfill invented attendance or rewrite existing users,
children, connections, enrolments, schedules or receipts. Validate on fresh053
and existing052 upgrades, preserving original row fingerprints; only session
columns get their declared defaults. Migration failure must leave052 intact.

All new tables have RLS enabled and ALL revoked from PUBLIC/anon/authenticated.
No client direct-table policy, broad service-role browser client or anonymous
RPC. Trusted owner runs SECURITY DEFINER public app RPCs with search_path=''.
Helpers are invoker functions, fully qualified, with no application execution
grants; create/revoke/grant commit atomically. Retain existing control defaults.

| Table / owner | Required keys, contents and constraints |
| --- | --- |
| schedule_sessions / scheduling | Add status text default scheduled/check, version int default1/check>0, updated_at timestamptz default clock_timestamp(). Add unique(workspace_id,batch_id,id). BEFORE UPDATE guard owns version: increment for actual starts_at/ends_at/status change; otherwise retain old version. Do not let callers manually reset or advance it. Reject workspace_id/batch_id changes. Existing insert functions keep working with defaults. |
| enrollments / enrolment | Add unique(workspace_id,batch_id,child_id,id) forward in053 solely for composite reference integrity. Keep052 statuses/functions unchanged. |
| attendance_sheets / attendance | session_id PK; workspace_id,batch_id; version positive int32; session_version positive int32; roster_token 64 lowercase hex; roster_size1..200; saved_by auth.users FK; saved_at timestamptz. Composite FK to schedule_sessions; unique(workspace_id,batch_id,session_id). No sheet exists before first save; read version0 then. |
| attendance_records / attendance | PK(session_id,enrollment_id), unique(session_id,child_id), unique(workspace_id,batch_id,session_id,enrollment_id,child_id); workspace_id,batch_id,child_id,enrollment_id; status check; sheet_version>0; source='coach_confirmed'; confirmed_by auth.users FK; confirmed_at timestamptz. Composite FK to sheet and to matching enrollment workspace/batch/child/id. Preserve records omitted by later rosters; they are historical records, not members of the latest active sheet. |
| attendance_record_events / attendance audit | id UUID PK; same scoped session/enrollment/child keys and status; from_status nullable; sheet_version; actor_id; created_at. Composite record FK; unique(session_id,enrollment_id,sheet_version). One event for each explicitly confirmed row per save, including reaffirmations. No notes. No update/delete RPC. |
| attendance_request_receipts / attendance recovery | request_id UUID PK; actor_id; canonical_payload JSONB object; workspace_id,batch_id,session_id; result_version,result_session_version,result_roster_token,result_saved_at,result_record_count. Composite FK to sheet. Full payload retained, not only a digest. One immutable row per successful request, no failure receipts. |
| parent_signals / signals | id UUID PK, unique(workspace_id,batch_id,session_id,child_id,id); workspace_id,batch_id,session_id,enrollment_id,child_id,actor_id; type/reason checks above; created_at clock_timestamp(). Composite FK to session and enrollment. Append-only per successful send; never upsert another actor's report. Signal history itself is the audit event. |
| parent_signal_request_receipts / signals recovery | request_id UUID PK; actor_id; canonical_payload JSONB object; signal_id unique FK; workspace_id,batch_id,session_id,child_id; result_created_at. Scoped FKs to the signal's unique(workspace_id,batch_id,session_id,child_id,id). Full normalized payload retained. |
| parent_items / parent feed | id UUID PK; workspace_id,batch_id,child_id,enrollment_id; source_session_id; type text nonempty<=80; schema_version positive int; priority smallint default0/check0..100; created_at,updated_at; expires_at nullable; payload JSONB object <=16KiB; audience_policy='child_guardian'. Composite session and enrollment FKs; unique(workspace_id,child_id,type,source_session_id). Only attendance writer in this migration. |

The parent-item id/created_at remain stable on correction; update its payload and
updated_at in the attendance transaction. This creates one parcel per child and
session, not one duplicate per save or one row per guardian. Authorised reads are
the fanout. No outbox/push delivery is implied. Separate immutable record events
preserve corrections. Future sensitive item writers need their own policy and
validation; `audience_policy=child_guardian` is not permission to include media,
private notes, fees or contacts in arbitrary payloads.

Indexes: schedule_sessions(workspace_id,starts_at,id),
schedule_sessions(workspace_id,batch_id,starts_at,id);
enrollments(workspace_id,batch_id,id) partial status='active';
records(child_id,confirmed_at DESC,session_id);
events(session_id,sheet_version,enrollment_id);
signals(session_id,child_id,actor_id,created_at DESC,id DESC);
items(child_id,created_at DESC,id DESC). Existing guardian/relationship/member
indexes remain usable. Verify query plans with synthetic multi-academy fixtures.

## Exact public RPC surface

All RPCs below return a single JSONB object, never an ambiguous set of rows. UUIDs
are lower-case strings, times UTC ISO timestamps, date YYYY-MM-DD, integers JSON
numbers. Every key described is required; nullable values are explicit null.
Unknown extra response keys may be ignored, but malformed required fields,
duplicates, invalid cursor or a response exceeding its bound fail closed.

```text
app_today_academies(p_after uuid DEFAULT NULL) RETURNS jsonb
  {academies:[{workspace_id,name,time_zone:null|string}],next_after:null|uuid}
app_today_sessions(p_workspace_id uuid,p_date date,
                   p_after_start timestamptz DEFAULT NULL,p_after_id uuid DEFAULT NULL) RETURNS jsonb
  {date,time_zone,server_now,sessions:[Session],next:null|{starts_at,id}}
  Session={id,batch_id,batch_name,course_name,starts_at,ends_at,status,version,
           sheet_version,roster_size:null|integer,roster_too_large:boolean,
           marked_count:integer,attendance_current:boolean}
app_attendance_sheet(p_workspace_id uuid,p_session_id uuid) RETURNS jsonb
  {session:Session,time_zone,server_now,sheet_version,saved_at:null|timestamp,
   saved_roster_token:null|hex64,roster_token:null|hex64,
   roster_too_large:boolean,rows:[RosterRow]}
  RosterRow={enrollment_id,enrollment_version,child_id,child_name,
             status:null|AttendanceStatus,confirmed_at:null|timestamp}
app_save_attendance(p_workspace_id uuid,p_session_id uuid,
                    p_expected_session_version integer,p_expected_sheet_version integer,
                    p_roster_token text,p_records jsonb,p_request_id uuid) RETURNS jsonb
  {request_id,session_id,sheet_version,session_version,roster_token,saved_at,record_count}
app_attendance_request_status(p_workspace_id uuid,p_session_id uuid,
                              p_request_id uuid,p_payload jsonb) RETURNS jsonb
  {state:'unknown',receipt:null} OR {state:'known',receipt:AttendanceReceipt}
app_session_parent_signals(p_workspace_id uuid,p_session_id uuid,
                           p_after_child uuid DEFAULT NULL,p_after_actor uuid DEFAULT NULL) RETURNS jsonb
  {signals:[Signal],next:null|{child_id,actor_id},server_now}
app_parent_academies(p_child_id uuid,p_after uuid DEFAULT NULL) RETURNS jsonb
  {academies:[{workspace_id,name,time_zone:null|string}],next_after:null|uuid}
app_parent_batches(p_child_id uuid,p_workspace_id uuid,p_after uuid DEFAULT NULL) RETURNS jsonb
  {batches:[{batch_id,batch_name,course_name,enrollment_id,enrollment_status}],next_after:null|uuid}
app_parent_sessions(p_child_id uuid,p_workspace_id uuid,p_date date,
                     p_batch_id uuid DEFAULT NULL,
                     p_after_start timestamptz DEFAULT NULL,p_after_id uuid DEFAULT NULL) RETURNS jsonb
  {date,time_zone,server_now,sessions:[ParentSession],next:null|{starts_at,id}}
  ParentSession={id,batch_id,batch_name,course_name,starts_at,ends_at,status,version,
    enrollment_id,enrollment_status,attendance:null|{status,confirmed_at},
    own_latest_signal:null|Signal,can_signal:boolean}
app_send_parent_signal(p_child_id uuid,p_workspace_id uuid,p_session_id uuid,
                       p_expected_session_version integer,p_type text,p_reason text,
                       p_request_id uuid) RETURNS jsonb
  {request_id,signal_id,session_id,child_id,type,reason,created_at}
app_parent_signal_request_status(p_child_id uuid,p_workspace_id uuid,p_session_id uuid,
                                 p_request_id uuid,p_payload jsonb) RETURNS jsonb
  {state:'unknown',receipt:null} OR {state:'known',receipt:SignalReceipt}
app_parent_items(p_child_id uuid,p_workspace_id uuid,
                  p_batch_id uuid DEFAULT NULL,
                  p_before_created timestamptz DEFAULT NULL,p_before_id uuid DEFAULT NULL) RETURNS jsonb
  {items:[ParentItemEnvelope],next:null|{created_at,id}}
app_parent_attendance_week(p_child_id uuid,p_workspace_id uuid,p_week_start date,
                           p_batch_id uuid DEFAULT NULL) RETURNS jsonb
  {week_start,time_zone,attended_count,recorded_count,
   rows:[{session_id,batch_id,batch_name,date,status,confirmed_at}],has_more:boolean}
```

`AttendanceReceipt` and `SignalReceipt` are exactly the respective write result.
`Signal={id,child_id,actor_id,type,reason,created_at}`. Actor UUID is provenance,
not a contact directory; display “Parent report” and time, never email/phone.
Only the coach endpoint returns other eligible actors' report IDs. The parent
sees their own signals only. Coach signals endpoint returns the latest report
per child/actor, ordered(child_id,actor_id), at most50, using DISTINCT ON backed
by the index. Filter current active roster/connection before selection. Latest
means greatest(created_at,id); session+actor+child writes are serialized. Keep
history private. Current creator-only scope yields at most one eligible parent
per child; preserve per-actor structure for a later reviewed guardian extension.

All cursor pairs must be both null or both present and finite/valid. Sessions
order ascending(starts_at,id), feed descending(created_at,id), use strict tuple
comparison and LIMIT51 to determine next. No offsets, client-provided limit,
whole-tenant dump or silent50-row truncation. Use date bounds `[local midnight,
next local midnight)` converted separately through the academy zone (not+24h).
Validate finite dates in2000-01-01..2100-12-31. Academies sorted UUID, LIMIT51.
The coach academy list may include an active coach with no assignments, producing
an honest empty Today; individual sessions always enforce assignments.
Parent academy pages sort workspace UUID; parent batch pages sort batch UUID,
both use LIMIT51/50 response and strict cursor comparison. A non-null optional
parent batch filter must match a retained enrolment for that own child in the
selected workspace, else42501. These dedicated reads are necessary:051
app_child_academies returns relationship IDs and052 app_parent_enrollments returns
enrolment IDs, neither returns the workspace/batch IDs needed for scoped navigation.

Session summaries inspect at most201 roster rows per session (50 sessions/page).
If oversized, roster_size=null and roster_too_large=true. Marked_count counts
matching current active roster records, never rows from a paused child.
attendance_current requires a sheet with matching session_version and current
roster_token; it does not mean a post was published. Unsaved sheet version0.
Do not claim a paginated partial session count as the academy's total.

Parent sessions use existing own-child eligible academy selection, join the
specific child's enrolments, and allow historical records for any retained
enrolment state while connection/workspace/guardian checks still hold. New signal
requires scheduled session, active enrolment and session's local date=today in
academy zone, rechecked after waits. Attendance has no extra time-window rule:
an authorised coach can explicitly confirm/correct any scheduled dated session.

Week start must be a Monday in the selected academy zone. Counts are exact
indexed aggregates of authorised saved records in that seven-local-day window;
attended_count counts present/late/make_up, recorded_count counts all five states.
Rows are capped50; has_more marks omitted detail, counts stay exact. This is a
bounded response, not a claim of constant-cost aggregate work. No lifetime count
or percentage scan is added. Signals never affect either count.

## Authorization and locking contract

Reject writes/status recovery outside READ COMMITTED (`25001`); advisory-lock
waits must not reuse an old transaction snapshot. auth.uid() is the actor, never
a supplied argument. All authorisation is database-owned; application getUser
matching is an extra session/account fence. No write result leaks raw SQL text.

Coach access: lock active workspace FOR SHARE, active actor membership FOR SHARE;
role owner/admin, or coach with matching batch assignment FOR SHARE. Parent:
lock active workspace, own created child, own provisional/active guardianship,
active workspace_children; relevant retained enrolment must exist. No suspended
workspace, revoked/disputed guardian or restricted/alumni/archived connection.
These checks apply independently of item type. History survives pause/withdrawal
but never overrides current access. A cached parent item grants no rights.

For new attendance save, do NOT call assert_schedule_write_access before the
batch lock: it takes batch SHARE and two concurrent saves could deadlock when
both upgrade to UPDATE. Implement a new private attendance guard that locks
workspace and membership, then acquires batch FOR UPDATE directly, then locks
coach assignment if needed; follow with session FOR SHARE, children sorted UUID,
connections sorted child UUID, enrolments sorted id, and sheet FOR UPDATE.
Session must match workspace/batch and scheduled/version. New saves lock all
current roster rows; compare exact canonical roster before any writes. Record,
event and item writes then run in enrollment-id order.

First enumerate up to201 active enrolments without a connection-status filter.
If at most200, lock the corresponding child and connection rows even when a
connection is currently inactive, then filter to active connections and compute
the token. Otherwise a concurrent restricted→active connection would be an
unlocked roster phantom. Both restriction and reactivation now serialize against
the same held connection locks;052's batch SHARE prevents enrolment-set changes.
The operational cap applies before this filtering so lock work is bounded; an
oversized active batch stays read-only even if many connections are restricted.

This batch UPDATE conflicts with052's batch SHARE, preventing admission/pause/
resume from changing the roster during snapshot/save. Sheet reads use the same
batch UPDATE mutex to return a coherent bounded roster (short read transaction,
no writes); summaries may be transient ordinary snapshots, never save authority.
Do not compute roster identity from stale client state or a previous RPC.

Canonical roster_token is SHA256 of UTF8 jsonb text of an array sorted by
enrollment UUID: `{enrollment_id,child_id,enrollment_version,relationship_id}`
for exactly active enrolments with active connections. Parse IDs through uuid
before JSON construction. Include enrolment version to catch pause/resume even
if final status is active. Return saved old record values for matching members;
new members are unmarked. A changed token requires reload, not silent omission.

Signal/status operations take workspace SHARE → batch SHARE → session SHARE →
child SHARE → guardian SHARE → connection SHARE → enrolment SHARE → request
advisory lock → actor/child/session advisory lock. Do not upgrade batch later.
Attendance takes request advisory lock after authority/batch/session locks and
before sheet mutation. Request locks are namespaced by operation plus request
UUID, not actor, so cross-actor UUID collisions serialize and then fail23505.
Current rights are checked before receipt disclosure. For replay/status, lock
the original payload's children/connections as well as current batch authority;
missing/inactive relationships deny disclosure. Historical replay can return a
committed receipt after pause/cancellation; it never performs a new write.

Current scheduling private insertion takes batch SHARE and is compatible with
this mutex. Coach assignment mutation015 also takes SHARE before its target
mutation. Any future cancel/move/restore/roster writer must take batch UPDATE
before session/roster rows. Privileged test/maintenance revocation must preserve
workspace → memberships → batch → session → children → guardians → connections
→ enrolments order when mutating multiple resources; direct single-row revokes
conflict with the held SHARE row locks. Arbitrary privileged multi-row updates
using another order are outside this RPC contract; do not claim global deadlock
freedom. On40P01/40001 transport-level uncertainty, keep the same request and
recover/retry after refreshing authority. Deterministic tests cover both orders.

Recheck session status/version and time-sensitive signal date after every
potential wait and before writing. A fully qualified private invoker clock helper
always delegates to pg_catalog.clock_timestamp() in production; revoke application
execution and permit no caller GUC, flag or runtime time override. In disposable
tests only, the privileged fixture owner may temporarily replace its definition
with an owner-only fixture clock, advance it while a caller is observably blocked,
and restore the original definition/drop the fixture in finally. This proves the
post-wait local-day recheck deterministically; it is synthetic-clock evidence,
not an observed natural/provider midnight. Production helper/ACL assertions must
prove that application roles cannot alter or select the time source. The authority/roster locks stay held through
receipt commit, so a revoke/cancel/pause either wins first and blocks the write,
or waits and affects subsequent reads/writes. Parent feed reads use FOR SHARE
locks on selected visible relationship/guardian/workspace rows for the transaction;
they cannot retract bytes already legitimately delivered before revocation.

## Atomic save, replay and unknown replies

Validate p_records is an array of1..200 objects with exactly enrollment_id,
child_id,status; IDs parse as UUID, states exact enum, no null/unknown fields,
duplicate enrolment or child (even case variants), oversized bodies (>64KiB),
fractional/negative/overflow versions or invalid token. Server and TS both reject.
Normalize UUIDs, sort by enrollment_id; object key and array order are irrelevant.

Attendance canonical payload is exactly:
`{operation:'save_attendance',workspace_id,session_id,expected_session_version,
expected_sheet_version,roster_token,records:[normalized record objects]}`.
Signal canonical payload is exactly:
`{operation:'send_parent_signal',child_id,workspace_id,session_id,
expected_session_version,type,reason}` (explicit reason:null included).
request_id is the immutable receipt key, actor_id is a separately bound field.
Status RPC p_payload accepts this exact object, applies identical normalization,
and compares the complete JSONB plus actor. Reject changed details23505, including
same key other actor; never match only actor/session/status or a payload digest.

After current access and request lock: if a matching receipt exists, return it
without reapplying new-write sheet/version/active-roster/cancel checks. If absent,
new save checks session version, sheet version (0 if absent), token and exact set
of current roster child/enrolment pairs. After current-authority validation,
roster/version/set mismatches raise40001. Unknown/foreign child-enrolment pairs
or unavailable current relationships raise42501 before receipt disclosure;
authorisation must not be weakened to force every invalid tuple into a conflict. Increment sheet
version once; update every submitted record with that version and one shared
server timestamp; append record events; upsert each attendance parent item;
insert immutable receipt. All run in one database transaction. Any record/event/
item/receipt failure rolls back every effect. Stable parent item id avoids
duplicate cards. Historical records for omitted now-inactive members stay intact.

For a matching status request with no committed receipt, return unknown after
the same request lock; this is not an absence proof or permission to replace the
UUID. Concurrent identical requests produce one operation/receipt. A known old
receipt may describe version1 while sheet is now3: always reload current sheet,
never install an old receipt as current editable data. A new explicit correction
gets a new UUID and observed current versions only after recovery resolves.

Application persists an in-flight request before send in sessionStorage under
`parentplus:attendance-pending:<actorUUID>` or `parentplus:signal-pending:<actorUUID>`.
Value is `{format:1,actorId,requestId,payload}` only; no names/contact/free text.
Validate storage on restore; quarantine malformed state with a redacted recovery
message. Pending helpers distinguish absent, valid pending, corrupt and unavailable
storage explicitly; corrupt never means absent. An immutable write distinguishes
stored/same from blocked and unavailable; it never overwrites a different pending
or corrupt entry. Clear uses the complete expected PendingOperation (actor,
operation, request and canonical payload), not request UUID alone, so clearing
attendance cannot remove a signal slot even if the UUID was reused across types. Keep the original key/body on timeout, thrown transport, malformed
response,40P01 or ambiguous provider failure; offer Check saved result and Retry
same request. Do not edit/create a replacement while unresolved. A definitive
22023/42501/40001/23505 RPC error is a rejected transaction and permits refresh;
status known plus receipt match resolves success. Clear only the matching pending
entry after a definitive outcome. Account switch clears displayed private data
immediately and never replays another actor's entry. Storage unavailable means
retain in memory and show “Keep this tab open until the save is checked”; no
claim of cross-device/new-tab recovery. No provider secrets enter storage.

## Typed item and safe fallback

Envelope exactly matches founder contract:
`{id,type,schema_version,child_id,class_id,priority,created_at,expires_at,payload}`.
Attendance v1 payload is exactly `{session_id,date,status,confirmed_at,
title:'Attendance recorded',body:<bounded status/date text>}`. date is the
session start's academy-local ISO date. No auth IDs, guardian details, private
coach notes or contact information in payload. No action is needed for v1.
Internal workspace_id/enrollment_id/source keys never enter envelope payload.

Client `renderParentItem(item: ParentItemEnvelope): ReactNode` uses the known
renderer only for recognized type AND schema_version1 with valid payload;
unknown type/version or invalid recognized payload uses a safe generic card.
Render title<=160/body<=2000 as React text; otherwise humanize bounded type and
empty body. Ignore all extra fields. Never use innerHTML, arbitrary markdown or
clickable raw URLs. If payload.action is an object, permit at most that one
`{label,href}` action; ignore action arrays/other shapes.

`safeParentAction(value: unknown,childId: string): {label:string;href:string}|null`
allows only an exact local route `/parent` or `/parent/children`, optionally the
single `child=<same envelope child UUID>` query. Build the final URL from the
allowlist, not from returned text. Reject fragments, duplicate/unknown query keys,
absolute/protocol-relative/backslash/control/percent-encoded path tricks,
javascript/data/file URLs, traversal and external hosts. Label is text1..80.
Destination re-verifies access; the link is never authority. These routes exist
in this slice; future routes require a deliberate allowlist extension.

All item reads check the child/guardian, active workspace/connection and matching
retained enrollment regardless of unknown type/version. Expired items are
excluded using server time. Only the reviewed private writer can label an item
safe for child_guardian audience; fallback rendering never grants data access.

## UI integration contract

Add feature modules `modules/attendance`, `modules/today`, `modules/parent-feed`
and server actions `lib/attendance/actions.ts`, `lib/parent-feed/actions.ts`.
Contracts own strict response decoders, canonical payload types and bounded input
checks. Server actions use createClient/getUser and compare expected actor every
call before RPC; never service credentials. Use redacted discriminated results:
`{ok:true,data:T}` or `{ok:false,kind:'invalid'|'forbidden'|'conflict'|'unknown'}`.
SQL errors22023/42501/40001/23505 map to definitive outcomes; other SQL/provider
or response errors remain unknown for mutations, ordinary failed state for reads.
Do not expose SQL messages. Read-only UI failure retains no stale cross-account
data, and retry refreshes the actual selected scope.

`TodayPanel` consumes verified actor and dedicated academy pages, autoloads first
eligible academy, date=today in its zone, seven-day date strip around selection,
actual session cards and Load more when paginated. Academy/date/session changes
increment a generation and discard late promises. Date changes never mutate data.
Header academy name comes from selection; greeting uses real display name only
when loaded, otherwise “Today”. Replace the static Meera/Creative Room values.
Keep prototype brand, compact cards, coloured strips and bottom navigation.
No stat tile appears until a real defined metric exists. A session card's actual
roster count is labelled enrolled children; no room if schema has none. Show
cancelled, attendance needed or attendance saved; don't confuse attendance and post.

`AttendancePanel({actorId,workspaceId,sessionId,onSaved})` loads one coherent
sheet and separately paged signals. Explicit Mark all present fills the displayed
complete roster after a confirmable visible action; it never saves. It preserves
already selected exceptions unless coach selects a separate explicit Replace
all marks action. “Review parent signals” presents missing_today suggestions;
“Apply absent suggestions” changes only unmarked rows with missing reports, not
saved/edited rows or late/drop/pick reports. Show which parents reported and time.
Neither action persists. Save requires every roster row marked. Success reloads
sheet and Today; on conflict reload and request review without merging silently.
Cancelled/oversized/zero roster is read-only with an honest reason. Poll signals
only while visible and authority is current; refreshing signals never resets edits.

`/parent` is a usable parent home with child selector, dedicated academy/class
selectors from eligible current connections/enrolments, date strip/session cards, own quick signals, exact
saved attendance feed and weekly counts. Automatically load ordinary reads after
session verification. Keep `/parent/children` as profiles/connections/classes and
add a real link to `/parent`; add Parent home to the signed-in login destinations,
preserving the existing profile destination, invitation links and creation recovery.
Parent date defaults to selected academy's today. Child or academy change clears
all dependent data and uses a new generation. Focus/session invalidation clears
private views before autoload; signout/unmount removes timers and late callbacks.
Do not reuse the existing boundary unchanged: it resets all state on focus and
does not preserve durable pending attendance operations. New shared boundary
must separate private fetched view invalidation from pending-operation storage.

All new copy has EN/HI keys and language selection. Date/status labels must be
localized, screen-reader announced; forms/toggles keyboard usable, hit areas44px,
save status live, no clipped mobile footer. Browser screenshots cover360px and
desktop, empty/loading/error/populated/cancelled/recovery states. Existing UI
catalog controls/scenarios must be revised when static demo controls disappear.

## Acceptance and evidence matrix

| ID / boundary | Required executable evidence |
| --- | --- |
| AT01 real Today | DB owner/admin/assigned-coach page isolation, no-assignment empty, date boundary/DST/cross-midnight, page50/51 ties; browser actual sessions from setup on selected date, correct academy/name, no demo stats. |
| AT02 explicit atomic attendance | Unit open leaves nulls, P/L/A+More, mark-all preserves exceptions, signal suggestion never saves; DB exact roster set, five states, sheet0→1, correction1→2, events/item/receipt same commit; browser saved rows survive reload. |
| AT03 strict inputs | SQL+TS reject null/wrong JSON/extra keys/duplicate/case variant IDs/bad versions/NaN dates/oversize/same child wrong batch; reordered array/object keys and upper-case UUIDs normalize to the same receipt. |
| AT04 concurrency roster | Deterministic052 admission/pause/resume/withdraw writer-first and attendance-first; pause/resume version ABA; child connection restriction/reactivation both orders, including initially hidden active enrolments; stale token refresh; no phantom or partial sheet. |
| AT05 authority races | Workspace suspend, membership suspend/demotion, assignment removal, guardian revoke/dispute and connection restrict in both orders; blocked call rechecks after wait; no receipt/item created when revoke wins. Manager, parent, stranger and other tenant negatives. |
| AT06 session race | Cancel/move/restore private fixture takes batch UPDATE then session UPDATE; both orders with save/signal. Cancellation first rejects new write; attendance first commits then cancellation preserves historical record. Version mismatch after move/restore rejects. |
| AT07 idempotency/recovery | Duplicate/concurrent identical same UUID commits once; other actor/full payload change conflicts; original receipt after newer save does not overwrite latest UI; dropped response before/after commit, reload restore, unknown status and same-key retry, malformed response, account switch and storage unavailable. |
| AT08 rollback | Inject failure at record/event/item/receipt separately; full before/after snapshot equality and zero new receipts. Signal insert/receipt failure also rollback; no orphan item or double count. |
| AT09 parent history/security | Creator+eligible guardian sees only own child; pause/end retains history but removes signal eligibility; revoked/restricted/suspended hides result immediately on next read; other parent never sees it; cancellation does not erase history or claim presence. |
| AT10 signals | Four enums, bounded missing reason, no free text, current academy local day only, active enrolment required; latest per actor plus immutable history, deterministic concurrent ordering, coach right batch only, own parent report only, timestamp provenance,15sec visible poll/focus. |
| AT11 typed fallback | Unknown type/version and malformed known payload render text; malicious HTML, JS/data/external/protocol-relative/encoded path/backslash/control URLs, duplicate query, wrong child and action arrays produce no unsafe navigation. Extra fields don't crash. DB base access independent of type; expired items excluded. |
| AT12 factual counts/bounds | 0/50/51 session/feed/signal pages;200 editable/201 blocked roster; no partial totals; weekly seven-local-day exact counts over >50 rows, statuses correct, signals don't count; paused old records don't inflate current roster. |
| AT13 complete signed journey | Actual local Supabase OTP/JWT browser: manager creates academy/current-date session → separate parent creates child/accepts link → explicit enrolment → Today mark/save → parent's exact result/weekly count → own signal → coach sees correct session → pause removes roster → unrelated parent denied. Each reload proves DB persistence. Mobile+desktop. |
| AT14 migration/evidence | Fresh PostgreSQL17 all053;052→053 existing data fingerprint preservation; every new private table/helper ACL, role/tenant negatives; runner collection/execution/JUnit/cleanup includes every new case/table; full source-bound selected frontend/database/browser/ops checks, independent review. |

Tests use synthetic fixtures; no provider simulation is called a signed-provider
journey. At design creation053 checks are unrun;052 passed its full source-bound
gate. Controller owns canonical docs, exact scenario IDs and verified publication.
Actual rollout uses the authorised existing TEST environment only after reviewed
source is immutable; implementers make no hosted calls. Broader real-family
retention, guardian dispute and launch policy remain existing release boundaries.
