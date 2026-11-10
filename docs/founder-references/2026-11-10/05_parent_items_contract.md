# 05. Parent items contract (UI-agnostic)

**In short:** everything a coach does reaches parents as a typed "parcel" with fixed fields. Any interface (today's PWA, a future native app, WhatsApp, a voice assistant) decides how to show each type. If an app doesn't recognise a type, it shows a simple fallback instead of breaking.

## Envelope (every item)

```json
{
  "id": "uuid",
  "type": "class_update",
  "schema_version": 1,
  "child_id": "uuid",
  "class_id": "uuid",
  "priority": 0,
  "created_at": "2026-11-04T13:02:00Z",
  "expires_at": null,
  "payload": { }
}
```

## Fallback rule

Every client must render any unknown `type`, or an unknown `schema_version`, as a fallback item:
`payload.title` (or the type name, humanised), `payload.body` (or nothing), and at most one action. Clients never crash on unknown types or extra fields.

## Pilot types (version 1)

| type | Created by | payload fields | Rules |
|---|---|---|---|
| `attendance_record` | Attendance trigger | session_id, date, status, confirmed_at | Only that child's guardians |
| `class_update` | `publish_post` | post_id, body, details.skills[], media_ids[], session_id, language | Media resolved through `can_see_media` |
| `child_note` | `publish_post` | post_id, body, details.level, details.home_tip, media_ids[] | One child only |
| `try_at_home` | `publish_post` | post_id, body, details.steps[], details.duration_min, details.skill | About one a week per child |
| `milestone_moment` | `publish_post` | post_id, body, details.skill, media_ids[], date | Kept permanently |
| `get_ready` | `publish_post` (Stage 6: reminder job) | post_id, body, details.items[], details.wear, session_id | Evening before, or 3 h before |
| `announcement` | `publish_post` | post_id, body, details.needs_reply | Quiet hours apply |
| `schedule_change` | Stage 6 | session_id, change, new_starts_at, reason, needs_rsvp | Affected families only |
| `fee_due` | Stage 9 | fee_id, period, amount_paise, due_date, upi | Paying guardian only |
| `receipt` | Stage 9 | payment_id, amount_paise, method, period | Paying guardian only |

## Changing the contract

- Adding a field: allowed in the same version. Clients ignore fields they don't know.
- Renaming or removing a field, or changing its meaning: bump `schema_version`, and keep writing the old version until every client supports the new one.
- New type: add a row here and a renderer in each client. Older clients show the fallback.
