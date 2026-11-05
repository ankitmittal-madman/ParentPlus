# ParentPlus — Quality Evidence Index

This is the canonical index of verification provenance and known availability,
not a replacement for raw results, the requirements registry or historical audits.
Update after quality checks. Distinguish a plan, an execution, an approval, a local
commit and a hosted result. No connector or CI result is inferred from a document.

## Recorded local implementation verification

| Field | Recorded value |
| --- | --- |
| Execution record baseline | ac2b1f9af85b531142310fcd851a24c17390f4ae, before the quality-gate commit |
| Source fingerprint | 70088b03963e79bd2993f5ffef801e3257eb28b48d09992d5b96ae3deb7447f7 |
| Subsequent local checkpoint | 5b068b995957414a47dd2f47e8b6eb4147958563 |
| Provenance reconciliation | This session reconstructed the committed 5b068b9 file fingerprint and confirmed it matches the execution record |
| Raw record | test-results/quality/audit/verified/quality-gate.json; ignored local artefact, not guaranteed present in another checkout |
| Independent review | Recorded in the versioned audit below; it is a prior review, not a new review of these documentation additions |

| Recorded check | Outcome | Limit |
| --- | --- | --- |
| Strict quality-engine tests | 49 passed | Prior execution; no claim the new docs have a fresh full-gate pass |
| Frontend | 24 tests, lint, type check and build passed | Mocks/component tests; not live OTP or E2E |
| Database | 39 unit cases and four standalone scenarios passed | Synthetic auth, isolated PostgreSQL; not hosted JWT/production authorization |
| Database setup/cleanup | 13 migrations applied locally; no residual test data | Not a migration deployment approval |
| Adversarial evidence checks | Source/receipt/report mismatch cases rejected | Local caller declarations still require an honest process and review |

Detailed findings, gap dispositions and original validation are owned by
[the independent audit](INTELLIGENT_QUALITY_GATE_AUDIT.md). The
[initial implementation report](INTELLIGENT_QUALITY_GATE_REPORT.md) is historical.
The [gate guide](INTELLIGENT_QUALITY_GATE.md) owns commands and evidence formats.
Counts here describe that recorded run; executable inventory is authoritative for
future counts, not a permanent numeric threshold in this document.

## Current documentation foundation

Scope is listed in [the handoff](AGENT_HANDOFF.md). Local documentation validation
on 2026-11-03 checked 14 Markdown files and 78 local file/directory links, preserved
the existing root/communication instructions and historical contract text, and
confirmed protected implementation files were unchanged. Whitespace and exact
Git-scope checks passed. These are local checks, not an installed CI checker.

A fresh strict engine self-test passed 49 cases. Registry/policy validation also
succeeded and produced a selection plan; it selected quality, frontend and database.
The latter two suites were not executed for this foundation. Temporary local
validation output is under /tmp/parentplus-context-foundation-checks; it is not a
portable GitHub artefact or a complete passing quality-gate record.

A separate read-only reviewer inspected the documentation and found an Important
Claude bootstrap-path omission. The entrypoint now explicitly names the shared
bootstrap and Claude adapter; both files exist and their links were checked. The
wording fix is verified locally, not by observing a future Claude session. Minor
duplicated Git-state and package-version details were reduced. Application and
future cross-agent behavior are outside that review's execution scope.

The current draft's source snapshot differs from the recorded implementation
snapshot above. Do not copy its old reports into a new receipt or claim they
validate this draft.

Application/database execution and hosted CI have not been rerun for this
foundation. Existing policy still selects broader regressions for root agent
instruction changes; that policy is unchanged. A local selection plan would not
establish those selected suites passed. The proposed documentation CI checker is
not implemented in this phase.

## Availability and sharing

- Versioned audit/report summaries survive an approved commit and publication. Raw test-results directories are ignored; another assistant must report them unavailable unless supplied or retrieved through authorized access.
- Existing workflow definitions retain hosted artefacts for 14 days. Their presence, URL, run/attempt and conclusion must be inspected; no hosted run URL is currently attested here.
- Preserve a sanitized durable summary of important run outcomes and source identity. Do not publish secrets, personal data, full environment dumps or private chats as evidence.
- A bundle of local results must identify branch, preparation baseline, source fingerprint, environment, dirty scope and omissions; it is not automatically the GitHub-published state.

## Future record contract

For each meaningful check, record date/environment, what ran, command or runner,
source baseline and fingerprint, result and actual case counts, skipped/failed/
expected-failure/unrun outcomes, artefact location/access/retention, review scope
and outstanding risks. Add real hosted run/attempt/commit links only after they
are inspected. Keep this index concise and link detailed feature reports.

Do not close broad security checklist items just because a narrower test passed.
The ten product gaps and their conditional release blockers remain in the audit
and registry; the documentation foundation changes none of their statuses.

## Reconstructed email verification screen — local scope

The reconstructed uncommitted slice uses mocked UI verification and keeps live OTP disabled by default. New scenarios cover accepted/rejected verification, field-associated errors, changing the email and concurrent submission; the successful state also receives keyboard focus. The initial focused tests failed because the code field was absent; the separate focus regression failed before its fix. Inspect the current local quality plan and reports for exact snapshot results; earlier environment results do not attest to this reconstructed work.

An independent reviewer identified incomplete session-aware continuation and sign-out, provider template compatibility, and potential account enumeration when provider responses differ for unknown accounts. These remain open for the live sign-in slice; no hosted provider was contacted. Complete sign-in browser E2E and real-provider sign-in remain release gaps.

## Browser test and evidence extension — local scope

The initial two Playwright scenarios exercise the login page through a real local Chromium browser with OTP disabled: invalid email and the disabled-provider response. Browser page requests outside the fixed localhost origin are intercepted, but this is not an operating-system network sandbox. The frontend CI workflow was changed locally to install Chromium and run these checks before attesting; the change has not been verified on GitHub.

An independent reviewer identified that skipped browser tests could otherwise appear as a successful frontend job. The quality gate now requires a Playwright JUnit report containing exactly the required cases, including the synthetic schedule preview, with no skipped, failed or missing results, and binds its digest in the frontend receipt. Regression tests exercise absent, skipped, wrong-case and altered evidence. A reviewer rechecked the correction and reported no remaining blocking finding in that scope. Inspect the current source-bound summary for the full run; hosted CI for this change, complete sign-in, live OTP and session behavior remain unverified.

## Local sign-out — current scope

The local screen and helper cover current-session sign-out after successful verification, generic failure handling and duplicate-submission protection using mocked provider responses. An independent reviewer found the SDK can remove local state before returning a provider error. A synthetic-fetch test using the actual SDK reproduced this; the screen now reports uncertainty rather than claiming an active session, and successful sign-out restores keyboard focus. The reviewer rechecked the correction and found no further important issue in this local slice. Inspect the source-bound local gate for current results. A local sign-out request is not proof of global device revocation, live provider behavior, session restoration or access authorization.

## Session restoration — current local scope

The local login screen uses provider `getUser` to choose between a signed-in display, sign-in form for a missing session, and a fail-closed retry for provider or configuration failures. Tests use mocked results and disabled mode makes no provider call. An independent reviewer identified that provider identity alone does not prove email verification; the screen now uses neutral signed-in wording, and retry focus was corrected. Inspect the current source-bound gate and final review for exact results. Cross-tab changes, expiry over time, live provider integration and server-side authorization remain unverified release gaps.

## Synthetic schedule preview — local scope

The schedule component and local Chromium tests cover the example-data notice and labelled list of course, batch and example session time. They do not establish backend scheduling, child access, enrollment or browser E2E for real scheduling. Inspect current local quality evidence and independent review for this source snapshot.

## Session-change safety — current local scope

Auth event handling is tested with synthetic notifications and deferred promises, including stale session/OTP results, sign-out failures during account changes, prior-email clearing, provider revalidation and unsubscribe. Independent review found account-switch and stale-email races; regression tests reproduced them and the revised implementation was rechecked. Exact current results belong to the source-bound gate summary. Mocked notifications do not establish live cross-tab delivery, remote revocation, timely expiry, or authorization of protected data.

## Session resume revalidation — local scope

When live authentication is enabled, returning focus or visibility triggers a recheck; disabled mode does not check. A signed-out user’s OTP entry or in-flight request is preserved if the provider confirms signed-out state. Tests use deferred promises for events overtaking older checks. Tests use synthetic focus events and mocked provider responses. Current source-bound gate evidence and independent review determine the result for the working snapshot. This is not continuous expiry monitoring, verified real cross-tab delivery, remote revocation or authorization to child/workspace data.

## Scheduling recurrence foundation — local scope

A pure local utility and tests cover one-off and bounded weekly recurrence, IANA time zones, daylight-saving gaps and overlaps, offset changes, elapsed duration, invalid input and occurrence boundaries. An independent reviewer found no material defect in the initial implementation and requested additional boundary coverage, which was added. The utility is not a backend authorization mechanism and is not integrated with persistent schedules. Inspect the current source-bound gate and independent re-review for exact results; hosted, UI and database scheduling behavior remains unimplemented.
