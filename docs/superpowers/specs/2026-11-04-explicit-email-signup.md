# Explicit email account creation — local draft

## Problem and acceptance

A new parent or coach needs an account before using ParentPlus. Existing sign-in deliberately requests an OTP with automatic signup disabled. This draft offers a separate, explicit “Create account” choice, hidden by default. When the choice and both local switches are enabled, the helper requests an email OTP with provider account creation allowed. The screen reports a signed-in state only after its verification helper succeeds or the provider session is revalidated. An accepted request does not prove that an email arrived or that a new account was created; the same flow may authenticate an existing account.

## Security and limits

The switches `NEXT_PUBLIC_ENABLE_ACCOUNT_SIGNUP` and `NEXT_PUBLIC_ENABLE_LIVE_OTP` default to false and are client-side interface controls, not provider access controls. A person with the public Supabase configuration can call the provider directly. Provider-side signup must remain disabled until separately approved and its configuration verified. Do not modify hosted settings in this work.

Before release, independently verify provider-side signup and rate limits, account enumeration and response behaviour, email template and OTP type, confirmation and expiry, abandoned unconfirmed-account cleanup, retries, account recovery, abuse, and real signed-session handling. Confirm provisioning without exposing children or workspace data. Email authentication alone does not establish guardianship or workspace access. No child data is requested or stored by this draft. Existing sign-in retains `shouldCreateUser: false`.

## Tests and evidence

Local mocked-provider tests cover disabled flags, explicit selection, signup intent, retry in the selected mode, code verification, in-flight switching and provider authentication event ordering. These tests do not contact a provider and do not establish live account creation or delivery. The existing browser checks run with live OTP disabled; they are not an enabled-signup end-to-end test.
