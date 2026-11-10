# Founder browser quality and reports

Founder request: automate headless tests for features, flows and button actions;
provide detailed Excel scenarios and an HTML results report with app screenshots;
make it a regular Git workflow. Founder manually confirmed both deployed initial
journeys work. Starting checkout: clean work at523efba, earlier stash preserved.
GitHub quality run42761558562 completed successfully for that commit.

## Approach and engineering choices

Extend existing Playwright and local Supabase. Keep an authored JSON scenario
catalog in Git, generate a genuine .xlsx workbook and self-contained HTML report
from the same catalog and actual Playwright JSON. Excel is the founder review
surface; executable tests remain versioned code. Excel-driven browser selectors
would be brittle; a separate paid testing service adds unnecessary dependencies.
These are routine engineering choices made under the founder's autonomy request,
not additional product decisions attributed to the founder.

Run desktop and mobile Chromium, synthetic .test accounts and actual local
Auth/PostgREST/PostgreSQL. Every browser scenario has a stable ID, persona,
preconditions, numbered steps, expected outcome, feature status and coverage kind.
Existing component/database tests stay mandatory and can be indexed in the Excel
regression sheet. Capture a screenshot and observed action names per scenario;
disable videos/traces and retain no cookies, request headers or provider logs.
Only synthetic local UI evidence is uploaded. Screenshots show outcomes, not proof
of database correctness; persistence and access assertions provide that evidence.

## Honest coverage

Inventory all current routes and expected visible controls. Report each authored
action as exercised, observed-only or not observed. Unmapped discovered controls
are visible as gaps, never silently called covered. Test happy paths, validation,
wrong OTP, account separation, reload/recovery, membership revocation/restoration,
navigation and mobile overflow. Fault-injection coverage remains separately
labelled from normal real-backend flows. Unbuilt enrollment/attendance/diary/fees
are not built, never passed. Placeholder-navigation checks assert only navigation.
No finite suite establishes every possible flow; report explicit scenario/action
coverage and remaining gaps instead of a blanket100% claim.

## Workflow and evidence

New additive GitHub Actions workflow on pull requests, pushes to main, daily
00:30UTC (06:00IST), and manual dispatch. Run the checked-out app with a fresh
local Supabase stack, not a shared hosted database. No hosted credentials required.
Use read-only repository permissions, fork-safe execution, no privileged PR event,
and finite timeout. Generate/upload HTML, Excel and summary even after failures.
Missing/duplicate scenarios, skipped/flaky outcomes, absent screenshots and failed
assertions fail the run. Existing intelligent quality/security workflow is retained.
Artifacts retained14days; do not automatically publish synthetic evidence to a
public Pages site or commit generated reports on every run.

Workbook: overview, detailed browser scenarios, browser results, action coverage,
existing regression inventory and future feature gaps. HTML: run/commit/environment,
status totals, filters, scenario steps, expected/actual status, screenshots, action
coverage and gaps. Missing reports produce NOT RUN, never a green scorecard.
HTML escapes untrusted content; image reads are confined to the run directory.
Inline-string spreadsheet cells cannot execute formulas.

## Acceptance and next product slice

Reproduce report validation defects with offline tests, execute all authored
browser scenarios on both viewports against actual local data, validate .xlsx ZIP
and XML structure, inspect representative screenshots/report, run existing gates,
obtain independent review and preserve all prior work. Repository publishing and
active scheduled-run claims require their actual authorisation and execution.
Next product slice after this safety net: parent/workspace connection and separate
class enrollment, before attendance and parent learning visibility.


## Narrow defect repair discovered during implementation

CLASS-004 exposed a legacy/v2 receipt incompatibility after the first class was
acknowledged. Forward050 admits only an exact current v2 begin receipt in that
legacy history guard, preserving all other checks and privileges. Add successful
second-generation recovery and mismatched-provenance SQL regressions; retain the
original browser failure and prove its corrected real-backend outcome. No data
rewrite, hosted application or old-migration edit is part of local verification.
