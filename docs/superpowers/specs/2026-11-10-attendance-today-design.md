# Attendance, parent signals and real Today view — next dependent loop

Status: planned; no implementation or test pass is claimed by this design.

## Product outcome

Follow M2-06/M2-09/M2-41 and the Coach/Tutor prototype: a coach opens Today, sees
actual dated sessions and enrolled children, records attendance in a few taps,
then the permitted parent sees that child's saved result. Parent quick signals
help the coach prepare but never silently become confirmed attendance.

Use the existing workspace/course/batch/session model and reviewed enrolment
contract. Preserve dummy testing sign-in, all data/stash and original references.
UI follows prototype header/cards, date strip, live attendance list, P/L/A controls,
with EN/HI new copy and honest empty states. Replace existing example dashboard
data as the actual journey becomes available. No fabricated counts or no-op CTAs.

## Foundation needed in this loop

- Private RLS attendance sheets/records/request receipts/events, parent signals,
  and typed parent_items with controlled RPCs. New migrations only.
- Add session status/version if absent: default scheduled; cancelled sessions are
  excluded from active attendance writes, while existing history is preserved.
  Schedule-edit user flows come in the dependent schedule-change loop.
- Typed parent envelope matches founder contract: id,type,schema_version,child_id,
  class_id(alias of batch),priority,created_at,expires_at,payload. Attendance_record
  v1 has session/date/status/confirmation fields and fallback title/body. No contact,
  auth or private coaching note in payload. Receipt/event atomicity includes fanout.
- Unknown type/version must display safe escaped title/body and at most one safe
  internal action; never crash or navigate to javascript/external URLs. Parent
  reads derive current child/connection/guardian access irrespective of item type.

## Writes and concurrency

Attendance is saved explicitly as an atomic session sheet using expected sheet
version and a request UUID bound to actor/session/complete normalized record array.
Allowed states: present,late,absent,excused,make_up. Do not mark unreviewed children
present merely by opening a screen. Provide explicit Mark all present and review
signals actions. A saved sheet covers the current active roster exactly; mismatched
roster/version requires refresh rather than silently dropping/admitting a child.

Hold a batch FOR UPDATE row lock during roster snapshot and save. Existing enrolment
writes lock the batch FOR SHARE before their mutation, so this prevents concurrent
admission/pause phantoms without editing an applied migration. Use consistent order:
workspace/membership → batch → session → connections/enrolments → sheet/records.
Recheck permissions and session/connection state after waits. Add composite FKs/
unique keys needed to prevent mixed-workspace/session/enrolment/child references.

Private record events preserve corrections; latest parent attendance item is updated
atomically without duplicate cards. Failed record/item/event/receipt creation rolls
back the complete sheet. Same request retries return the original operation receipt
only after current permissions are checked; UI refreshes current sheet, never treats
an older receipt as latest state. Unknown responses retain request/actor/payload and
provide check/retry, not a replacement write.

Owners/admins and active coaches assigned to the batch can record attendance.
Parent reads/signals require own eligible child, active academy connection/workspace
and relevant enrolment. Signals require active participation; historical attendance
reads can include ended enrolment while current relationship/guardian access holds.
A revoked/disputed guardian or restricted relationship cannot access new data.

Parent signals: running_late,missing_today,dropped_off,picked_up. These are parent
reports, not verified handover or pickup authorisation. Latest signal is shown with
timestamp/actor provenance; it never authorises release of a child. Safe pickup log
M2-11 remains a separate permission-aware feature. Use request idempotency and do
not let one parent overwrite another's report silently.

## User experience and verification

Automatically load ordinary scoped reads after verifying the session; default to
single/first eligible academy and actual local date/time zone. Allow date/academy
selection and refresh without developer-style multi-step loading. Clear stale data
and ignore late promises after account/focus changes. Parent has a usable app entry
with child/class/feed selection rather than a profiles-only destination. Preserve
existing creation/recovery screens and invitation links.

Real browser acceptance: manager creates academy/class, separate parent connects
child, explicit enrolment, coach marks attendance, parent sees exact saved result
after reload; parent signal appears only in the right batch; pause excludes the
child; cancelled class refuses writes; another parent sees no result. Test batch
scope, wrong actor/workspace, bad statuses, duplicate/reordered JSON, stale sheet,
dropped replies, injected rollback and both concurrency orderings for permission,
connection, session and enrolment changes. Keep all catalogue/control/screenshot
mappings current. Test unknown typed-item fallback separately with synthetic local
fixtures without claiming a real provider. Full selected regression and independent
review before publishing; then continue class updates/parent feed.
