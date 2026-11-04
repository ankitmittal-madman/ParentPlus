# Parent-created profiles — local read-only draft

## Product and scope

A signed-in parent needs to find profiles they have created. This narrow list displays only IDs and names for children created by the current account where that account still has a provisional or active guardianship. It does not show every linked child; revoked, disputed and missing relationships are excluded without explaining why. It does not establish legal guardianship, create a child, grant access to an academy or expose the child directory.

## Privacy and operation

The database read control `parent_child_read_controls` and server flag `PARENTPLUS_ENABLE_PARENT_CHILD_LIST` default to false. The authenticated-only database function checks the current database identity and locks the control and returned child and guardian rows for the read transaction. It returns at most 100 profiles and fails closed above that limit; it does not silently present a truncated list. The server validates and projects only identifiers and names, and the dynamic page avoids static rendering. The interface requires session observation, clears displayed names on observed auth, focus or visibility changes, and ignores stale responses. No browser persistence is used.

This is local groundwork, not a released parent journey. Already displayed names may remain visible if access is revoked while the tab stays open and no invalidation event occurs. Real signed-JWT/PostgREST enforcement, continuous revocation, cross-tab event delivery, browser caching, pagination beyond 100, real-device accessibility, provider access and end-to-end user testing remain release blockers. Client observation does not replace database authorization; an already delivered response cannot be recalled. Do not enable the flags or use real child data before the security and provider review.

## Tests

Synthetic local database cases cover disabled and anonymous access, caller ownership and guardian status, exact 100/101 bounds, private privileges, and both orderings of guardian revocation and control disablement against reads. Mocked server and component cases cover projection, malformed responses, missing identity, display, empty results, errors, session changes, stale responses and unmount. These do not prove real provider, browser-cache, or live revocation behaviour.

## Signed-in navigation

When the default-off public navigation flag is enabled, a confirmed signed-in view offers a link to this page; it is hidden while sign-out is in progress and when the session is unavailable. The public flag controls visibility only and is not an authorization control. It is embedded at build time; the server and database controls are separate and must be coordinated. A previously built link may remain visible if the server control is later disabled. Navigation does not itself authorise child data: the server action and database recheck identity and their default-off controls. Next.js prefetch is disabled on the link. If the server flag is off, the destination explains that profiles are unavailable. Real-provider, browser-navigation, cache and live revocation behaviour remain unverified.
