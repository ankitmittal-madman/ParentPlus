# ParentPlus automated browser testing

## Enrolment report — verified 10 November 2026

The current catalogue has43 scenarios and99 route/control mappings. Local run
`run-20261110T125133Z-daf7fd` passed86/86 desktop/mobile executions with zero action
gaps and86 embedded screenshots, matching the final-v6 source fingerprint in
Quality Evidence. It adds five enrolment scenarios plus public install metadata:
explicit admission, parent reload/lifecycle, same-request interruption recovery,
Hindi/two-batch states and two-manager stale-edit reconciliation. This does not
claim every possible interaction, physical-device installation or unbuilt features.
Five future-feature gap groups remain explicit; the complete founder catalogue
is tracked in Build Progress. Earlier37/33-scenario entries below are historical.

**What the e2e folders mean:** E2E means end-to-end: testing a journey through its
actual boundaries. `apps/web/e2e-qa/` drives the browser against real local Supabase
and produces Excel/HTML/screenshots. `e2e/` checks signed-out/disabled-provider
behaviour; `e2e-enabled/` uses a deliberately synthetic isolated provider;
`e2e-local/` checks actual local email OTP; `e2e-founder/` checks dummy OTP with the
real local database; `e2e-qa-harness/` checks reporting/control discovery. Their
names do not make synthetic checks equivalent to real-provider or deployed tests.

## Invitation scenarios added — 10 November 2026

Verified local run `run-20261110T095841Z-4cf29f` passed74/74 with zero action gaps
and74 embedded screenshots. It covers81 mapped route/control pairs. The current
register adds four family-invitation scenarios (37 scenarios total,
74 desktop/mobile executions): separate coach/parent connection with persisted
roster, missing/fake links, interrupted issue recovery, and Hindi controls/empty
parent connections. See `quality/browser-scenarios.json` for exact control mappings.
The Students route now tests the real connection interface, replacing the older
Coming soon expectation. Pagination and adversarial database histories have SQL/
component coverage; this does not claim every possible UI state or full M2-49.

HTML and Excel reports must distinguish successful scenarios from observed or
unclicked controls. Invitation inputs are masked, textual invite secrets redacted,
and raw diagnostics excluded from upload. Later results must be checked against
their recorded source fingerprint; earlier 33-scenario evidence below is historical.

The founder confirmed the deployed parent and coach entry journeys work for an
initial manual check. This system adds repeatable headless testing of the code
against a real, checkout-owned local Supabase stack. It does not test the deployed
Vercel URL or send email, and needs no hosted Supabase credentials.

## Scenario register and reports

`quality/browser-scenarios.json` is the versioned source for33 detailed browser
scenarios and route/control expectations. Tests live in `apps/web/e2e-qa/` and
identify scenarios with stable IDs. Each scenario runs at1280×900 and390×844:
66 expected executions. Five future feature gaps remain explicit. The catalog
does not claim all possible interactions or full product completion.

Each fresh run generates:

- `index.html`: self-contained results, filters, expected/actual outcomes,
  per-scenario screenshots, action coverage, evidence errors and future gaps.
- `ParentPlus-Test-Scenarios.xlsx`: overview, detailed scenario steps and
  preconditions, browser results, control coverage, existing regression inventory
  and product gaps. Cells are literal text, not executable formulas. Edit the JSON
  catalog and test together; regenerating a workbook replaces manual Excel edits.
- `summary.json`: sanitised machine-readable result and coverage summary.

HTML screenshots are embedded so the report stays readable after download.
The Excel file sits beside the HTML; keep them together for its download link.
The regression inventory is explicitly an index, not proof that those separate
unit/database suites executed in the browser job. Their results remain in the
existing intelligent quality workflow. The new browser suite supplements that
gate; it does not alter its protected minima or receipt validation.

## Run locally

From the repository root with locked frontend dependencies and local Supabase:

```sh
bash scripts/dev/local-supabase.sh start
PARENTPLUS_CHROMIUM_PATH=/usr/bin/chromium python3 scripts/qa/run-browser.py
```

Omit `PARENTPLUS_CHROMIUM_PATH` when using Playwright-installed Chromium. Reports
are in a NEW ignored `test-results/qa/run-<UTC>-<unique>/` folder every time;
`test-results/qa/latest-run.txt` gives its location. Prior reports and existing test
records are preserved. The runner restores previous local feature controls.
Never run a second manual founder/test launcher while this lease is held.

No API/table/session fixtures replace the normal app journeys. Deterministic
fault scenarios deliberately abort selected local browser or Next server-action
requests, assert the interruption occurred, then exercise the real recovery path.
Other scenarios use normal UI calls and database persistence. Browser requests
outside the exact loopback app/API are blocked. Test accounts are fictional .test
addresses. Videos, traces and request/response capture are disabled; verification
inputs are masked in screenshots. Raw diagnostics stay local and are not uploaded.

## Regular GitHub workflow

Published `.github/workflows/founder-browser-quality.yml` triggers on pull requests,
pushes to main, manual dispatch and daily00:30UTC (06:00IST). GitHub may delay
scheduled starts. The workflow is on the default branch and its first push run passed
(run42783630419, code431c0e7). The daily schedule is configured; a scheduled
execution has not yet been observed.

Flow: checkout → locked dependencies/Chromium → report regression checks → fresh
local Supabase → desktop/mobile journeys → HTML/Excel → artifact upload → stop
local Supabase. It uses read-only repository permissions, no inherited application
secrets and no privileged pull_request_target event. Existing quality checks stay
in place. Reports are uploaded after failures as well; setup failures produce
NOT RUN evidence. Missing/duplicate scenario-viewports, skips, retries, screenshots
or unmapped/unexercised controls fail the job. Future features are NOT BUILT,
not skipped passing tests. Reports are retained14days; generated artifacts are
not committed or automatically published to a public Pages site.

To review an active run: GitHub repository → Actions → ParentPlus Founder Browser
Quality → selected run → Artifacts → download parentplus-browser-report → extract
ZIP → open index.html. The workbook is in the same extracted run folder.

## Coverage and maintenance

Add a scenario, steps and expected result in the catalog; implement the matching
ID in Playwright; map each control to scenarios that assert its outcome. Visible
controls are discovered during tests. Newly discovered controls without a mapping
fail coverage rather than silently disappearing. EXERCISED requires a recorded
click in a mapped passing scenario on both viewports. Busy labels refer to the
same stable control. Discovery cannot enumerate every conditional state by itself;
the authored inventory and lower-level failure/concurrency tests remain necessary.

## Product defect found by the new suite

CLASS-004 reproduced a real later-class recovery defect: migration048 archives
the first acknowledged setup and writes a v2 begin receipt, while recovery from029
recognised only legacy next-request receipts. Forward migration050 recognises an
exact actor/workspace/intent/generation/course/batch v2 receipt while preserving
legacy validation, authorisation, locking, relation checks and private privileges.
No record rewrite is needed. The returned legacy prior/request pair remains NULL.

The isolated SQL regression failed with the old recovery function and passed with
050. Its companion checks reject missing receipts and mismatched actor, workspace,
generation, course and batch. The fix was first verified on checkout-owned LOCAL
Supabase, then applied to the existing hosted TEST project after founder approval.
Its migration receipt, preservation hashes and helper privileges were verified.
Direct hosted-browser regression remains unrun from this restricted network. Existing scripts now
expect50 migrations and423+4=427 database cases; no coverage minimum was lowered.

Exploratory browser runs and failed reports are retained. The first setup run
correctly reported no passing cases when Chromium was unavailable at its default
path. A later run passed62/66; the remaining menu-state and SDK sign-out assumptions
were corrected in the tests. Final current-source execution and independent review
are recorded in the final handoff/ignored quality receipts, not inferred here.


Independent review fixes: attribute-only reveals and zero-scenario success were
reproduced and fixed. Two standalone browser instrumentation checks verify revealed
controls and non-capture of field values; offline report tests include zero/missing
evidence, project mismatch, unsafe screenshots, skipped/retried/duplicate results,
unmapped controls, literal Excel cells and escaped HTML. Interrupted JSON still
produces failed HTML/Excel. CI executes these checks before the app journeys.


First hosted report: [run42783630419](https://github.com/ankitmittal-madman/ParentPlus/actions/runs/42783630419), [download artifact](https://github.com/ankitmittal-madman/ParentPlus/actions/runs/42783630419/artifacts/13747596711). Download/extract in your browser; this workspace cannot fetch the artifact-storage redirect. Full GitHub quality run42783630836 and Vercel deployment for431c0e7 passed.
