# Parent child-profile creation — local draft

## Product scope

A signed-in parent can check creation status, enter a child name, create a profile, confirm that they have seen the result, and deliberately start another profile. The initial relationship is provisional and self-declared; this flow does not establish legal guardianship, connect an academy or give access to private academy records. The existing parent profile list is paused while a creation result is uncertain and marked for refresh after a confirmed result.

## Local design and boundaries

Migration 035 atomically revokes authenticated access to the legacy `create_child` function and publishes narrowly scoped authenticated wrappers. The existing private database creation control remains off by default; both `PARENTPLUS_ENABLE_PARENT_CHILD_LIST` and `PARENTPLUS_ENABLE_CHILD_CREATION` also default off on the server. The server flags are not database authorization: the database control and current database identity gate direct RPC calls as well. No hosted resources are changed by this draft.

Each actor has one durable current creation intent. Its previous-intent and request IDs bind a retry to its original request. The database serializes an actor's status, begin and acknowledgement operations and creates the child, provisional guardianship and intent atomically. A repeated matching request returns the same result; changed or stale requests fail closed. A separate explicit acknowledgement is required before starting another profile. The client rechecks the returned intent before displaying a result, does not automatically acknowledge it, and can retry the same unconfirmed request while the original session and input remain in memory.

The list and creation panels coordinate only within the current page. They clear displayed data on observed auth, focus and visibility changes. If an uncertain creation cannot be attributed to the exact request, the page blocks another attempt rather than assuming failure. A session change clears the retained child name; an unresolved request may then require a later check or manual recovery. This can also block a different account's list in the same page until resolution. No browser storage, logs or URL parameters are used for child names or request recovery.

## Release limits

This is a default-off local draft, not a complete end-to-end feature. Recovery context in the browser does not survive navigation, crash or reload; same-actor database status is durable, but cross-account identity loss and requests after intervening generations need a reviewed recovery path. Existing profiles created before this protocol have no intent record and require a migration/reconciliation plan; names cannot establish identity. The database retains only the current intent, so old request receipts and deletion/retention policy remain open. A local event does not coordinate other browser tabs or prove live revocation; names already displayed may remain visible after remote access changes until invalidation.

Before release, verify real signed-JWT/PostgREST roles and function ownership, provider sessions and revocation, abuse controls, browser and cache isolation, live failure/retry behaviour, accessibility, old-data reconciliation, recovery/escalation and retention. Do not enable the controls or use real child data until the relevant security review and authorization are complete.

## Test evidence scope

Synthetic local SQL tests cover initial and next requests, same and competing request IDs, stale priors, cross-actor denial, access revocation, control disablement, actual lock ordering, rollback and the private legacy ACL. Historical `create_child` behaviour tests temporarily grant the old function only inside isolated synthetic fixtures; separate actual-role tests verify it is inaccessible to authenticated users after migration 035. Mocked server and component tests cover flag-off behavior, actor checks, exact request provenance, uncertain responses, same-session retries, account changes, explicit acknowledgement and list invalidation. The existing browser suite runs with creation disabled and does not establish a live creation journey.
