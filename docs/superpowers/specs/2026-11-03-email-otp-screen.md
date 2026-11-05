# Email OTP screen — local slice

## Product problem and acceptance
A parent or coach who has requested an email code needs a field to enter it. After an accepted request, show a labelled code field; pass the normalised requested email and code to the existing verification helper. Report success only on helper success; show a field-associated error on rejection or failure. Changing the email invalidates the displayed code step; concurrent submissions and email edits are disabled while a request or verification is in progress.

## Security and boundaries
Email authentication does not establish guardianship, workspace membership or permission to read child records. Keep live OTP disabled by default and preserve the existing no-automatic-signup setting. Do not expose tokens, access hosted services, or add navigation to a protected destination. A real provider session, signup, expiry, rate limits and protected routes require separate integration and security verification.

## Test mapping
The four FE-LOGINPAGE requirements added to the registry cover successful and rejected mocked verification, email changes, and concurrent verification controls. Existing request and verify helper cases cover input validation, disabled live calls, provider failures and missing sessions. Browser E2E and real provider behavior remain uncovered release blockers. Confirm the configured provider email template exposes the six-digit token and assess whether unknown-email responses enable account enumeration before live rollout. The current local UI provides explicit sign-out and a provider-checked restore path; actual provider behavior, cross-tab synchronization and session-aware navigation require separate verification.
