# Session change safety — local authentication slice

## Purpose and acceptance
A user who signs out or changes account in another tab should not continue seeing an old signed-in state in the login screen. When live authentication is enabled, subscribe to provider auth-change notifications as invalidation hints, not identity proof; confirm identity separately with getUser. Ignore the initial subscription event for identity. Invalidate pending checks and login completions when a later event arrives; clear stale one-time codes and avoid exposing user or token data. Disabled mode must not create a client or subscribe.

## Security and boundaries
Never await or invoke provider calls within the provider callback; defer checks until after the callback returns to avoid SDK lock reentrancy. Handle notifications during local verification or sign-out without allowing stale completion to overwrite newer state. A sign-out error remains uncertain even if the SDK has cleared local state. Stop listening and invalidate pending work on unmount. Subscription or verification errors show an unavailable state, not a guessed identity.

This is a local, mocked-event slice: it does not establish timely expiry or remote revocation detection, real cross-tab delivery, real-provider behavior, protected-route authorization or child access. Such integration and security checks remain release blockers. No hosted service or real account is used.

## Test plan
Test subscription disabled mode, ignored initial event, relevant notifications, callback timing and unsubscribe. UI tests exercise delayed provider verification overtaken by sign-out, event during verification, event during sign-out failure, and unmount cleanup. Add requirements mappings; independently review race handling and run frontend, browser and database quality checks.
