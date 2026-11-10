# 14. Decision log (Architecture Decision Records)

**In short:** each big technical choice, what we chose, what we didn't, and why. If a decision changes, we add a new record; we never rewrite history.

## ADR-001: Next.js and Supabase
- **Decision:** Next.js (TypeScript) for the app; Supabase for database, sign-in, files, live updates and jobs.
- **Why:** the best-known stack for AI builders; one vendor for the whole backend; strong security in the database (RLS); free tier; Mumbai region.
- **Not chosen:** Firebase (its document database fits our relational data poorly), a custom backend (too much to run for a two-founder team).

## ADR-002: Installable web app (PWA) first
- **Decision:** one PWA with coach and parent experiences.
- **Why:** no app-store review, instant updates, one codebase, ₹0.
- **Trade-off:** iPhone push needs the app on the home screen. Revisit native apps after the pilot.

## ADR-003: Keep the MVP's 7 table names; add organisations now
- **Decision:** keep profiles, children, classes, enrollments, attendance, posts and fees. Add organizations and org_members from day one.
- **Why:** continuity with the MVP plan. No pilot data exists yet, so adding academies now avoids a risky migration later.

## ADR-004: Typed parent items (UI-agnostic contract)
- **Decision:** everything parents receive is a typed, versioned row in `parent_items`, with a fallback rendering.
- **Why:** features stay independent of design; new apps or channels can be added without changing the backend.

## ADR-005: Pilot sign-in is Google plus email code
- **Decision:** per D2 (recommended A).
- **Why:** free and familiar. SMS codes in India need DLT registration and cost money per message. Supabase's built-in email reaches only team addresses, so Resend is connected for parents.

## ADR-006: AI behind an adapter, with names removed
- **Decision:** Gemini free tier through `src/lib/adapters/ai.ts`; names and phone numbers replaced before every call; a cost cap; AI can be switched off.
- **Why:** quality at ₹0, with a clean switch to a paid, no-training provider later.

## ADR-007: Hosting
- **Decision:** build on Vercel Hobby; decide production hosting at Stage 7 (D4). The default plan is to try Cloudflare's free plan, falling back to Vercel Pro.
- **Why:** Vercel Hobby is for non-commercial use only. Keeping the code portable (no Vercel-only features) keeps both options open.

## ADR-008: Security in the database
- **Decision:** RLS on every table; permissions from relationships; consent checked by database functions; SQL tests required for every rule.
- **Why:** the app can have bugs, but the database still won't hand one family another family's data.

## ADR-009: PostHog for analytics, errors and feature flags
- **Decision:** one free tool instead of three; session replay off or fully masked.
- **Why:** fewer vendors and fewer places where data could leak.

## ADR-010: Our own nightly backups
- **Decision:** a nightly encrypted dump via GitHub Actions, kept 14 days; a restore drill at every gate.
- **Why:** the Supabase free plan has no automatic backups (Supabase recommends regular exports).
