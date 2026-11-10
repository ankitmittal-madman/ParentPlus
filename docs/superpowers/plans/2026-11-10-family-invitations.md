# Family invitations implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline, then one fresh-context final review.

**Goal:** Real academy family connection and Students roster using Supabase.
**Architecture:** Private token-hash table; scoped authenticated RPCs; validated
server actions; EN/HI client panels with observed-session invalidation.
**Tech Stack:** PostgreSQL, Next.js, React, TypeScript, Vitest, Playwright.
**Spec:** ../specs/2026-11-10-family-invitations-design.md

## Global constraints

Preserve all work/data/stash. No schema reset. Dummy OTP unchanged. Joining is
separate from enrolment. No raw tokens in logs/storage/screenshots. New copy EN/HI.

## Review focus

Expired token after lock; other child/account retries; issuer suspension;
late auth result revealing roster; lost response causing unsafe new writes.

## Tasks

- [ ] Archive originals with manifest/index; independent review and commit.
- [ ] SQL regressions RED; migration 051 for issue/preview/accept/roster/parent lookup;
  tests GREEN including real concurrency; update runner migration/count guards.
- [ ] Server action validation tests RED; implement family module and validate
  every returned row/identity; tests GREEN.
- [ ] Client tests RED; EN/HI Students and Join panels; memory-only fragment token,
  session invalidation, bounded roster pagination, parent connection display.
- [ ] Extend scenario catalogue and real local browser journey with screenshots;
  run frontend/database/browser/report/quality gate; resolve failures.
- [ ] Independent final review, regress findings, update canonical progress/evidence;
  commit/push/merge authorised work, inspect actual GitHub/Vercel outcomes.
