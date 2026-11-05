# Local sign-out — email verification slice

## Purpose and acceptance
After successful code verification, a parent or coach needs an explicit way to sign out before using another email. While this screen knows verification succeeded, hide the sign-in form and show a clearly labelled sign-out action. Attempt to sign out only the current local session. Restore the sign-in form only after the provider reports success. On a provider error or exception, show an uncertain sign-out status with a retry action instead of claiming the session is still active; prevent duplicate sign-out requests. After success, move focus to the restored email field.

## Security and boundaries
Keep live OTP disabled by default; never call the provider when disabled. Use the existing browser client and local sign-out scope without exposing tokens or provider error details. Sign-out is not proof of child/workspace authorization or global device revocation. If a provider error clears local state, a later successful retry cannot prove the original remote revocation succeeded. No protected route, hosted resource, real account or database change is included. Session discovery after reload, cross-tab behavior, refresh, globally revoked sessions, real-provider and browser sign-in testing remain explicit release gaps.

## Test plan
Test disabled, successful, provider-error and thrown-error helper responses; verify local scope and no sensitive errors. UI tests mock both OTP helpers and sign-out to verify success, failure and duplicate submission. Register every executable case, run the full frontend and database gate, and obtain a fresh independent review. Existing browser cases remain valid and do not simulate successful live login.
