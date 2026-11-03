# ParentPlus Intelligent Quality Gate v1

The gate produces an explained test plan, then requires successful selected jobs and matching evidence. `planned` is not test success. `passed` covers the registered scenarios and selected checks, not complete product correctness, real Supabase/JWT behavior or production readiness.

See [Engineering Standards](ENGINEERING_STANDARDS.md), [Feature Delivery Workflow](FEATURE_DELIVERY_WORKFLOW.md) and the [independent audit](INTELLIGENT_QUALITY_GATE_AUDIT.md).

## Architecture and current inventory

- `quality/requirements.json`: versioned requirement IDs, domains, descriptions, implementation status, risk, scenarios, exact executable references, coverage status and existing source/decision files.
- `quality/policy.json`: additive path rules, mandatory engine validation and conservative unknown-change fallback.
- `scripts/quality/quality_gate.py`: collection, schema/coverage validation, Git analysis, selection, execution receipts and JSON/Markdown evidence.
- `tests/quality/test_quality_gate.py`: positive and negative behavioral regressions.
- `intelligent-quality.yml`: event orchestration; the original frontend/database workflow files supply reusable checks.

Current application inventory: 39 database unit cases, four standalone scenarios and 24 frontend cases. These are observed baseline counts, not fixed thresholds in the new gate. Engine regressions are separate mandatory checks. Ten planned/deferred product gaps remain explicitly uncovered; the audit classifies their release consequences.

Database unittest discovery is recursive and collects without executing test bodies. Every database `test_*.py` module must contribute actual TestCases or be registered as a standalone scenario; unsupported/empty modules cannot disappear silently. Registered scenarios must define synchronous `main()` and invoke it directly under `if __name__ == "__main__":`. The legacy standalone runner supports flat filenames; nested scripts need a deliberate runner extension. Collection still imports modules, so top-level test code must be safe.

Vitest's actual JSON collector supplies file paths/full test names. Source-text regex counts are not treated as discovery. Duplicate or unmapped identities, invalid sources and uncovered implemented high/critical requirements fail. Planned/deferred requirements cannot claim covered tests. Narrow scenario coverage does not prove an entire feature implemented.

## Add or change a requirement

1. Write observable acceptance criteria and threats; register planned requirements with stable IDs, risk and source decisions.
2. Implement tests and the smallest feature slice using the relevant skills.
3. Collect exact identities:

   ```bash
   python3 scripts/quality/quality_gate.py inventory
   ```

4. Link actual `{ "suite": "frontend|database|concurrency", "ref": "exact identity" }` references to the narrow scenarios demonstrated. Mark only the completed slice implemented.
5. Update the execution runners as needed and verify fresh results. The legacy database/frontend count safeguards remain intact and must grow intentionally with new tests/migrations; never lower them to conceal lost assertions.

Frontend identity example: `apps/web/src/lib/auth/request-email-otp.test.ts::requestEmailOtp > normalizes email and prevents automatic signup`. Python identities use module/class/method; standalone identities use `tests/database/<filename>.py`.

## Selection rules

All matching rules contribute suites; rule order cannot suppress another match. Path matching is segment-aware: `*` stays inside one directory, `**` spans directories. Thus `apps/web/*.ts` cannot classify a new nested domain as a root configuration file.

Protected code rules enforce broad security/dependency minima. Only the explicitly supported documentation patterns may omit execution suites. Human review must still assess classifications: declaring a new path known/frontend-only is a design decision, not proof that no database or privacy impact exists.

| Change | Minimum selection |
| --- | --- |
| Known frontend presentation | Engine validation + frontend tests/type/lint/build |
| Authentication/shared libraries/security paths | Engine + frontend + database |
| Database migrations/tests | Engine + database; security-keyword paths may select both |
| Dependencies, CI, engine, policy | Engine + frontend + database |
| Unknown paths, missing/empty comparison, non-ancestor history | Full regression |
| Explicit documentation-only paths | Engine/registry validation |

Git comparison includes both sides of renames/deletions. Non-ancestor history selects full regression so a force-push cannot hide security-file removal. Commit-based comparison excludes dirty work; use a full plan for uncommitted features. `--changed-file` is a local diagnostic override, not certification of the complete scope.

## Local execution

From the repository root, after installing locked frontend dependencies:

```bash
python3 scripts/quality/quality_gate.py self-test
python3 scripts/quality/quality_gate.py plan --output test-results/quality/feature-plan
```

`self-test` rejects failed, skipped or zero-test runs. The plan records HEAD and a SHA-256 fingerprint of nonignored checkout bytes/executable modes. Root generated `test-results/` is excluded; ignored dependencies are reproduced from lockfiles rather than fingerprinted. Source symlinks are explicitly unsupported. Editing test bodies, source, policy or docs at the same HEAD invalidates the previous snapshot.

Run the complete frontend checks from `apps/web` with live OTP disabled:

```bash
NEXT_PUBLIC_ENABLE_LIVE_OTP=false npm test -- \
  --reporter=default --reporter=junit \
  --outputFile.junit=test-results/vitest-junit.xml
npm run lint
npm run typecheck
NEXT_PUBLIC_ENABLE_LIVE_OTP=false NEXT_TELEMETRY_DISABLED=1 npm run build
```

From the root, run the complete existing isolated database gate:

```bash
bash scripts/ci/database-quality.sh
```

It creates its own disposable PostgreSQL 17 container with no network/published ports, loads synthetic auth and migrations, runs unit/concurrency checks, validates evidence, audits zero residual data and removes its container. Do not connect to hosted Supabase.

Only after all required checks succeed, generate receipts against the pre-execution plan:

```bash
python3 scripts/quality/quality_gate.py attest --suite frontend \
  --plan test-results/quality/feature-plan/quality-gate.json \
  --reports apps/web/test-results
python3 scripts/quality/quality_gate.py attest --suite database \
  --plan test-results/quality/feature-plan/quality-gate.json \
  --reports test-results/database
mkdir -p test-results/evidence/frontend test-results/evidence/database
cp apps/web/test-results/vitest-junit.xml \
   apps/web/test-results/frontend-receipt.json test-results/evidence/frontend/
cp test-results/database/unittest-junit.xml \
   test-results/database/concurrency-junit.xml \
   test-results/database/cleanup-count.txt \
   test-results/database/database-receipt.json test-results/evidence/database/
python3 scripts/quality/quality_gate.py verify \
  --plan test-results/quality/feature-plan/quality-gate.json \
  --reports test-results/evidence \
  --job-result quality=success \
  --job-result frontend=success \
  --job-result database=success
```

For narrower plans, run/attest only selected suites and report other jobs as skipped. A local success declaration is valid only after the entire suite, including lint/type/build or isolation/cleanup, succeeds. Receipts bind report hashes to source, commit and run/attempt context; they are not cryptographic proof that a caller executed shell commands. Deliberately regenerating a receipt for stale reports remains a human/process trust boundary. Do not re-label old reports as new executions.

Verification recomputes current inventory, gaps, selection and source bytes; requires successful selected jobs, matching exact cases, valid counters/durations, no failures/errors/skips/orphan nodes, unique reports and clean database state. Missing/stale/mismatched receipts fail. Default output is ignored `test-results/quality/quality-gate.json` and `summary.md`; it records snapshot, reasons, expected identities, gaps and verified report digests. Failed validation does not establish coverage.

## GitHub Actions behavior

Automatic pushes cover all branches without path filters. PR activity includes opened, synchronize, reopened, ready-for-review and edited (including base changes). Merge-group events are supported if a repository owner enables a merge queue; unknown bases select full regression. Manual runs also select full regression without a reliable comparison.

Concurrency separates event type and PR number/full ref, so fork branch names cannot cancel each other. A push and PR may legitimately produce separate commit-context runs; each selected reusable suite executes once per workflow run.

The plan job installs dependencies for real collection and runs strict engine tests. Reusable jobs retain the original checks and manual dispatch. Receipts are generated only after all job checks succeed; frontend artifact upload now follows the build/receipt step and still runs after failures for diagnosis. The final gate runs even when prerequisites fail, independently recomputes changed paths from the event base, and requires actual `needs` outcomes plus reports/receipts downloaded from the same run. Run-attempt binding prevents a retained artifact from an earlier attempt satisfying a later attempt; rerun all selected jobs when retrying a run.

Permissions remain read-only; no privileged `pull_request_target` or inherited production secrets. GitLab mirror automation is unchanged. Source/workflow edits require human review and repository protection. These workflows are prepared locally, not verified active on GitHub until an approved commit/push and inspected run. No branch-protection settings are changed here.

## Failure investigation and limitations

Missing references require real collection and corrected mappings, not invented results. Critical coverage gaps require tests or correction of a false implementation claim, not risk downgrades. Missing/stale evidence requires current execution and receipts. Diagnose setup versus product defects, retain the reproduction and verify the regression.

Turbopack needs local worker ports: use supported sandbox escalation when blocked; clear only generated cache if a denied operation was cached. Keep TLS/checksum checks enabled. Do not change application behavior to mask environment failures.

Mocks do not prove live OTP, signed JWTs, legal guardianship or hosted authorization. No browser E2E suite is installed. Human review must identify unspecified requirements and truthful scenario coverage. AI may propose missing scenarios and explain failures only when an agent is actually invoked; it cannot suppress deterministic checks or approve production actions. See the operating workflow for release blockers and approvals.
