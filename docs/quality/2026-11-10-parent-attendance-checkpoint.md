# Parent attendance checkpoint — 10 November 2026

Parent Home now reads real child-scoped saved attendance, exact weekly facts and
own session reports by academy/class/date. Signed-in login and profiles link to
Home. Four report types, strict actor/input/response checks, original-request
recovery, EN/HI copy and safe typed-item fallback are implemented. Reports remain
separate from coach-confirmed attendance and do not assert verified handover.
No SQL migration, dependency or hosted database change is included.

## Verification and provenance

The final application implementation passed 528 frontend cases, lint, types,
production build, six disabled browser cases, six network-isolated synthetic
provider cases, 602 isolated database cases (598 unit + four standalone), 58 gate
engine tests, 25 operations tests and five action-observer checks. Database cleanup
was zero. Source-bound verification passed for execution fingerprint
`44c4333d8d43f43daeb9e5039d83735f4e96b4b972a60ec2f4da3bd48cf88018`
at pre-commit baseline `c5f2d7af243ee6a988187cb6bf8bd82fcf2a54a4`.

Real local browser run `run-20261110T182330Z-4c5d9c` executed 104/104 desktop/mobile
cases successfully with no retries or skipped cases. Reporting found one unmapped
Hindi Sign in control, so that report is not a complete action-coverage pass.
The anonymous navigation scenario was then expanded to click the actual Hindi
link; `run-20261110T190246Z-978902` passed both viewport cases. This subset leaves
102 cases NOT RUN and is not presented as a new complete run. The final source
also includes these QA/catalogue and documentation changes; earlier execution
receipts are retained as historical, not reissued for changed source. Fresh
final-head GitHub quality and full browser checks are required before merge.

Local detailed outputs are ignored under `test-results/qa/<run>/index.html`,
`scenarios.xlsx`, screenshots and `test-results/evidence/parent-attendance-hindi-current/`.
They may disappear with a replaced workspace. The GitHub browser workflow uploads
sanitised HTML/Excel/screenshots for durable download; inspect its actual matching
head result and artifact before claiming hosted success. The regular mobile
viewport is 390px; an additional exact360 capture remains a pre-merge check.

## Review and recovered work

The replaced workspace initially lacked uncommitted parent files, logs and stash.
That was reported before changes. Parent source was reconstructed against the
published c5f2d7a checkpoint; byte-identical recovery is not claimed. The original
founder reference files remain unchanged. All 961 pre-existing requirement entries
were preserved; 51 narrow parent test references append, with 73 matching EN/HI keys.

Independent review reproduced and fixed Refresh abandoning a pending class load
and a first recovery Check losing its reply during automatic selector bootstrap.
Both regressions first failed, then passed; scoped re-review found both addressed.
Complete checkpoint review found no new Critical/Important source issue. Minor
formatting/tool-advice cleanup remains deferred. The final Hindi action mapping
and real click were independently reviewed. Publication remains gated by actual
GitHub outcomes, not these local claims.

## Compatibility decision and remaining product scope

Immutable053 writes `attendance`; the founder contract calls it `attendance_record`.
Both are accepted as v1 read aliases with identical strict validation. Existing
records/writers/permissions were preserved. Cost: both spellings require ongoing
reader regression coverage.

This is a founder-testing attendance slice, not a completed app or launch sign-off.
Second-guardian distribution, diary/media/consent, AI, reminders, fees, richer
Needs you workflows and real-device/offline checks remain. Hosted browser behavior
and real email delivery are not established by local signed .test/123456 journeys.
The next development slice is saved class drafts, parent preview and real publish.
