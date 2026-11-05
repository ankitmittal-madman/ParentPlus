# Login browser tests — local synthetic slice

## Purpose and boundaries
Exercise the actual ParentPlus login page in Chromium with live OTP disabled. A parent or coach should see an accessible email form, receive a clear error for an invalid email, and receive a truthful disabled-service message instead of a false delivery claim for a syntactically valid email. Synthetic example addresses only; no hosted provider, real accounts, child data or production access.

## Architecture and risk
Use Playwright against a locally built Next.js server. Pin the free test dependency, run only local Chromium, start a server with live OTP disabled, and make the browser suite a mandatory step of the existing frontend CI job before its success receipt. Keep component and database tests unchanged. Use a fixed localhost base URL, block an enabled live-OTP environment, and intercept non-local page requests. Page interception does not establish server-side network isolation. Validate exact browser cases and bind their JUnit evidence to the frontend receipt. No changes to authentication, database or security policy.

## Acceptance and gaps
Tests cover page load/accessible label, malformed email and valid-email disabled-provider response with no success claim. A passing browser check does not prove email delivery, successful live OTP, session persistence, provider authorization, mobile-device behavior, or protected-route security. Those remain separate M2 release gaps. Test failures and missing browser/dependencies must fail the CI job rather than be skipped.
