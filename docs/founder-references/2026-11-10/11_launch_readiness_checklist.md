# 11. Launch readiness checklist (Stage 7)

**In short:** before the first real family joins, every box is ticked. If one can't be ticked, we either fix it or write down why it's safe to launch without it.

## Product
- [ ] Every Stage 1 to 6 gate is passed
- [ ] The full class-day rehearsal is done (founder as coach, a friend as parent, two phones)
- [ ] Empty states and error messages say what to do next, in English and Hindi
- [ ] The known-issues list is written and shared with the pilot coach

## Quality
- [ ] End-to-end tests pass on production: sign in, set up, invite, attend, post, consent, reminders
- [ ] Android Chrome and iPhone Safari (installed) both tested
- [ ] The first screen loads in under 3 s on a mid-range Android over 4G
- [ ] No open bug marked "must fix"

## Privacy and safety
- [ ] Privacy policy and consent wording reviewed (ideally by a lawyer) and live in the app
- [ ] "Delete my data" request path works, end to end
- [ ] Consent withdrawal hides media immediately (verified on production)
- [ ] No children's data in analytics, logs or AI requests (spot-check)
- [ ] Two-step login confirmed on every service account

## Operations
- [ ] Production backup ran last night; a restore drill passed this week
- [ ] North-star and guardrail dashboard live in PostHog
- [ ] Hosting is on a plan that allows commercial use (D4)
- [ ] Usage is checked against free limits, with alerts set (Supabase, Resend, AI)
- [ ] Rollback steps written down and tested once
- [ ] Supabase pause risk handled: the app is in daily use, or the project is upgraded

## People
- [ ] Pilot coach trained (under 20 minutes) and has a one-page guide
- [ ] Parent welcome message ready (what Parent Plus is, privacy in one paragraph, how to install)
- [ ] Support WhatsApp number set up, with replies within 4 working hours
- [ ] Founder sign-off: "I'd be proud to show this to a parent"
