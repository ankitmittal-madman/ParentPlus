# 06. Engineering standards

**In short:** small changes, everything tested automatically, security in the database, secrets in vaults, and a plain-language note on every change. This is how top product teams keep quality high while moving fast.

## Code

- TypeScript `strict`. No `any` without a comment explaining why.
- Business rules in `src/modules/*`, independent of the UI. Screens in `src/app/*` only display data and call modules.
- Validate every input at the edge with zod schemas (`schema.ts` in each module).
- No user-facing text in code: everything goes in `messages/en.json` and `messages/hi.json`.
- Outside services only through `src/lib/adapters/*`.
- Prefer boring, well-known libraries. Each new dependency needs a one-line reason in the pull request.

## Branches and pull requests

- `main` is always deployable and protected: no direct pushes.
- One story per branch: `story/S2-03-invite-link`.
- Pull requests are small (aim for under 400 changed lines) and use `.github/pull_request_template.md`, which starts with a plain-language summary.
- Merge by squash. Commit messages follow Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`).

## Automatic checks (CI) on every pull request

1. Lint and formatting (ESLint, Prettier)
2. Type check (`tsc --noEmit`)
3. Unit tests (Vitest)
4. Database migration and security tests on a throwaway Postgres (`supabase/tests/run_db_tests.sh`)
5. Production build
6. End-to-end smoke tests (Playwright) against the preview URL, for critical journeys

A red check blocks the merge. Flaky tests are fixed or removed within a day, never ignored.

## Database

- Migrations are numbered, append-only and reviewed. They're applied to staging by CI, and to production only at a gate.
- Every new table gets RLS policies **and** SQL tests in the same pull request.
- Use actions (RPC functions) for multi-step operations that must be atomic (for example `publish_post`).
- Backups: nightly encrypted dump (`.github/workflows/nightly-backup.yml`), plus a restore drill at every gate.

## Secrets and configuration

- Real values live only in Vercel and Supabase environment settings and in GitHub Secrets.
- The service-role key is server-only, and never prefixed `NEXT_PUBLIC_`.
- Rotate any key that was ever exposed, immediately.

## Testing strategy

| Level | What | Where |
|---|---|---|
| Unit | Module logic: schedules, reminder ladders, redaction, item builders | `src/modules/**/*.test.ts` |
| Database | Access rules and triggers | `supabase/tests/*_test.sql` |
| End to end | The gate journeys: sign in, set up a batch, invite, attend, post, consent | `e2e/*.spec.ts` |
| Manual | The founder's demo script on Android and iPhone | Gate review |

Target: 80% line coverage on `src/modules`. Every bug fix includes a test that would have caught it.

## Performance and quality budgets

First screen under 3 s on a mid-range Android over 4G. JavaScript for first load under 200 KB gzipped. Photos under 300 KB. Lighthouse PWA and accessibility scores of 90 or more.

## Observability

PostHog for product events, errors and feature flags. No children's names, photos or free text in events. Session replay off, or fully masked. Each job logs start, finish, item counts and errors to `events`.

## Dependencies and updates

Dependabot (free) opens update pull requests weekly. Security updates are merged within 7 days.
