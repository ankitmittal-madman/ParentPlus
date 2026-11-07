# Coach route access — 2026-11-07

## Outcome

Protect the `(coach)` route group using the signed-in user's active workspace
membership. Give signed-in users without an active workspace membership a clear,
recoverable message. This slice does not enable course or batch writes.

## Acceptance and threats

- A missing or invalid provider identity redirects to `/login` before any
  membership read.
- Membership access is limited to the actor's active membership and active
  workspace; owner, admin and coach are the only accepted roles.
- Provider errors and malformed identity or membership results fail closed.
- A user with no eligible membership receives an explanation and can sign out;
  failed sign-out is reported without claiming success.
- Anonymous browser navigation to the coach home (`/`) and `/schedule` returns
  to the sign-in journey.
- No hosted data, migration, or class setup write path changes in this slice.

## Security boundary

The route guard uses the server Supabase client and `auth.getUser()`, then reads
`workspace_memberships` through existing RLS. Migration
`20261101000300_initial_rls.sql` permits a user to read only their own active
memberships; workspace rows are limited to active memberships. The route guard
adds an active workspace filter and explicit allowed roles. This is a page
boundary, not a substitute for authorization checks in future write APIs.

## Scenarios and evidence

Unit coverage: `requireCoachAccess` tests anonymous identity, eligible roles,
empty membership and provider errors. UI coverage: `coach access recovery`
tests the sign-out path and uncertainty message. Browser coverage checks an
anonymous coach-home and schedule navigation redirect to `/login`.

## Remaining work

Class setup is still unavailable. Independent review, real-provider/JWT checks,
hosted configuration and the cross-manager reservation/recovery race remain
open. The next class-setup slice must fix and verify that race before adding a
course + recurring batch write flow.
