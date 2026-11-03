# Independent Audit and Engineering Operating System Report

Date: 2026-11-03. Branch: `feature/intelligent-quality-gate-v1`. Baseline/HEAD: `ac2b1f9af85b531142310fcd851a24c17390f4ae`. All work remains uncommitted; no push, merge, deployment, hosted Supabase/production action, repository-setting change or paid service occurred.

## Verdict and independent review

The original 39 green quality tests did not establish that the framework was safe against all collection/selection/evidence mistakes. A fresh read-only reviewer and author adversarial probes reproduced confirmed gaps. Ten additional regression tests plus negative subcases now bring the strict engine suite to 49. The independent reviewer reran those 49 tests, collected the real inventory, inspected preserved security assertions and exercised receipt tampering/source-edit checks in temporary repositories.

The reviewer found no remaining confirmed Important/Critical code defect in the corrected scope. A Minor documentation ambiguity about refreshing evidence after documentation edits was corrected: historical full-suite reports must not be re-attested as fresh. The author performed final validation after the report/build-progress updates; those prose updates are not claimed independently reviewed.

This is readiness for founder review of a local engineering change, not production readiness or a claim of hosted CI success. Local callers can still lie about commands or deliberately fabricate receipts; the system is not a cryptographic attestation service. Human review and repository enforcement remain necessary.

## Findings by severity and corrections

No Critical issue was confirmed. The following Important defects/operational gaps were corrected locally:

| ID | Reproduced defect or gap | Correction and evidence |
| --- | --- | --- |
| A1 | Python fnmatch let `apps/web/*.ts` match nested unknown domain code, selecting frontend alone | Segment-aware matching; new-domain `.ts` regressions now select full regression while a root config stays frontend-only |
| A2 | A failing standalone `__main__` body, async main, alternate entrypoint, reversed guard or empty test module could disappear from inventory | Every database test module must collect real TestCases or be a registered supported scenario; temporary unsupported forms now fail closed |
| A3 | A registered failing `main()` without any invocation exited zero and could produce false-green standalone evidence | Canonical direct main invocation is required; missing-entrypoint regression fails before the fix and is rejected afterward |
| A4 | HEAD and case names stayed unchanged after edits to test/source bodies, permitting stale plans/evidence | Source-byte/mode fingerprint, current-source plan comparison and source/report/run-attempt receipts; source edits, receipt deletion and source/context/digest tampering are rejected |
| A5 | Raw unittest could report green for zero/skipped/expected-failure engine tests; database expected failures could appear as passing cases through the legacy reporter | Strict self-test rejects these outcomes; database collection refuses disabled/expected-failure cases before registry coverage claims. Original legacy assertions remain intact |
| A6 | An accidental catch-all rule with no execution suites suppressed the unknown fallback | No-execution/quality-only rules are restricted to explicit documentation paths; invalid broad rules are rejected while protected security minimums remain additive |
| A7 | Extra failing testcase nodes outside a testsuite could be ignored by JUnit parsing | All testcase nodes must be accounted for and failure/error/skip nodes anywhere reject evidence; orphan-failure fixture proves the negative behavior |
| A8 | Push filters omitted non-feature branch names, and default PR activity did not rerun on base retargeting | All-branch pushes, explicit PR edited/ready events and merge-group support; final verification independently recomputes event changes, artifacts are attempt-scoped. Syntax/logic reviewed locally; actual hosted event/artifact behavior remains unverified |

These are demonstrated reproductions and targeted corrections, not issues marked fixed merely because the old suite stayed green. Regression histories were captured in `/tmp/parentplus-audit-*.log`; durable final results are in ignored `test-results/quality/audit/` and its associated runner outputs.

Minor corrected: BUILD_PROGRESS described an old branch/milestone/test count; it now separates current local facts from historical notes. Evidence-refresh wording now expressly prohibits re-labeling old reports.

## Mapping, policy and test review

The versioned registry contains 77 narrow entries: 67 implemented scenario contracts corresponding to exactly 39 database unit identities, four standalone scenarios and 24 frontend identities, plus ten planned/deferred requirements with no passing tests claimed. Every executable reference was validated through real collection; no incorrect mapping was confirmed. Frontend OTP and UI mappings are unit/component contracts with mocks, not live-provider/E2E claims.

The initial 39 gate tests exercise behavior: registry schema and references, duplicate IDs, critical gaps, current inventory completeness, temporary real Git histories, recursive collection, policy floors, planned-feature constraints and positive/negative XML evidence. The added tests cover the bypasses above. Fixture receipts are refreshed for intentional XML mutations so digest mismatches cannot hide a broken XML assertion. Tests do not merely check filenames or configuration text.

Comparison with HEAD confirms no edits to application tests/source, database migrations, legacy CI runner assertions/counts/isolation/cleanup logic, package declarations/lockfile or GitLab backup workflow. Reusable workflow checks are retained; frontend upload moves after build/receipt generation, still running after failure for diagnosis. Receipts are additive checks. Superpowers skills and Next.js instructions are unchanged.

Policy remains conservative, not an authorization proof. A developer intentionally classifying a new path frontend-only still needs architecture/threat review; an enforcement-code rewrite cannot be secured solely by tests in the same change. Required-check repository settings remain a separate owner decision.

## Ten gap dispositions

All ten are **acceptable as explicit nonblocking gaps for this synthetic-data tooling milestone**. The release classification below is separate; a green tooling gate does not waive it.

| Registry ID | Primary release disposition | Required consequence/decision |
| --- | --- | --- |
| AUTH-LIVE-OTP | Blocking | No real sign-in/session release until live synthetic integration, token/session rejection and acceptance/E2E behavior are verified |
| GUARDIAN-FORMAL-VERIFICATION | Future decision; conditional blocker | Decide method/timing under DEC-013. No sensitive real-child access solely from declaration; dispute, authorization and revocation controls cannot be deferred indefinitely. Never label declaration verified legal guardianship |
| CONNECTION-COACH-INVITATION | Blocking | Do not offer coach invitation/confirm/skip/reject journeys until implementation, expiry/authorization and user-journey tests exist |
| ENROLLMENT-LIFECYCLE | Blocking | No enrollment release or claim an approved connection enrolls a child until its distinct lifecycle is tested |
| ATTENDANCE-AUTHORIZATION | Blocking | No attendance access/changes before workspace/guardian authorization and relevant user journeys are verified |
| DIARY-MEDIA-CONSENT | Blocking | No private diary/media collection or sharing without consent, access, retention and negative tests |
| ACCOUNT-RETENTION | Blocking; policy decision required | Resolve real-account/child-record deletion, ownership transfer and retention controls before affected real-data rollout |
| GUARDIAN-HISTORY | Blocking | No historical learning-record access promise until authorization/revocation and retention behavior is implemented/tested |
| PHONE-OTP | Acceptable deferred option / future product decision | DEC-011 permits initial email-only scope; no blocker unless phone sign-in is added to acceptance criteria |
| LEARNING-DELIVERY | Blocking | No release claiming courses/lessons/batches/sessions/coach assignment behavior before corresponding contracts/journeys exist |

Requirement statuses and risks were not downgraded. Planned gaps are not passing tests or permission to release their behavior.

## Validation and evidence

Observed local results during this audit:

| Check | Result |
| --- | --- |
| Strict engine self-test and independent regression run | 49 passed; no skipped/expected failures counted as success |
| Actual collection + registry | 39 database + 4 concurrency + 24 frontend identities; all mapped |
| Frontend | Six files/24 tests passed; lint, TypeScript and production build passed with live OTP disabled |
| Existing complete database quality gate | All 13 migrations, 39 unit tests and 4 standalone scenarios passed; isolation, JUnit and zero-residue cleanup passed |
| Receipt adversarial checks | Valid round trip accepted; source edits at same HEAD, report edits, wrong source/run/digest and missing receipts rejected |
| Workflow syntax | actionlint 1.7.7 passed locally |
| Python syntax and Git whitespace | Validated for new code and complete changed-file scope |
| Secret scanning | Gitleaks 8.24.3 scans the exact changed/new scope, excluding generated dependency/build trees; final result is recorded with audit evidence |
| Final source-bound verification | See `test-results/quality/audit/verified/quality-gate.json` and `summary.md`; source digest is recorded there to avoid embedding a self-referential hash in source |
| Hosted CI, artifact downloads/cancellation and branch protection | Not run/verified or changed |
| Browser E2E, physical-device, real OTP/JWT/Supabase and production | Not established; outside this local verification |

The final source snapshot includes the operating docs and this audit. Tests/receipts are refreshed after freezing that snapshot; earlier unbound/historical reports are not treated as final evidence. Original execution logs and JUnit are under existing result directories, and copied final logs/receipts live under `test-results/quality/audit/` and `test-results/evidence/audit/`.

## Engineering operating system and future workflow

`docs/ENGINEERING_STANDARDS.md` defines feature entry artefacts, threat review, applicable test matrix, traceability, strict evidence, independent review, failure handling and checkpoint approvals. `docs/FEATURE_DELIVERY_WORKFLOW.md` turns founder request → requirements → architecture → test plan → implementation → execution → independent AI/human review → evidence → founder approval into an actionable procedure, including every exception case requested. AGENTS routes future agents to both documents without removing existing skills or Next.js guidance.

This makes the procedure available to an invoked Codex agent using actual exposed tools. It does not install a scheduled autonomous builder, browser runner, approval bot or mandatory hosted enforcement. AI suggestions remain advisory and cannot suppress deterministic checks.

`docs/BUILD_PROGRESS.md` now records the correct branch, unchanged baseline HEAD, uncommitted scope, verified local capabilities, incomplete product milestones, hosted limitations and next approvals. Old roadmap/DEC-002/checkpoint wording is explicitly historical where it conflicts with current task authorization.

## Founder actions and remaining risks

No new product/privacy decision is needed to review this tooling milestone. Before the affected real product releases, resolve the gap decisions/blockers above. Current handoff requires founder review of the complete code/document scope and evidence; **no commit is permitted until approval after that presentation**. Push and hosted CI inspection are a separate approval. Requiring the final check in branch protection is a separate owner action; merge/deployment/hosted migrations remain separately unauthorized.

Remaining limits: local receipt creation trusts the caller; human review judges scenario truth/unspecified requirements; ignored runtime dependencies are lockfile-managed, not fingerprinted; source symlinks are unsupported; the legacy runner module/count lists still need deliberate extension; hosted behavior and production/provider/E2E controls remain unverified. Retry all selected jobs in a new CI attempt so old attempt artefacts cannot satisfy it. No enforcement claim is made without actual repository settings and an inspected run.

## Exact uncommitted file scope relative to HEAD

- Modified: `.github/workflows/database-quality.yml`
- Modified: `.github/workflows/frontend-quality.yml`
- New: `.github/workflows/intelligent-quality.yml`
- Modified: `.gitignore`
- Modified: `AGENTS.md`
- Modified: `docs/BUILD_PROGRESS.md`
- New: `docs/ENGINEERING_STANDARDS.md`
- New: `docs/FEATURE_DELIVERY_WORKFLOW.md`
- New: `docs/INTELLIGENT_QUALITY_GATE.md`
- New: `docs/INTELLIGENT_QUALITY_GATE_AUDIT.md`
- New: `docs/INTELLIGENT_QUALITY_GATE_REPORT.md`
- New: `docs/superpowers/plans/2026-11-03-engineering-operating-system.md`
- New: `docs/superpowers/plans/2026-11-03-intelligent-quality-gate.md`
- New: `docs/superpowers/specs/2026-11-03-intelligent-quality-gate.md`
- New: `quality/policy.json`
- New: `quality/requirements.json`
- New: `scripts/quality/quality_gate.py`
- New: `tests/quality/test_quality_gate.py`
