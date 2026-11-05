# ParentPlus Engineering Standards

Status: repository operating instructions for future work. These instructions guide Codex and reviewers; they are not a background autonomous service. Current task instructions and permissions take precedence. Preserve the installed Superpowers skills and Next.js guidance.

## Ownership and approval

The founder owns the product problem, acceptance criteria, release scope, unresolved privacy decisions and approval of reviewed checkpoints. Codex owns investigation, implementation within the authorized scope, safe local verification and an honest evidence report. An independent reviewer assesses the completed change and reproduces suspected defects; the implementation author remains responsible for fixes.

Use the existing checkout in an isolated cloud task. Before editing, record branch, full HEAD and `git status --short`; preserve existing work and identify which edits belong to this task. Work on the branch the founder authorizes. Do not create another branch/worktree, change machine-wide settings or reset unrelated work without authorization.

Default checkpoint rule: present the complete scope, independent-review findings, test evidence, gaps and exact changed files before requesting approval to commit. Do not commit until that approval is given. Commit approval does not authorize push, merge, deployment, hosted migrations, production access, repository settings or paid services; each requires explicit authorization for that action. Reuse authorization already supplied rather than asking again. Never ask for secret values in chat.

The older roadmap checkpoint language and DEC-002's founder-run terminal workflow are historical context, not permission to push or an instruction to ask the founder to run every command. Codex executes available safe checks itself; current instructions and these standards govern the handoff.

## Feature entry requirements

For a product feature, create a dated design/spec under `docs/superpowers/specs/` and an actionable plan under `docs/superpowers/plans/`, using the relevant skills. Scale detail to risk. A small documentation correction needs a concise purpose and validation note, not a full product design.

Before implementation, record:

- User and product problem, expected outcome, included/excluded behavior and constraints.
- Acceptance criteria with observable success and rejection examples, including unauthorized and invalid requests where applicable.
- Stable requirement IDs, implementation status and risk in `quality/requirements.json`; planned work must remain visibly unimplemented. A requirement describes a behavior, not merely a test filename.
- Affected routes, components, shared libraries, API boundaries, tables/functions/RLS, migrations, dependencies and workflows. Identify callers and downstream effects, not just files directly edited.
- Architecture choices and alternatives, data ownership, compatibility, failure/rollback approach and dependency/toolchain needs. Follow the installed version's Next.js documentation before changing application code.
- A test matrix mapping every acceptance criterion and threat to existing tests, new tests or an explicit gap with an owner and release consequence.

Use repository evidence over stale prose. Decisions describe intent; migrations, code, tests and actual executions establish local implementation. Neither proves hosted deployment.

## Privacy, authorization and security review

For any account, child, workspace, connection, enrollment, attendance, media or retention change, record assets, actors, trust boundaries, misuse cases and enforcement points before implementing. Include these questions where relevant:

- Can another user/workspace read or mutate this data? Can an anonymous, suspended, removed, disputed or revoked actor succeed?
- Is the actor derived from a verified server identity rather than caller-provided IDs? Is authorization checked again at execution time and after lock waits?
- Can a direct table write, duplicate request, retry, stale approval or concurrent revocation bypass the intended function?
- Are connection and enrollment separate? Does self-declaration incorrectly appear as verified legal guardianship?
- What data is collected, logged, exposed in errors, retained, exported or deleted? What is the consent and dispute/revocation model?

Use only synthetic data and approved disposable test containers. Do not connect to hosted Supabase or production as an incidental test. Do not weaken RLS, grant broader roles, disable TLS/checksum verification, suppress assertions or copy credentials into artefacts. Inspect variable names/presence and existing authentication before requesting missing configuration securely.

Unknown privacy or authorization semantics block the affected implementation/release decision. Continue independent safe work, record the exact missing decision and escalate to the founder; do not invent consent, guardianship or retention policy.

## Implementation and test requirements

Use TDD where practical: reproduce the expected failure first, implement the smallest change, then verify the regression and relevant suites. For configuration/documentation or tools that cannot execute here, state why a runtime test is unavailable and perform the strongest available validation; never label inspection as execution.

| Change | Required verification |
| --- | --- |
| Frontend presentation | Component behavior/accessibility assertions, frontend suite, TypeScript, lint and production build; representative layout review when layout changes |
| Auth/shared application libraries | Frontend and complete database regression; invalid input, disabled live access, error redaction, session rejection and authorization cases; real-provider checks only in separately authorized synthetic environments |
| Database/RLS/relationships | Fresh PostgreSQL 17 isolated initialization, every migration, role/tenant negative tests, rollback/idempotency, applicable deterministic race tests, exact JUnit evidence and cleanup audit |
| Concurrent writes/approval/revocation | Both lock orderings, retries/duplicates, atomicity, expiry during waits and no residual data; avoid relying only on nondeterministic sleeps |
| New cross-component journey | Integration tests at actual boundaries and E2E acceptance tests where a user journey is promised; mocks cannot establish signed JWT/provider/browser behavior |
| Dependencies, CI or gate | Broad regressions, lockfile integrity, gate positive/negative tests, source/receipt validation and workflow syntax validation; examine impact on existing check enforcement |
| Documentation only | Registry/gate validation, links/commands and consistency review; product suites only if selection/risk requires them |

The browser E2E suite currently covers two disabled-OTP login cases and the synthetic schedule preview. If a feature requires additional browser coverage, add the suitable tests within scope or report the release blocker; do not claim component tests are E2E or that these limited cases establish a complete sign-in journey. New third-party services or paid tools require approval.

Do not use zero-test runs, skipped/disabled security cases, expected failures or formatter success as substitutes for passing required tests. Capture exit codes even through pipelines (`set -euo pipefail`), inspect actual case identities/counts and keep passed, failed, skipped and unrun distinct. Do not repeatedly broaden testing after relevant checks pass unless code changes or unresolved findings justify it.

## Traceability and deterministic CI

Use `python3 scripts/quality/quality_gate.py inventory` to collect exact identities. Every collected application/database case must map to a truthful narrow requirement scenario. A new standalone database scenario must follow the supported `main()`/`__main__` convention and be registered in the existing runner. Add new database modules to the execution runner as well as the registry; collection alone is not execution.

Use `python3 scripts/quality/quality_gate.py self-test` for the engine. It rejects zero or skipped test runs. Use a full `plan` for an uncommitted feature; Git-base comparisons omit uncommitted edits. The policy is deterministic and conservative for unknown/security changes. Review new path classifications: a rule declaring a path known is a human design decision, not proof of safe impact. Rules omitting execution suites are limited to the explicitly supported documentation paths.

Before checks, record the execution plan/source fingerprint. After successful complete frontend or database checks, generate the suite's receipt and verify the current plan, exact reports, report digests, cleanup and required job results. See [the quality-gate guide](INTELLIGENT_QUALITY_GATE.md) for commands. Changing source bytes invalidates earlier plans/receipts even at the same HEAD. Generated reports and ignored local configuration are not versioned source; dependencies must be reproduced from reviewed lockfiles.

The existing legacy count assertions must grow intentionally when tests/migrations are added. Never lower counts or delete mappings to conceal lost security coverage. Changes to requirement status/risk, policy minimums or evidence validators need independent review and an explicit rationale. An unfinished critical product requirement cannot be renamed “planned” to justify releasing its behavior.

CI orchestration and evidence upload are code present in this branch, not verified hosted enforcement until approved commit/push and an inspected run. Branch protection is separately configured by an authorized repository owner; without it, a passing/absent check cannot prevent merges. Never claim that installing instructions makes a hosted check mandatory.

## Failure handling and independent review

Investigate failures with the systematic-debugging skill. Preserve logs, determine setup versus product versus test defects, reproduce the failing input/history/role and write a regression. A fix is resolved only when the original reproduction stops failing for the intended reason and relevant suites remain green. Do not merely rerun existing tests and declare the issue fixed.

Use a fresh reviewer when tools are available; provide the spec, full baseline, tracked and untracked diff, acceptance/test matrix and known gaps. Ask for adversarial cases: collection omissions, wildcard/path changes, stale evidence, skipped jobs, cross-tenant access, dependency changes and event triggers. The reviewer must not edit the shared checkout. Reconcile every finding as fixed with evidence, open/blocking, or explicitly accepted with an owner and consequence. State when independent review is unavailable; author review is not independent review.

AI review is advisory. It cannot approve scope expansion, waive security minimums, prove tests ran or substitute for founder approval. Do not claim a fresh review occurred if the reviewer failed to start.

## Evidence and verified checkpoints

Each feature handoff must include: branch/full HEAD, source fingerprint and uncommitted scope; requirement/acceptance matrix; commands and exit results; current report/receipt paths; skipped/unrun checks; independent findings and reproductions/fixes; remaining gaps and release consequences; exact created/modified/deleted files; and the precise next approval needed.

Store machine output in ignored `test-results/` directories and a durable human report under `docs/` or the feature's spec/plan. Summarize environment/time without secrets. Update `docs/BUILD_PROGRESS.md` when a milestone or verified capability changes. Historical successful runs must be labeled historical and cannot attest to new code.

After approved commit, verify its full SHA and clean/expected status; record that as a local checkpoint. After an independently approved push, verify the remote ref and inspect the actual hosted checks; record run identity, commit and conclusion. A local test, saved plan, Git commit, remote push and green hosted run are separate facts. Revalidate after fixes or conflicts. Merge/deployment remain separate approvals.
