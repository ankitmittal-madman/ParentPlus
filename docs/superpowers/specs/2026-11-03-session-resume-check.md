# Session revalidation on returning to the app

## Purpose
When a coach returns to an open ParentPlus tab, check the current provider user again rather than relying only on the status established when the page opened. Only apply this when live authentication is enabled. No check authorizes access to a child or workspace.

## Behavior and safety
On window focus or return to a visible document, defer revalidation until any in-flight operation finishes, then block the form while checking the current provider user. Preserve an active OTP entry when the provider confirms signed-out state; clear it on a confirmed signed-in state. A newer provider auth-change event invalidates stale operations and older checks. If a verified view was visible, clear its previous email from the screen before revalidation. Keep in-flight sign-in and uncertain sign-out handling safe; never turn an uncertain sign-out into an unverified success. Coalesce notifications and unsubscribe listeners on unmount. No provider calls occur when the feature flag is disabled.

## Tests and limitations
Use mocked provider outcomes and synthetic focus/visibility events to verify rechecking, stale-check handling, disabled mode and clearing prior identity. This is not a timed expiry monitor: a visible page may remain stale without a focus or provider event. Real cross-tab delivery, live provider revocation, network failures and backend authorization remain release gaps.
