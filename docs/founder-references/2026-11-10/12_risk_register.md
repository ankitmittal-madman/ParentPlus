# 12. Risk register (product and technical)

**In short:** the things most likely to hurt us, how likely and how bad each is, and what we're doing about it. Reviewed at every gate.

| # | Risk | Likelihood | Impact | Mitigation | Early warning |
|---|---|---|---|---|---|
| R1 | Coaches stop posting after the novelty wears off | Medium | High | AI drafts (Stage 5), the 2-minute wrap-up, a 'Needs you' nudge, posting-rate tracking | Posting days below 4 of 5 for a week |
| R2 | Hinglish voice-to-text is too poor | Medium | High | Test set of 10 real notes; text fallback; swap speech provider through the adapter | Fewer than 8 of 10 drafts usable |
| R3 | iPhone parents miss notifications (PWA not installed) | High | Medium | Install prompt with steps; WhatsApp-link fallback; track push opt-in | Push opt-in below 50% of iPhone parents |
| R4 | A privacy mistake with a child's photo | Low | Very high | Database consent rules; 55+ tests; crop or blur prompt; gate privacy checklist | Any consent-related bug report |
| R5 | Supabase free project pauses, or hits limits | Medium | High | Daily use during the pilot; usage alerts; photo compression; upgrade trigger in docs/03 | Storage over 70%; no activity for 5 days |
| R6 | No automatic backups on the free tier | Certain | High | Nightly encrypted dump; a restore drill at every gate | A backup job fails once |
| R7 | Free AI tier limits or data terms change | Medium | Medium | Adapter, name removal, cost cap; can switch provider or disable AI | Rate-limit errors; terms update |
| R8 | Sign-in emails fail or hit 100 a day | Low | High | Google sign-in as the main path; Resend monitoring | Email bounce rate over 2% |
| R9 | Hosting terms (Vercel Hobby is non-commercial) | Certain at launch | Medium | Decision D4 at Stage 7; portable code (no Vercel-only features) | Stage 7 reached |
| R10 | The AI builder introduces subtle bugs | Medium | Medium | Small pull requests, CI, SQL security tests, end-to-end tests, founder preview checks | Bug reports per stage over 5 |
| R11 | Founder time is too thin for weekly reviews | Medium | High | 45-minute fixed slot; 10-minute daily diary; one named approver (D7) | Two missed demos |
| R12 | Scope creep before the pilot | High | Medium | Stage gates; 'later' list; a new idea goes into the backlog, not into the current stage | Gate dates slipping twice |
