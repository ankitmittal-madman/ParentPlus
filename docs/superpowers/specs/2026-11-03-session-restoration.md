# Session restoration — local authentication slice

## Purpose and acceptance
A coach or parent who reloads the login page should not be shown a new sign-in form while their session is still valid. When live authentication is enabled, check the current user with the provider SDK before showing a verified state; no saved user or unverified cookie alone establishes identity. A missing session displays the sign-in form. A provider or configuration error displays an unavailable state and retry, without claiming sign-in or sign-out. With live authentication disabled, no provider client is created and the normal disabled sign-in path remains available.

## Security and boundaries
This check establishes neither guardianship nor workspace or child access. No protected destination or authorization decision relies on this client-side display. Keep live OTP disabled by default, do not contact hosted services in tests, and do not expose provider errors or tokens. Expiry, remote revocation, cross-tab synchronization and authorization must be verified separately with real provider behavior before release. Ignore results after the page unmounts; concurrent retry is disabled during a check.

## Test plan
Use synthetic mocked provider results for disabled mode, valid user, missing session, provider errors, malformed response and thrown errors. UI tests cover checking, restored identity, missing session and unavailable/retry states. Preserve current OTP and sign-out regressions, register all cases and run the full quality gate including browser and database checks. Obtain independent security review.
