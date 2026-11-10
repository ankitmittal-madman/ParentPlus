# ParentPlus first-use rollout: preparation

## Current local verification — 2026-11-09

The recovered preparation below is historical. Local Supabase now applies all
49 migrations, and parent, independent-coach and academy-owner first-use browser
journeys pass with real local Auth/Mailpit/PostgREST/PostgreSQL. The default-off
workspace screen now supports same-request creation/recovery using the existing
controlled function. The current rollout boundary is unchanged: hosted state,
upgrade safety for the actual project, release approval, retention and sensitive
family-data use remain unverified. See [local evidence](LOCAL_FIRST_USE_VERIFICATION.md).


This is a preparation record, not permission to change the hosted project.
The founder reported that the hosted Supabase project has migrations 001–013.
That observation was made in another session and has not been independently
rechecked in this checkout. Recheck the exact project, migration versions and
schema immediately before a rollout.

## Intended first-use journeys

1. A parent requests and verifies an email code, signs in and creates a child
   profile with fictional test data.
2. A new coach signs in, creates an independent-coach or academy workspace,
   then creates a course, batch and recurring class sessions.

Neither journey is confirmed end to end against the hosted provider. At the recovered preparation baseline, the new
coach workspace screen and application-accessible recovery flow were incomplete.
The deployed app and local checkout must not be assumed to be the same version.

## Migration inventory and dependencies

The local repository contains 49 ordered migrations. If the reported hosted
baseline is confirmed unchanged, migrations 014–049 are locally ahead of that
baseline. This is an inventory, not a recommendation to apply them as a batch.

On 2026-11-08, an isolated PostgreSQL rehearsal applied 001–013, inserted one
fictional workspace and owner plus one fictional child and guardian, then
applied 014–049. Those selected records survived and the workspace, child and
class creation controls remained disabled. The repeatable local script is
`scripts/ci/rehearse-first-use-upgrade.sh`. It uses a simulated Auth fixture;
it does not reproduce the hosted database, real JWTs, existing data variants,
interrupted upgrades or the complete authorization and recovery review.

| Local migrations | Main area | Rollout consideration |
| --- | --- | --- |
| 014–031 | Scheduling foundation and class setup protocol | Includes intermediate draft operations and later restrictions; assess the ordered sequence as a whole. |
| 032–037 | Parent-created profile access and child creation recovery | Default-off controls, authorization and recovery require verification. |
| 038–040 | Guardian connection receipts and restrictions | Intermediate functions have different privileges; see the database security review before any partial rollout. |
| 041–047 | Workspace creation controls, receipts and private recovery | Creation controls default off; private recovery functions are not an application onboarding flow. |
| 048–049 | Class setup generations and weekly sessions | Depends on earlier scheduling work; controls remain off and enabled browser/provider testing is open. |

Review exact SQL dependencies, hosted roles, existing data and privileges, and
the current [database security review](DB_SECURITY_REVIEW.md). Rehearse the
actual hosted-baseline upgrade on a disposable isolated database with synthetic
representative data, including partial-failure and recovery checks. A fresh
database migration run is useful but does not establish upgrade safety.

## Before hosted changes

- Verify the target project and current migration history, then prepare a tested
  backup and recovery procedure suitable for a long-lived database.
- Complete review of authorization, row-level security, privilege boundaries,
  concurrency, retry and recovery, retention and other open privacy risks.
- Verify email template/code type, delivery, rate limits, signup settings and
  identity behaviour using test accounts; do not put provider secrets in chat.
- Identify application and database flags individually and verify their default
  states. A frontend flag is not an authorization boundary.
- Prepare an exact ordered change, verification and recovery plan. Obtain the
  required approval before hosted migrations, configuration or real data use.
- Test parent and coach journeys with fictional data after rollout. Browser,
  real-provider and hosted evidence are separate from mocked or local checks.

The selected project is intended to hold real family data later. Do not reset it
or use it for destructive/concurrency tests. See [DEC-020](DECISION_LOG.md#dec-020-continuity-of-the-selected-supabase-project).
