# Founder testing with real local data

Founder instruction: dummy email/OTP, complete frontend/backend data flow, and
founder override controls for testing access scenarios. Preserve all uncommitted
work at 010fd412; do not modify hosted Supabase. Communication calibration ended
5/5; no new calibration counter is required.

Use the existing Next/Supabase implementation. A development-only, server-enabled
local sandbox accepts synthetic .test emails and code 123456, exchanges a local
admin-generated one-time token for an ordinary local session, and persists it
through the existing browser client. No real mailbox, external identity check,
mock database or fake session. Browser code never receives the local service key.
Normal persona operations continue through actual user-scoped RPC/RLS boundaries.

Founder console can inspect local record counts and assign active/suspended/removed
owner/admin/coach memberships to synthetic test accounts. This is an explicit local
founder override, not a relaxation of production policies. Require development
runtime, private and public mode flags, exact loopback API endpoint and local-only
credentials. Refuse production/hosted endpoints before creating an admin client.

Launcher validates checkout-owned local containers, enables existing controls and
features during manual testing and restores prior controls on normal shutdown.
A separate browser config tests dummy login, real child/workspace/class writes and
membership override. No data reset, deletion of existing records, commit or deployment.

This completes founder access to implemented first-use features. Enrollment,
attendance, diary and fees remain visibly incomplete until actual workflows exist.
